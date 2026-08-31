import argparse, hashlib, time
import pandas as pd

_memo = {}

def keep_user(uid, pct):
    if uid not in _memo:
        _memo[uid] = int(hashlib.md5(str(uid).encode()).hexdigest(), 16) % 100 < pct
    return _memo[uid]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--pct", type=int, default=5)
    p.add_argument("--chunksize", type=int, default=1000000)
    a = p.parse_args()

    t0, rows_in, rows_out, first = time.time(), 0, 0, True
    print("reading " + a.input)

    for i, chunk in enumerate(pd.read_csv(a.input, chunksize=a.chunksize, compression="infer"), 1):
        rows_in += len(chunk)
        keep_ids = {u for u in chunk["user_id"].unique() if keep_user(u, a.pct)}
        sampled = chunk[chunk["user_id"].isin(keep_ids)]
        rows_out += len(sampled)
        sampled.to_csv(a.output, mode="w" if first else "a", header=first,
                       index=False, compression="infer")
        first = False
        print("chunk %d: read %d rows, kept %d rows, %.0fs" % (i, rows_in, rows_out, time.time()-t0), flush=True)

    print("\nDONE. %d rows -> %d rows (%.1f%%). Output: %s" % (rows_in, rows_out, rows_out/rows_in*100, a.output))

if __name__ == "__main__":
    main()
