import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path("data/processed/bluestock_mf.db")
SQL_PATH = Path("sql/queries.sql")

queries = [q.strip() for q in SQL_PATH.read_text().split(";") if q.strip()]
conn = sqlite3.connect(DB_PATH)

for i, q in enumerate(queries, 1):
    print(f"\n===== Query {i} =====")
    df = pd.read_sql_query(q, conn)
    print(df.head(10).to_string(index=False) if len(df) else "No rows returned")
    print(f"Rows returned: {len(df)}")

conn.close()