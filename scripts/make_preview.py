"""Builds a preview image of the dashboard layout from the CSV data (matplotlib)."""
import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

root = Path(__file__).resolve().parent.parent
inv = pd.read_csv(root/"data/fact_inventory_daily.csv", parse_dates=["date"])
po = pd.read_csv(root/"data/fact_purchase_orders.csv", parse_dates=["order_date","promised_date","delivery_date"])
prod = pd.read_csv(root/"data/dim_products.csv"); sup = pd.read_csv(root/"data/dim_suppliers.csv")
inv = inv.merge(prod, on="product_id")
inv["rev"] = inv.units_sold*inv.unit_price; inv["cogs"] = inv.units_sold*inv.unit_cost
inv["lost"] = (inv.units_demanded-inv.units_sold)*inv.unit_price

rev, cogs = inv.rev.sum(), inv.cogs.sum()
last = inv[inv.date==inv.date.max()]; inv_val = (last.closing_stock*last.unit_cost).sum()
avg_inv = (inv.assign(v=inv.closing_stock*inv.unit_cost).groupby("date").v.sum()).mean()
turn = cogs/avg_inv
stockout = inv.stockout_flag.mean(); fill = inv.units_sold.sum()/inv.units_demanded.sum()
d = po[po.status=="Delivered"].copy(); d["ontime"] = d.delivery_date<=d.promised_date
d["delay"] = (d.delivery_date-d.promised_date).dt.days.clip(lower=0)
otd = d.ontime.mean()

kpis = [("Revenue", f"${rev/1e6:.1f}M"), ("Inventory Value", f"${inv_val/1e6:.2f}M"),
        ("Inventory Turnover", f"{turn:.1f}x"), ("Stockout Rate", f"{stockout:.1%}"),
        ("Fill Rate", f"{fill:.1%}"), ("On-Time Delivery", f"{otd:.1%}")]

NAVY, TEAL, ORANGE, RED = "#1f3a5f", "#2a9d8f", "#f4a261", "#e76f51"
fig = plt.figure(figsize=(16, 9), facecolor="#f4f6f8")
fig.text(0.03, 0.95, "Supply Chain & Inventory Management Dashboard", fontsize=20, weight="bold", color=NAVY)
fig.text(0.03, 0.92, "FY 2025  |  40 products  |  8 suppliers  (layout preview - build the interactive version in Power BI)", fontsize=10, color="#666")
for i,(k,v) in enumerate(kpis):
    ax = fig.add_axes([0.03+i*0.16, 0.78, 0.145, 0.11]); ax.axis("off")
    ax.add_patch(plt.Rectangle((0,0),1,1,color="white",transform=ax.transAxes,ec="#dde3ea"))
    ax.text(0.5,0.62,v,ha="center",fontsize=20,weight="bold",color=NAVY)
    ax.text(0.5,0.18,k,ha="center",fontsize=10,color="#666")

m = inv.groupby(inv.date.dt.to_period("M")).agg(rev=("rev","sum"), lost=("lost","sum"))
ax = fig.add_axes([0.05,0.44,0.28,0.27]); ax.bar(range(12), m.rev/1e3, color=TEAL, label="Revenue")
ax.plot(range(12), m.lost/1e3, color=RED, marker="o", label="Lost revenue (stockouts)")
ax.set_xticks(range(12)); ax.set_xticklabels(["J","F","M","A","M","J","J","A","S","O","N","D"])
ax.set_title("Monthly Revenue vs Lost Revenue ($K)", loc="left", fontsize=11, color=NAVY); ax.legend(fontsize=8, frameon=False)

c = inv.groupby("product_name").lost.sum().nlargest(8).sort_values()/1e3
ax = fig.add_axes([0.40,0.44,0.26,0.27]); c.plot.barh(ax=ax, color=NAVY)
ax.set_title("Top 8 Products by Lost Revenue ($K)", loc="left", fontsize=11, color=NAVY); ax.set_ylabel("")

so = inv.groupby("category").stockout_flag.mean().sort_values()*100
ax = fig.add_axes([0.73,0.44,0.24,0.27]); so.plot.barh(ax=ax, color=ORANGE)
ax.set_title("Stockout Rate by Category (%)", loc="left", fontsize=11, color=NAVY); ax.set_ylabel("")

s = d.groupby("supplier_id").agg(otd=("ontime","mean"), delay=("delay","mean")).join(sup.set_index("supplier_id")).sort_values("otd")
ax = fig.add_axes([0.12,0.07,0.26,0.27])
ax.barh(s.supplier_name, s.otd*100, color=[RED if x<.6 else ORANGE if x<.8 else TEAL for x in s.otd])
ax.axvline(90, ls="--", color="#999"); ax.set_title("On-Time Delivery % by Supplier (target 90%)", loc="left", fontsize=11, color=NAVY)

ax = fig.add_axes([0.47,0.07,0.22,0.27]); ax.scatter(s.avg_lead_time_days, s.delay, s=120, color=NAVY)
for _,r in s.iterrows(): ax.annotate(r.supplier_name.split()[0], (r.avg_lead_time_days, r.delay), fontsize=7, xytext=(4,4), textcoords="offset points")
ax.set_xlabel("Planned lead time (days)", fontsize=8); ax.set_ylabel("Avg delay (days)", fontsize=8)
ax.set_title("Lead Time vs Delay", loc="left", fontsize=11, color=NAVY)

dd = inv.groupby("date").stockout_flag.sum().rolling(14).mean()
ax = fig.add_axes([0.75,0.07,0.22,0.27]); ax.plot(dd.index, dd.values, color=RED)
ax.set_title("Products Out of Stock (14-day avg)", loc="left", fontsize=11, color=NAVY)
ax.tick_params(axis="x", labelsize=7)

for a in fig.axes:
    for sp in ["top","right"]: a.spines[sp].set_visible(False)
    a.set_facecolor("white")
fig.savefig(root/"images/dashboard_preview.png", dpi=130)
print({k:v for k,v in kpis})
print(d.groupby("supplier_id").ontime.mean().round(2).to_dict())
