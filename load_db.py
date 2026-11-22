import sqlite3
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
DB_PATH = PROCESSED / "bluestock_mf.db"
SCHEMA_PATH = Path("sql/schema.sql")


def find_raw(keyword):
    return [f for f in RAW.glob("*.csv") if keyword in f.name.lower()][0]


def build_dim_date():
    dates = pd.date_range("2022-01-01", "2026-12-31", freq="D")
    dd = pd.DataFrame({"date": dates})
    dd["year"] = dd["date"].dt.year
    dd["month"] = dd["date"].dt.month
    dd["month_name"] = dd["date"].dt.strftime("%B")
    dd["quarter"] = dd["date"].dt.quarter
    dd["year_month"] = dd["date"].dt.strftime("%Y-%m")
    dd["is_weekend"] = (dd["date"].dt.dayofweek >= 5).astype(int)
    dd["date"] = dd["date"].dt.strftime("%Y-%m-%d")
    return dd


def prep_fund_master():
    fm = pd.read_csv(find_raw("fund_master"))
    cols = ["amfi_code", "fund_house", "scheme_name", "category", "sub_category",
            "plan", "launch_date", "benchmark", "exit_load_pct", "min_sip_amount",
            "min_lumpsum_amount", "fund_manager", "risk_category", "sebi_category_code"]
    fm = fm[cols].drop_duplicates(subset="amfi_code")
    fm["amfi_code"] = fm["amfi_code"].astype(int)
    return fm


def prep_nav():
    nav = pd.read_csv(PROCESSED / "nav_history_clean.csv")
    nav["date"] = pd.to_datetime(nav["date"]).dt.strftime("%Y-%m-%d")
    return nav[["amfi_code", "date", "nav", "nav_filled"]]


def prep_transactions():
    tx = pd.read_csv(PROCESSED / "investor_transactions_clean.csv")
    tx["transaction_date"] = pd.to_datetime(tx["transaction_date"]).dt.strftime("%Y-%m-%d")
    tx.insert(0, "transaction_id", range(1, len(tx) + 1))
    return tx


def prep_performance():
    p = pd.read_csv(PROCESSED / "scheme_performance_clean.csv")
    cols = ["amfi_code", "return_1yr_pct", "return_3yr_pct", "return_5yr_pct",
            "benchmark_3yr_pct", "alpha", "beta", "sharpe_ratio", "sortino_ratio",
            "std_dev_ann_pct", "max_drawdown_pct", "aum_crore", "expense_ratio_pct",
            "morningstar_rating", "risk_grade"]
    return p[cols]


def prep_aum():
    aum = pd.read_csv(find_raw("aum_by"))
    aum["date"] = pd.to_datetime(aum["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    aum["fund_house"] = aum["fund_house"].str.strip()
    aum = aum[["date", "fund_house", "aum_crore", "num_schemes"]]
    return aum.drop_duplicates(subset=["date", "fund_house"])


def main():
    dim_date = build_dim_date()
    dim_fund = prep_fund_master()
    fact_nav = prep_nav()
    fact_tx = prep_transactions()
    fact_perf = prep_performance()
    fact_aum = prep_aum()

    # Link checks (SQLite does not enforce foreign keys by default)
    fund_codes = set(dim_fund["amfi_code"])
    date_set = set(dim_date["date"])
    print("Orphan checks (rows pointing to a missing key):")
    print("  fact_nav amfi_code:", (~fact_nav["amfi_code"].isin(fund_codes)).sum())
    print("  fact_transactions amfi_code:", (~fact_tx["amfi_code"].isin(fund_codes)).sum())
    print("  fact_transactions date:", (~fact_tx["transaction_date"].isin(date_set)).sum())
    print("  fact_performance amfi_code:", (~fact_perf["amfi_code"].isin(fund_codes)).sum())
    print("  fact_aum date:", (~fact_aum["date"].isin(date_set)).sum())

    # Create the database from schema.sql
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()
    conn.close()

    # Load in order: dimensions first, then facts
    tables = [
        ("dim_date", dim_date),
        ("dim_fund", dim_fund),
        ("fact_nav", fact_nav),
        ("fact_transactions", fact_tx),
        ("fact_performance", fact_perf),
        ("fact_aum", fact_aum),
    ]
    engine = create_engine(f"sqlite:///{DB_PATH}")
    for name, df in tables:
        df.to_sql(name, engine, if_exists="append", index=False, chunksize=5000)
        print(f"Loaded {name}: {len(df)} rows")

    # Verify row counts in the database
    print("\nRow count verification:")
    with engine.connect() as conn:
        for name, df in tables:
            n = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {name}").scalar()
            status = "OK" if n == len(df) else "MISMATCH"
            print(f"  {name}: DB={n}, DataFrame={len(df)} -> {status}")

    print("\nSaved: data/processed/bluestock_mf.db")


if __name__ == "__main__":
    main()