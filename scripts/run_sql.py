"""跑 SQL 的小工具（备用；平时建议直接用 sqlite3 命令行更快）。

用法（在 ~/ecommerce-project 目录下）：
    python3 scripts/run_sql.py sql/01_data_quality.sql
    python3 scripts/run_sql.py "SELECT COUNT(*) FROM events"
"""
import os, sys, sqlite3, pandas as pd

pd.set_option("display.max_rows", 80)
pd.set_option("display.width", 200)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "data", "ecommerce.db")

arg = " ".join(sys.argv[1:])
sql_text = open(arg, encoding="utf-8").read() if os.path.isfile(arg) else arg
stmts = [s.strip() for s in sql_text.split(";") if s.strip()]

conn = sqlite3.connect(DB)
for i, s in enumerate(stmts, 1):
    if len(stmts) > 1:
        print("\n" + "=" * 70 + "\n[查询 %d]\n" % i + "=" * 70)
    try:
        print(pd.read_sql(s, conn).to_string(index=False))
    except Exception as e:
        print("报错：%s" % e)
conn.close()
