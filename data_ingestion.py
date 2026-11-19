from pathlib import Path
import pandas as pd

RAW = Path("data/raw")
CODE_CANDIDATES = ["amfi_code", "scheme_code"]


def find_file(keyword):
    """Return the first CSV in data/raw whose name contains the keyword."""
    matches = [f for f in RAW.glob("*.csv") if keyword in f.name.lower()]
    return matches[0] if matches else None


def code_column(df):
    """Return the scheme code column name, whichever one this file uses."""
    for c in CODE_CANDIDATES:
        if c in df.columns:
            return c
    return None


def load_all():
    files = sorted(RAW.glob("*.csv"))
    print(f"Found {len(files)} CSV files in {RAW}\n")
    frames = {}
    for f in files:
        df = pd.read_csv(f)
        frames[f.name] = df

        print("=" * 60)
        print(f"FILE: {f.name}")
        print("shape:", df.shape)
        print("dtypes:\n", df.dtypes)
        print("head:\n", df.head(), "\n")

        nulls = df.isna().sum()
        nulls = nulls[nulls > 0]
        dupes = df.duplicated().sum()
        print(f"Anomalies -> missing values: {dict(nulls) if len(nulls) else 'none'}, "
              f"duplicate rows: {dupes}\n")
    return frames


def explore_fund_master(frames):
    name = find_file("fund_master")
    if name is None:
        print("No fund_master file found.")
        return None
    fm = frames[name.name]
    print("=" * 60)
    print("FUND MASTER EXPLORATION")
    print("Columns:", list(fm.columns))

    for col in ["fund_house", "category", "sub_category"]:
        if col in fm.columns:
            print(f"\nUnique {col} ({fm[col].nunique()}):")
            print(fm[col].value_counts(dropna=False).to_string())

    code_col = code_column(fm)
    if code_col:
        codes = fm[code_col].astype(str)
        print(f"\nCode column: {code_col}")
        print("Code length range:", codes.str.len().min(), "to", codes.str.len().max())
    return fm


def validate_amfi_codes(frames, fund_master):
    nav_file = find_file("nav_history")
    if nav_file is None or fund_master is None:
        print("Skipping AMFI validation: nav_history or fund_master missing.")
        return
    nav = frames[nav_file.name]
    master_col = code_column(fund_master)
    nav_col = code_column(nav)
    if master_col is None or nav_col is None:
        print("Skipping AMFI validation: no code column found.")
        return

    master_codes = set(fund_master[master_col].astype(str))
    nav_codes = set(nav[nav_col].astype(str))

    missing_in_nav = master_codes - nav_codes
    missing_in_master = nav_codes - master_codes

    print("\n" + "=" * 60)
    print("AMFI CODE VALIDATION")
    print(f"Codes in fund_master: {len(master_codes)}")
    print(f"Codes in nav_history: {len(nav_codes)}")
    print(f"Fund master codes with no NAV data: {len(missing_in_nav)} {sorted(missing_in_nav)[:10]}")
    print(f"NAV codes not in fund master: {len(missing_in_master)} {sorted(missing_in_master)[:10]}")


if __name__ == "__main__":
    frames = load_all()
    fund_master = explore_fund_master(frames)
    validate_amfi_codes(frames, fund_master)