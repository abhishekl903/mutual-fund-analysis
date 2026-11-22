from pathlib import Path
import pandas as pd

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
PROCESSED.mkdir(parents=True, exist_ok=True)


def find_file(keyword):
    matches = [f for f in RAW.glob("*.csv") if keyword in f.name.lower()]
    return matches[0]


def clean_nav():
    raw = pd.read_csv(find_file("nav_history"))
    print("Raw shape:", raw.shape)
    print("Raw dtypes:\n", raw.dtypes)

    df = raw.copy()
    df["amfi_code"] = df["amfi_code"].astype(str).str.strip()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")

    # Validation report before cleaning
    print("\nBad dates:", df["date"].isna().sum())
    print("Missing NAV:", df["nav"].isna().sum())
    print("NAV <= 0:", (df["nav"] <= 0).sum())
    print("Exact duplicate rows:", df.duplicated().sum())
    print("Duplicate amfi_code + date:", df.duplicated(["amfi_code", "date"]).sum())

    # Remove bad rows and duplicates
    df = df.dropna(subset=["date"])
    df = df[df["nav"] > 0]
    df = df.drop_duplicates(subset=["amfi_code", "date"])
    df = df.sort_values(["amfi_code", "date"])

    # Build a full daily calendar per fund and forward-fill weekends and holidays
    frames = []
    for code, g in df.groupby("amfi_code"):
        g = g.set_index("date").sort_index()
        full_range = pd.date_range(g.index.min(), g.index.max(), freq="D")
        g = g.reindex(full_range)
        g["amfi_code"] = code
        g["nav_filled"] = g["nav"].isna()
        g["nav"] = g["nav"].ffill()
        frames.append(g.rename_axis("date").reset_index())

    clean = pd.concat(frames, ignore_index=True)
    clean = clean[["amfi_code", "date", "nav", "nav_filled"]]
    clean.to_csv(PROCESSED / "nav_history_clean.csv", index=False)

    print("\n===== CLEAN SUMMARY =====")
    print("Rows before cleaning:", len(raw))
    print("Rows after daily fill:", len(clean))
    print("Funds:", clean["amfi_code"].nunique())
    print("Filled rows (weekends/holidays):", clean["nav_filled"].sum())
    print("Date range:", clean["date"].min().date(), "to", clean["date"].max().date())
    print("Saved: data/processed/nav_history_clean.csv")


if __name__ == "__main__":
    clean_nav()