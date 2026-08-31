"""目标函数敏感性检验：把最大化 GMV 换成最大化毛利，看最优分配是否改变。

补贴是从毛利里直接扣掉的：
    每件毛利 = 用户实付 p0(1-s) - 成本 p0(1-m) = p0(m-s)
    总毛利   = R0 (m-s) (1-s)^beta
"""
import os
import sqlite3
import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S_MAX, BUDGET_PCT, MARGIN = 0.10, 0.05, 0.20

conn = sqlite3.connect(os.path.join(ROOT, "data", "ecommerce.db"))
base = pd.read_sql("""
    SELECT CASE
             WHEN category_code = 'electronics.video.tv'   THEN 'electronics.video.tv'
             WHEN category_code = 'electronics.smartphone' THEN 'electronics.smartphone'
             ELSE 'other'
           END AS "group",
           COUNT(*) AS Q0, SUM(price) AS R0
    FROM events
    WHERE event_type = 'purchase' AND price > 0 AND category_code IS NOT NULL
    GROUP BY 1
""", conn)
conn.close()

g = pd.read_csv(os.path.join(ROOT, "output", "elasticity_groups.csv")).merge(base, on="group")
g = g.sort_values("beta").reset_index(drop=True)
R0, BETA = g.R0.values, g.beta.values
SCALE, B = R0.sum(), BUDGET_PCT * R0.sum()

gmv    = lambda s: np.sum(R0 * (1 - s) ** (1 + BETA))
cost   = lambda s: np.sum(R0 * s * (1 - s) ** BETA)
profit = lambda s, m=MARGIN: np.sum(R0 * (m - s) * (1 - s) ** BETA)

def solve(obj, budget=B, smax=S_MAX, m=MARGIN):
    return minimize(
        lambda s: -obj(s, m) / SCALE if obj is profit else -obj(s) / SCALE,
        x0=np.full(len(R0), 0.02), method="SLSQP",
        bounds=[(0.0, smax)] * len(R0),
        constraints=[{"type": "ineq", "fun": lambda s: (budget - cost(s)) / SCALE}],
        options={"maxiter": 500, "ftol": 1e-10})

s_gmv = solve(gmv).x
s_pft = solve(profit).x
base_gmv, base_pft = gmv(np.zeros(len(R0))), profit(np.zeros(len(R0)))

print("=== 两种目标下的最优补贴率对比（毛利率假设 %.0f%%）===" % (MARGIN * 100))
print(pd.DataFrame({
    "组": g.标签, "弹性beta": BETA,
    "最大化GMV_补贴率%": (s_gmv * 100).round(2),
    "最大化毛利_补贴率%": (s_pft * 100).round(2),
}).to_string(index=False))

print("\n最大化 GMV 方案:   GMV %+.2f%%   毛利 %+.2f%%"
      % ((gmv(s_gmv) / base_gmv - 1) * 100, (profit(s_gmv) / base_pft - 1) * 100))
print("最大化毛利方案:    GMV %+.2f%%   毛利 %+.2f%%"
      % ((gmv(s_pft) / base_gmv - 1) * 100, (profit(s_pft) / base_pft - 1) * 100))

# ---- 补贴在毛利上划算的临界条件 ----
# d(毛利)/ds 在 s=0 处 = R0 * (-1 - beta*m)，大于 0 才值得补贴，即 |beta| > 1/m
print("\n=== 补贴值得做的临界毛利率（|beta| > 1/m）===")
print(pd.DataFrame({
    "组": g.标签, "弹性beta": BETA,
    "所需最低毛利率%": (100 / np.abs(BETA)).round(1),
    "20%毛利下是否值得": np.where(np.abs(BETA) > 1 / MARGIN, "是", "否"),
}).to_string(index=False))

# ---- 毛利率敏感性 ----
print("\n=== 毛利率敏感性：不同 m 下的最优补贴率 ===")
rows = []
for m in [0.20, 0.30, 0.40, 0.50]:
    x = solve(profit, m=m).x
    rows.append({"毛利率%": int(m * 100),
                 **{g.标签.iloc[i]: round(x[i] * 100, 2) for i in range(len(R0))},
                 "毛利增幅%": round((profit(x, m) / profit(np.zeros(len(R0)), m) - 1) * 100, 2)})
msens = pd.DataFrame(rows)
print(msens.to_string(index=False))

msens.to_csv(os.path.join(ROOT, "output", "margin_sensitivity.csv"), index=False)
print("\n已保存 -> output/margin_sensitivity.csv")
