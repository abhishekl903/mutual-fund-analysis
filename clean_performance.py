from pathlib import Path
import pandas as pd

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
PROCESSED.mkdir(parents=True, exist_ok=True)

RETURN_COLS = ["return_1yr_pct", "return_3yr_pct", "return_5yr_pct", "benchmark_3yr_pct"]
RETURN_MIN, RETURN_MAX = -50, 100      # plausibility range for annual returns
EXPENSE_MIN, EXPENSE_MAX = 0.1, 2.5    # business rule from the brief


def find_file(keyword):
    matches = [f for f in RAW.glob("*.csv") if keyword in f.name.lower()]
    return matches[0]


def clean_performance():
    raw = pd.read_csv(find_file("scheme_perf"))
    print("Raw shape:", raw.shape)
    print("Exact duplicate rows:", raw.duplicated().sum())
    print("Duplicate amfi_code:", raw["amfi_code"].duplicated().sum())

    df = raw.drop_duplicates().copy()

    # 1. Numeric check on return columns
    for col in RETURN_COLS:
        before_nan = df[col].isna().sum()
        df[col] = pd.to_numeric(df[col], errors="coerce")
        new_nan = df[col].isna().sum() - before_nan
        print(f"{col}: non-numeric values converted to NaN = {new_nan}")

    # 2. Flags
    df["flag_missing_return"] = df[RETURN_COLS].isna().any(axis=1)
    df["flag_return_out_of_range"] = df[RETURN_COLS].apply(
        lambda s: (s < RETURN_MIN) | (s > RETURN_MAX)
    ).any(axis=1)
    df["flag_expense_out_of_range"] = ~df["expense_ratio_pct"].between(EXPENSE_MIN, EXPENSE_MAX)

    print("\n===== FLAGS =====")
    print("Missing returns:", df["flag_missing_return"].sum())
    print("Returns outside", RETURN_MIN, "to", RETURN_MAX, ":", df["flag_return_out_of_range"].sum())
    print("Expense ratio outside", EXPENSE_MIN, "to", EXPENSE_MAX, ":", df["flag_expense_out_of_range"].sum())
    print("Expense ratio min/max:", df["expense_ratio_pct"].min(), "/", df["expense_ratio_pct"].max())

    # 3. Keep rows that pass the hard checks; keep flags as columns for review
    flagged = df[df[["flag_missing_return", "flag_return_out_of_range", "flag_expense_out_of_range"]].any(axis=1)]
    clean = df[~df.index.isin(flagged.index)].copy()

    clean.to_csv(PROCESSED / "scheme_performance_clean.csv", index=False)
    df.to_csv(PROCESSED / "scheme_performance_flagged.csv", index=False)

    print("\n===== CLEAN SUMMARY =====")
    print("Rows before cleaning:", len(raw))
    print("Rows after cleaning:", len(clean))
    print("Rows flagged for review:", len(flagged))
    print("Saved: data/processed/scheme_performance_clean.csv")
    print("Saved: data/processed/scheme_performance_flagged.csv (all rows with flags)")


if __name__ == "__main__":
    clean_performance()