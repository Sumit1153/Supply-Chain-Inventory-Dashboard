"""
Generates a synthetic supply chain dataset for the Power BI dashboard.

Simulates one year (2025) of daily demand, inventory levels and purchase
orders for 40 products and 8 suppliers using a reorder-point policy.
Supplier deliveries can be late, which causes stockouts and lost sales.

Run:  python scripts/generate_data.py
Output: CSV files in /data
"""
import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
OUT = Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(exist_ok=True)

START, END = "2025-01-01", "2025-12-31"
dates = pd.date_range(START, END)

# ---------- Suppliers ----------
suppliers = pd.DataFrame({
    "supplier_id": [f"S{i:02d}" for i in range(1, 9)],
    "supplier_name": ["Apex Industrial", "BlueLine Chemicals", "Condor Packaging",
                      "Delta Components", "EverGreen Supply", "Fortis Materials",
                      "GlobalTrade Co", "Helix Polymers"],
    "region": ["India", "India", "China", "Germany", "India", "USA", "China", "Singapore"],
    "avg_lead_time_days": [5, 7, 18, 14, 6, 21, 16, 12],
    # probability that a delivery is late (reliability differs per supplier)
    "late_probability": [0.10, 0.15, 0.45, 0.25, 0.08, 0.50, 0.40, 0.20],
})

# ---------- Products ----------
categories = {
    "Raw Materials": (40, 90),
    "Packaging": (5, 20),
    "Consumables": (10, 40),
    "Spare Parts": (60, 250),
    "Finished Goods": (80, 300),
}
rows = []
for i in range(1, 41):
    cat = list(categories)[(i - 1) % 5]
    lo, hi = categories[cat]
    cost = round(rng.uniform(lo, hi), 2)
    rows.append({
        "product_id": f"P{i:03d}",
        "product_name": f"{cat.split()[0]} Item {i:02d}",
        "category": cat,
        "unit_cost": cost,
        "unit_price": round(cost * rng.uniform(1.25, 1.6), 2),
        "avg_daily_demand": int(rng.integers(8, 40)),
        "supplier_id": rng.choice(suppliers.supplier_id),
    })
products = pd.DataFrame(rows)
products = products.merge(suppliers[["supplier_id", "avg_lead_time_days"]], on="supplier_id")
# reorder point = demand during average lead time + safety stock (~3 days)
products["reorder_point"] = (products.avg_daily_demand * (products.avg_lead_time_days + 3)).astype(int)
products["order_quantity"] = (products.avg_daily_demand * 30).astype(int)
products = products.drop(columns="avg_lead_time_days")

sup = suppliers.set_index("supplier_id")

# ---------- Simulation ----------
inv_rows, po_rows = [], []
po_counter = 1
for _, p in products.iterrows():
    stock = int(p.reorder_point + p.order_quantity * 0.5)
    open_po = None  # (arrival_date, qty, po_index)
    for d in dates:
        # receive delivery
        if open_po is not None and d >= open_po["delivery"]:
            stock += open_po["qty"]
            po_rows[open_po["idx"]]["qty_received"] = open_po["qty"]
            open_po = None

        # demand with weekly + seasonal pattern
        season = 1 + 0.25 * np.sin(2 * np.pi * (d.dayofyear - 60) / 365)
        weekday = 0.85 if d.dayofweek >= 5 else 1.05
        demand = int(max(0, rng.normal(p.avg_daily_demand * season * weekday,
                                       p.avg_daily_demand * 0.25)))
        sold = min(demand, stock)
        stock -= sold
        lost = demand - sold

        inv_rows.append({
            "date": d.date(), "product_id": p.product_id,
            "units_demanded": demand, "units_sold": sold,
            "closing_stock": stock, "stockout_flag": int(stock == 0),
        })

        # place PO when stock falls to reorder point
        if open_po is None and stock <= p.reorder_point:
            s = sup.loc[p.supplier_id]
            lead = int(s.avg_lead_time_days)
            promised = d + pd.Timedelta(days=lead)
            late = rng.random() < s.late_probability
            delay = int(rng.integers(2, 10)) if late else 0
            delivery = promised + pd.Timedelta(days=delay)
            qty = int(p.order_quantity)
            po_rows.append({
                "po_id": f"PO{po_counter:05d}", "supplier_id": p.supplier_id,
                "product_id": p.product_id, "order_date": d.date(),
                "promised_date": promised.date(), "delivery_date": delivery.date(),
                "qty_ordered": qty, "qty_received": 0,
                "unit_cost": p.unit_cost,
            })
            open_po = {"delivery": delivery, "qty": qty, "idx": len(po_rows) - 1}
            po_counter += 1

inventory = pd.DataFrame(inv_rows)
pos = pd.DataFrame(po_rows)
# POs whose delivery falls after year end are still open
pos.loc[pd.to_datetime(pos.delivery_date) > pd.Timestamp(END), "delivery_date"] = pd.NaT
pos["status"] = np.where(pos.delivery_date.isna(), "Open", "Delivered")

products.to_csv(OUT / "dim_products.csv", index=False)
suppliers.drop(columns="late_probability").to_csv(OUT / "dim_suppliers.csv", index=False)
inventory.to_csv(OUT / "fact_inventory_daily.csv", index=False)
pos.to_csv(OUT / "fact_purchase_orders.csv", index=False)

print(f"products: {len(products)}  suppliers: {len(suppliers)}")
print(f"inventory rows: {len(inventory):,}  purchase orders: {len(pos):,}")
