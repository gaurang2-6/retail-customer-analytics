"""Run the SQL pipeline and export the result tables.

Run from the repo root:  python -m retail.run
Executes sql/01..04 in order on DuckDB, writes reports/retail.duckdb and one CSV
per result table to powerbi/ (the Power BI data source).
"""
from pathlib import Path

import duckdb

from . import load

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
EXPORT_DIR = ROOT / "powerbi" / "data"
DB_PATH = ROOT / "reports" / "retail.duckdb"

EXPORT_TABLES = [
    "cleaning_log", "headline_kpis", "monthly_kpis", "top_countries", "top_products",
    "rfm", "rfm_segments", "revenue_concentration",
    "cohort_retention", "retention_curve", "repeat_purchase",
]


def main():
    load.main()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.unlink(missing_ok=True)
    con = duckdb.connect(str(DB_PATH))
    for path in sorted(SQL_DIR.glob("*.sql")):
        print(f"Running {path.name}")
        con.execute(path.read_text(encoding="utf-8"))
    for table in EXPORT_TABLES:
        con.execute(f"COPY {table} TO '{(EXPORT_DIR / table).as_posix()}.csv' (HEADER)")
    for table in ["cleaning_log", "headline_kpis", "rfm_segments", "revenue_concentration",
                  "retention_curve", "repeat_purchase"]:
        print(f"\n{table}")
        print(con.sql(f"SELECT * FROM {table}").df().to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()
