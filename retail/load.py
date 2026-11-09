"""Download Online Retail II (UCI) and convert both Excel sheets to one Parquet file.

Run from the repo root:  python -m retail.load
"""
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
XLSX = DATA / "online_retail_II.xlsx"
PARQUET = DATA / "online_retail_ii.parquet"


def main():
    DATA.mkdir(exist_ok=True)
    if PARQUET.exists():
        print(f"{PARQUET.name} already exists")
        return
    if not XLSX.exists():
        zip_path = DATA / "online_retail_ii.zip"
        print("Downloading Online Retail II (45 MB)...")
        urllib.request.urlretrieve(URL, zip_path)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(DATA)
    print("Reading both Excel sheets (takes ~2 minutes)...")
    sheets = pd.read_excel(XLSX, sheet_name=None, dtype={"Invoice": str, "StockCode": str, "Description": str})
    df = pd.concat(sheets.values(), ignore_index=True)
    df.columns = ["invoice", "stock_code", "description", "quantity", "invoice_date",
                  "price", "customer_id", "country"]
    df["customer_id"] = df["customer_id"].astype("Int64")
    df.to_parquet(PARQUET, index=False)
    print(f"Wrote {len(df):,} rows to {PARQUET.name}")


if __name__ == "__main__":
    main()
