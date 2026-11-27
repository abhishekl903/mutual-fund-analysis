from pathlib import Path
import sqlite3
import pandas as pd
from sqlalchemy import create_engine

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
DB_PATH = PROCESSED / "bluestock_mf.db"
SCHEMA_PATH = Path("sql/schema.sql")

TYPE_MAP = {
    "sip": "SIP", "lumpsum": "Lumpsum", "lump sum": "Lumpsum",
    "lump-sum": "Lumpsum", "redemption": "Redemption", "redeem": "Redemption",
}
VALID_KYC = {"Verified", "Pending"}

TX_COLS = ["transaction_id", "investor_id", "transaction_date", "amfi_code", "transaction_type",
           "amount_inr", "state", "city", "city_tier", "age_group", "gender",
           "annual_income_lakh", "payment_mode", "kyc_status"]
PERF_COLS = ["amfi_code", "return_1yr_pct", "return_3yr_pct", "return_5yr_pct",
             "benchmark_3yr_pct", "alpha", "beta", "sharpe_ratio", "sortino_ratio",
             "std_dev_ann_pct", "max_drawdown_pct", "aum_crore", "expense_ratio_pct",
             "morningstar_rating", "risk_grade"]
FUND_COLS = ["amfi_code", "fund_house", "scheme_name", "category", "sub_category", "plan",
             "launch_date", "benchmark", "exit_load_pct", "min_sip_amount",
             "min_lumpsum_amount", "fund_manager", "risk_category", "sebi_category_code"]


def find_raw(keyword):
    return [f for f in RAW.glob("*.csv") if keyword in f.name.lower()][0]


# ---------- TRANSFORM ----------

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


def build_dim_fund():
    fm = pd.read_csv(find_raw("fund_master"))
    fm = fm[FUND_COLS].drop_duplicates(subset="amfi_code").copy()
    fm["amfi_code"] = fm["amfi_code"].astype(int)
    return fm


def build_fact_nav():
    df = pd.read_csv(find_raw("nav_history"))
    df["amfi_code"] = df["amfi_code"].astype(str).str.strip().astype(int)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["date", "nav"])
    df = df[df["nav"] > 0].drop_duplicates(subset=["amfi_code", "date"])
    df = df.sort_values(["amfi_code", "date"])

    frames = []
    for code, g in df.groupby("amfi_code"):
        g = g.set_index("date").sort_index()
        full = pd.date_range(g.index.min(), g.index.max(), freq="D")
        g = g.reindex(full)
        g["amfi_code"] = code
        g["nav_filled"] = g["nav"].isna().astype(int)
        g["nav"] = g["nav"].ffill()
        frames.append(g.rename_axis("date").reset_index())

    out = pd.concat(frames, ignore_index=True)[["amfi_code", "date", "nav", "nav_filled"]]
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")
    return out


def build_fact_transactions():
    tx = pd.read_csv(find_raw("investor_t")).drop_duplicates().copy()
    tx["transaction_type"] = tx["transaction_type"].astype(str).str.strip().str.lower().map(TYPE_MAP)
    tx["transaction_date"] = pd.to_datetime(tx["transaction_date"], errors="coerce")
    tx["amount_inr"] = pd.to_numeric(tx["amount_inr"], errors="coerce")
    tx["kyc_status"] = tx["kyc_status"].astype(str).str.strip().str.title()

    ok = (tx["transaction_type"].notna() & tx["transaction_date"].notna()
          & (tx["amount_inr"] > 0) & tx["kyc_status"].isin(VALID_KYC))
    tx = tx[ok].copy()
    tx["transaction_date"] = tx["transaction_date"].dt.strftime("%Y-%m-%d")
    tx["amfi_code"] = tx["amfi_code"].astype(int)
    tx.insert(0, "transaction_id", range(1, len(tx) + 1))
    return tx[TX_COLS]


def build_fact_performance():
    p = pd.read_csv(find_raw("scheme_perf")).drop_duplicates().copy()
    ret_cols = ["return_1yr_pct", "return_3yr_pct", "return_5yr_pct", "benchmark_3yr_pct"]
    for c in ret_cols:
        p[c] = pd.to_numeric(p[c], errors="coerce")
    ok = (p[ret_cols].notna().all(axis=1)
          & p[ret_cols].apply(lambda s: s.between(-50, 100)).all(axis=1)
          & p["expense_ratio_pct"].between(0.1, 2.5))
    return p[ok][PERF_COLS].copy()


def build_fact_aum():
    aum = pd.read_csv(find_raw("aum_by"))
    aum["date"] = pd.to_datetime(aum["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    aum["fund_house"] = aum["fund_house"].astype(str).str.strip()
    aum = aum[["date", "fund_house", "aum_crore", "num_schemes"]]
    return aum.drop_duplicates(subset=["date", "fund_house"])


def build_fact_sip():
    sip = pd.read_csv(find_raw("monthly_sip")).drop_duplicates().copy()
    sip = sip.rename(columns={"month": "sip_month"})
    return sip[["sip_month", "sip_inflow_crore", "active_sip_accounts_crore",
                "new_sip_accounts_lakh", "sip_aum_lakh_crore", "yoy_growth_pct"]]


# ---------- LOAD ----------

def create_database():
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()
    conn.close()


def check_links(tables):
    funds = set(tables["dim_fund"]["amfi_code"])
    dates = set(tables["dim_date"]["date"])
    print("\nLink checks (should all be 0):")
    print("  fact_nav amfi_code:", (~tables["fact_nav"]["amfi_code"].isin(funds)).sum())
    print("  fact_transactions amfi_code:", (~tables["fact_transactions"]["amfi_code"].isin(funds)).sum())
    print("  fact_transactions date:", (~tables["fact_transactions"]["transaction_date"].isin(dates)).sum())
    print("  fact_performance amfi_code:", (~tables["fact_performance"]["amfi_code"].isin(funds)).sum())
    print("  fact_aum date:", (~tables["fact_aum"]["date"].isin(dates)).sum())


def main():
    PROCESSED.mkdir(parents=True, exist_ok=True)

    print("Transforming...")
    tables = {
        "dim_date": build_dim_date(),
        "dim_fund": build_dim_fund(),
        "fact_nav": build_fact_nav(),
        "fact_transactions": build_fact_transactions(),
        "fact_performance": build_fact_performance(),
        "fact_aum": build_fact_aum(),
        "fact_sip": build_fact_sip(),
    }
    check_links(tables)

    print("\nCreating database from schema.sql...")
    create_database()

    engine = create_engine(f"sqlite:///{DB_PATH}")
    print("\nLoading tables:")
    for name, df in tables.items():
        df.to_sql(name, engine, if_exists="append", index=False, chunksize=5000)
        print(f"  {name}: {len(df)} rows")

    print("\nVerifying row counts in the database:")
    with engine.connect() as conn:
        for name, df in tables.items():
            n = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {name}").scalar()
            status = "OK" if n == len(df) else "MISMATCH"
            print(f"  {name}: DB={n}, DataFrame={len(df)} -> {status}")

    print("\nDone. Database saved to data/processed/bluestock_mf.db")


if __name__ == "__main__":
    main()