from pathlib import Path
import pandas as pd

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
PROCESSED.mkdir(parents=True, exist_ok=True)

TYPE_MAP = {
    "sip": "SIP",
    "systematic investment": "SIP",
    "lumpsum": "Lumpsum",
    "lump sum": "Lumpsum",
    "lump-sum": "Lumpsum",
    "lump_sum": "Lumpsum",
    "redemption": "Redemption",
    "redeem": "Redemption",
}
VALID_KYC = {"Verified", "Pending"}


def find_file(keyword):
    matches = [f for f in RAW.glob("*.csv") if keyword in f.name.lower()]
    return matches[0]


def clean_investor():
    raw = pd.read_csv(find_file("investor_t"))
    print("Raw shape:", raw.shape)
    print("Exact duplicate rows:", raw.duplicated().sum())

    df = raw.drop_duplicates().copy()

    # 1. Transaction type
    raw_type = df["transaction_type"].astype(str).str.strip().str.lower()
    df["transaction_type"] = raw_type.map(TYPE_MAP)
    unmapped = raw_type[df["transaction_type"].isna()]
    print("\nUnmapped transaction_type values:", len(unmapped))
    if len(unmapped):
        print(unmapped.value_counts().to_string())

    # 2. Date
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")

    # 3. Amount
    df["amount_inr"] = pd.to_numeric(df["amount_inr"], errors="coerce")

    # 4. KYC
    df["kyc_status"] = df["kyc_status"].astype(str).str.strip().str.title()

    # Validation flags
    bad_type = df["transaction_type"].isna()
    bad_date = df["transaction_date"].isna()
    bad_amount = df["amount_inr"].isna() | (df["amount_inr"] <= 0)
    bad_kyc = ~df["kyc_status"].isin(VALID_KYC)
    bad_any = bad_type | bad_date | bad_amount | bad_kyc

    print("\nBad transaction_type:", bad_type.sum())
    print("Bad date:", bad_date.sum())
    print("Bad amount (missing or <= 0):", bad_amount.sum())
    print("Bad KYC status:", bad_kyc.sum())
    if bad_kyc.sum():
        print(df.loc[bad_kyc, "kyc_status"].value_counts().to_string())

    clean = df[~bad_any].copy()
    clean.to_csv(PROCESSED / "investor_transactions_clean.csv", index=False)

    print("\n===== CLEAN SUMMARY =====")
    print("Rows before cleaning:", len(raw))
    print("Rows after cleaning:", len(clean))
    print("Rows removed:", len(raw) - len(clean))
    print("Transaction types:\n", clean["transaction_type"].value_counts().to_string())
    print("KYC status:\n", clean["kyc_status"].value_counts().to_string())
    print("Date range:", clean["transaction_date"].min().date(), "to", clean["transaction_date"].max().date())
    print("Saved: data/processed/investor_transactions_clean.csv")


if __name__ == "__main__":
    clean_investor()