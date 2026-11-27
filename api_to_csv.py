from pathlib import Path
import pandas as pd
import requests

URL = "https://api.mfapi.in/mf/125497"
OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)

response = requests.get(URL, timeout=30)
response.raise_for_status()
payload = response.json()

meta = payload["meta"]
df = pd.DataFrame(payload["data"])
df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
df.insert(0, "scheme_code", meta["scheme_code"])
df.insert(1, "scheme_name", meta["scheme_name"])
df = df.sort_values("date")

print("Scheme from API:", meta["scheme_name"])
print("Rows:", len(df))
print("Date range:", df["date"].min().date(), "to", df["date"].max().date())
print(df.head())

df.to_csv(OUT / "api_response_125497.csv", index=False)
print("Saved: data/processed/api_response_125497.csv")