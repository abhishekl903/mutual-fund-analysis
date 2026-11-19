import requests
import pandas as pd
from pathlib import Path

OUT = Path("data/raw")
OUT.mkdir(parents=True, exist_ok=True)

SCHEMES = {
    "hdfc_top100_direct": 125497,
    "sbi_bluechip": 119551,
    "icici_bluechip": 120503,
    "nippon_large_cap": 118632,
    "axis_bluechip": 119092,
    "kotak_bluechip": 120841,
}


def fetch_nav(code):
    url = f"https://api.mfapi.in/mf/{code}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    payload = response.json()

    meta = payload.get("meta", {})
    df = pd.DataFrame(payload["data"])
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df.insert(0, "scheme_code", code)
    df.insert(1, "scheme_name", meta.get("scheme_name"))
    return df.sort_values("date").reset_index(drop=True)


if __name__ == "__main__":
    for label, code in SCHEMES.items():
        try:
            df = fetch_nav(code)
            path = OUT / f"nav_{label}_{code}.csv"
            df.to_csv(path, index=False)
            print(f"{label}: {len(df)} rows, {df['date'].min().date()} to {df['date'].max().date()} -> {path}")
        except Exception as e:
            print(f"{label} ({code}) failed: {e}")