"""弹性估计的显著性检验与最优解稳健性检查"""
import os
import sqlite3
import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import minimize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S_MAX = 0.10
BUDGET_PCT = 0.05

elas = pd.read_csv(os.path.join(ROOT, "output", "elasticity_groups.csv"))

# ---------- 1. 两个原假设：beta = 0 和 beta = -1 ----------
# beta=0 回答「有没有价格敏感度」，beta=-1 回答「补贴能不能拉高 GMV」。
# 分配决策用的是后者。
rows = []
for r in elas.itertuples():
    t0 = r.beta / r.SE
    t1 = (r.beta + 1) / r.SE
    rows.append({
        "组": r.标签,
        "beta": r.beta,
        "SE": r.SE,
        "CI下界": round(r.beta - 1.96 * r.SE, 3),
        "CI上界": round(r.beta + 1.96 * r.SE, 3),
        "t(H0:b=0)": round(t0, 2),
        "p(H0:b=0)": round(2 * (1 - stats.norm.cdf(abs(t0))), 4),
        "t(H0:b=-1)": round(t1, 2),
        "p(H0:b=-1)": round(2 * (1 - stats.norm.cdf(abs(t1))), 4),
    })
tests = pd.DataFrame(rows)
print("=== 显著性检验 ===")
print(tests.to_string(index=False))

# ---------- 2. 两两差异 ----------
print("\n=== 组间差异 ===")
diff = []
for i in range(len(elas)):
    for j in range(i + 1, len(elas)):
        a, b = elas.iloc[i], elas.iloc[j]
        d = a.beta - b.beta
        sd = np.sqrt(a.SE ** 2 + b.SE ** 2)
        t = d / sd
        diff.append({"对比": "%s vs %s" % (a.标签, b.标签), "差": round(d, 3),
                     "SE": round(sd, 3), "t": round(t, 2),
                     "p": round(2 * (1 - stats.norm.cdf(abs(t))), 4)})
diff = pd.DataFrame(diff)
print(diff.to_string(index=False))

# ---------- 3. 把不显著的估计换成别的值，看最优解变不变 ----------
conn = sqlite3.connect(os.path.join(ROOT, "data", "ecommerce.db"))
base = pd.read_sql("""
    SELECT CASE
             WHEN category_code = 'electronics.video.tv'   THEN 'electronics.video.tv'
             WHEN category_code = 'electronics.smartphone' THEN 'electronics.smartphone'
             ELSE 'other'
           END AS "group",
           SUM(price) AS R0
    FROM events
    WHERE event_type = 'purchase' AND price > 0 AND category_code IS NOT NULL
    GROUP BY 1
""", conn)
conn.close()

g = elas.merge(base, on="group").sort_values("beta").reset_index(drop=True)
R0 = g.R0.values
B = BUDGET_PCT * R0.sum()
SCALE = R0.sum()
i_other = int(np.where(g["group"] == "other")[0][0])

def solve(BETA):
    gmv = lambda s: np.sum(R0 * (1 - s) ** (1 + BETA))
    cost = lambda s: np.sum(R0 * s * (1 - s) ** BETA)
    res = minimize(lambda s: -gmv(s) / SCALE, x0=np.full(len(R0), 0.02),
                   method="SLSQP", bounds=[(0.0, S_MAX)] * len(R0),
                   constraints=[{"type": "ineq", "fun": lambda s: (B - cost(s)) / SCALE}],
                   options={"maxiter": 500, "ftol": 1e-10})
    s = res.x
    g0 = gmv(np.zeros(len(R0)))
    return s, (gmv(s) / g0 - 1) * 100, (gmv(s) - g0) / cost(s)

print("\n=== 最优解对「其他品类」估计的敏感性 ===")
out = []
for label, val in [("点估计 -0.24", -0.240), ("按不显著处理 0", 0.0), ("CI下界 -0.52", -0.520)]:
    BETA = g.beta.values.copy()
    BETA[i_other] = val
    s, gain, roi = solve(BETA)
    out.append({"其他品类beta": label,
                **{("补贴率_" + g.标签.iloc[k]): round(s[k] * 100, 2) for k in range(len(R0))},
                "GMV增幅%": round(gain, 2), "整体ROI": round(roi, 2)})
out = pd.DataFrame(out)
print(out.to_string(index=False))

tests.to_csv(os.path.join(ROOT, "output", "elasticity_tests.csv"), index=False)
out.to_csv(os.path.join(ROOT, "output", "robustness_checks.csv"), index=False)
print("\n已保存 -> output/elasticity_tests.csv, robustness_checks.csv")
