// =====================================================
// Power Query (M) - paste each block in Advanced Editor
// Replace the folder path with where you cloned the repo
// =====================================================

// ---------- fact_inventory_daily ----------
let
    Source = Csv.Document(File.Contents("C:\supply-chain-dashboard\data\fact_inventory_daily.csv"),
                [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"date", type date}, {"product_id", type text},
        {"units_demanded", Int64.Type}, {"units_sold", Int64.Type},
        {"closing_stock", Int64.Type}, {"stockout_flag", Int64.Type}}),
    NoNulls = Table.SelectRows(Typed, each [date] <> null and [product_id] <> null)
in
    NoNulls

// ---------- fact_purchase_orders ----------
let
    Source = Csv.Document(File.Contents("C:\supply-chain-dashboard\data\fact_purchase_orders.csv"),
                [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"po_id", type text}, {"supplier_id", type text}, {"product_id", type text},
        {"order_date", type date}, {"promised_date", type date}, {"delivery_date", type date},
        {"qty_ordered", Int64.Type}, {"qty_received", Int64.Type},
        {"unit_cost", type number}, {"status", type text}}),
    // Days late for delivered POs (0 if on time)
    AddDelay = Table.AddColumn(Typed, "delay_days",
        each if [delivery_date] = null then null
             else List.Max({0, Duration.Days([delivery_date] - [promised_date])}), Int64.Type)
in
    AddDelay

// ---------- dim_products ----------
let
    Source = Csv.Document(File.Contents("C:\supply-chain-dashboard\data\dim_products.csv"),
                [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"product_id", type text}, {"product_name", type text}, {"category", type text},
        {"unit_cost", type number}, {"unit_price", type number},
        {"avg_daily_demand", Int64.Type}, {"supplier_id", type text},
        {"reorder_point", Int64.Type}, {"order_quantity", Int64.Type}})
in
    Typed

// ---------- dim_suppliers ----------
let
    Source = Csv.Document(File.Contents("C:\supply-chain-dashboard\data\dim_suppliers.csv"),
                [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"supplier_id", type text}, {"supplier_name", type text},
        {"region", type text}, {"avg_lead_time_days", Int64.Type}})
in
    Typed
