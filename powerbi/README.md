# Power BI dashboard

`python -m retail.run` writes the result tables as CSVs to `powerbi/data/`. The dashboard is built
on those CSVs, so all the cleaning and business logic stays in SQL and the report only
handles the visuals.

## Build it (Power BI Desktop, free)

1. **Get data → Text/CSV**, and load these files from `powerbi/data/`:
   `monthly_kpis`, `headline_kpis`, `top_countries`, `top_products`, `rfm`, `rfm_segments`,
   `cohort_retention`, `retention_curve`.
2. In Power Query, set `invoice_month` and `cohort_month` to **Date** and `is_partial_month` to
   **True/False**.
3. Add the measures below to `monthly_kpis` and `rfm`.
4. Build the two pages described below, then save the file as `powerbi/retail_dashboard.pbix`.
5. Export each page as a PNG (**File → Export → PDF**, or a screenshot) to
   `reports/figures/powerbi_kpi.png` and `reports/figures/powerbi_segments.png`, and link them
   in the main README.

There are no relationships between the tables: each visual reads from one table.

## DAX measures

```DAX
-- monthly_kpis
Revenue          = SUM ( monthly_kpis[revenue] )
Orders           = SUM ( monthly_kpis[orders] )
AOV              = DIVIDE ( [Revenue], [Orders] )
New Customers    = SUM ( monthly_kpis[new_customers] )

-- Complete months only (Dec 2011 holds just 9 days)
Revenue (complete months) =
    CALCULATE ( [Revenue], monthly_kpis[is_partial_month] = FALSE () )

Revenue YoY % =
VAR cur  = [Revenue]
VAR prev = CALCULATE ( [Revenue], DATEADD ( monthly_kpis[invoice_month], -12, MONTH ) )
RETURN DIVIDE ( cur - prev, prev )

-- rfm
Customers        = COUNTROWS ( rfm )
Net Revenue      = SUM ( rfm[monetary] )
Revenue Share    = DIVIDE ( [Net Revenue], CALCULATE ( [Net Revenue], ALL ( rfm[segment] ) ) )
Customer Share   = DIVIDE ( [Customers], CALCULATE ( [Customers], ALL ( rfm[segment] ) ) )
Median Recency   = MEDIAN ( rfm[recency_days] )
```

`DATEADD` needs a continuous date column. If it complains, use the precomputed
`monthly_kpis[revenue_yoy_pct]` column instead, which SQL already calculated with `lag(…, 12)`.

## Page 1: KPIs

| Area | Visual | Fields |
|---|---|---|
| Top row | 5 cards | `headline_kpis`: total_revenue, orders, customers, avg_order_value, return_rate_pct |
| Middle, left | Line chart | x `invoice_month`, y `[Revenue]`. Filter out `is_partial_month = True`, or note it in a subtitle |
| Middle, right | Column chart | x `invoice_month`, y `[New Customers]`: its own chart, **not** a second axis on the revenue line |
| Bottom, left | Bar chart | `top_countries`: country by revenue |
| Bottom, right | Table | `top_products`: description, units, revenue, revenue_share_pct |
| Slicer | Date range | `monthly_kpis[invoice_month]` |

## Page 2: Customer segments

| Area | Visual | Fields |
|---|---|---|
| Top row | 3 cards | Champions revenue share, At Risk (high value) customers, repeat rate (from `repeat_purchase.csv`) |
| Left | Clustered bar | y `rfm[segment]`, x `[Customer Share]` and `[Revenue Share]` |
| Right | Table | `rfm_segments`: all columns, sorted by revenue |
| Bottom, left | Matrix (heatmap) | rows `cohort_month`, columns `months_since_first` (1–12), values `retention_pct`; conditional formatting with a single-hue background scale |
| Bottom, right | Line chart | `retention_curve`: months_since_first 1–18 by retention_pct |
| Slicer | Segment, country | `rfm[segment]`, `rfm[country]` |

The segment-to-action table from the main README ("Recommendations") can go on this page as a text box.

## Colours

The same palette as the Python charts, so the dashboard and the README look like one project:
blue `#2a78d6` for series 1, orange `#eb6834` for series 2, ink `#0b0b0b` / `#52514e` for
text, and a single blue scale for the cohort heatmap.
