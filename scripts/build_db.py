"""把抽样数据灌进本地 SQLite 数据库，建好索引。只需要跑一次。

用法（在 ~/ecommerce-project 目录下）：
    python3 scripts/build_db.py
"""
import os, sqlite3, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV = os.path.join(ROOT, "data", "sample_2019_oct.csv.gz")
DB  = os.path.join(ROOT, "data", "ecommerce.db")

conn = sqlite3.connect(DB)
conn.execute("DROP TABLE IF EXISTS events")

total = 0
for i, chunk in enumerate(pd.read_csv(CSV, chunksize=300000, compression="gzip"), 1):
    # 原始 event_time 结尾是 ' UTC'，去掉后 SQLite 的 DATE()/strftime() 才能用
    chunk["event_time"] = chunk["event_time"].str.replace(" UTC", "", regex=False)
    chunk.to_sql("events", conn, if_exists="append", index=False)
    total += len(chunk)
    print("已写入 %d 行" % total, flush=True)

print("建索引 ...")
for s in ["CREATE INDEX idx_user ON events(user_id)",
          "CREATE INDEX idx_type ON events(event_type)",
          "CREATE INDEX idx_time ON events(event_time)",
          "CREATE INDEX idx_cat  ON events(category_code)",
          "CREATE INDEX idx_prod ON events(product_id)",
          "CREATE INDEX idx_user_type ON events(user_id, event_type)"]:
    conn.execute(s)
conn.commit()
print("完成：%d 行 -> %s" % (total, DB))
conn.close()
