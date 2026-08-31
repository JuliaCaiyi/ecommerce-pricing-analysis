"""预算约束下的补贴分配优化：最大化 GMV"""
import os
import sqlite3
import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S_MAX = 0.10          # 补贴率上限，见脚本说明
BUDGET_PCT = 0.05     # 预算 = 基准 GMV 的 5%

# ---------- 1. 基准盘：从全量成交数据算每组的当前 GMV ----------
# 用 ecommerce.db 的全部 purchase 事件，而不是弹性面板的子集，
# 因为基准 GMV 要反映平台真实规模。
conn = sqlite3.connect(os.path.join(ROOT, "data", "ecommerce.db"))
base = pd.read_sql("""
    SELECT CASE
             WHEN category_code = 'electronics.video.tv'   THEN 'electronics.video.tv'
             WHEN category_code = 'electronics.smartphone' THEN 'electronics.smartphone'
             ELSE 'other'
           END AS "group",
           COUNT(*)   AS Q0,
           SUM(price) AS R0,
           AVG(price) AS p0
    FROM events
    WHERE event_type = 'purchase' AND price > 0 AND category_code IS NOT NULL
    GROUP BY 1
""", conn)
conn.close()

elas = pd.read_csv(os.path.join(ROOT, "output", "elasticity_groups.csv"))
g = elas.merge(base, on="group")
g = g.sort_values("beta").reset_index(drop=True)

R0 = g.R0.values
BETA = g.beta.values
B = BUDGET_PCT * R0.sum()

print("=== 基准盘 ===")
print(g[["标签", "beta", "Q0", "R0", "p0"]].to_string(index=False))
print("\n基准 GMV 合计 %.0f 美元，补贴预算 B = %.0f 美元（%.0f%%）\n"
      % (R0.sum(), B, BUDGET_PCT * 100))

# ---------- 2. 模型 ----------
def gmv(s):
    """补贴后总 GMV = sum R0 * (1-s)^(1+beta)"""
    return np.sum(R0 * (1 - s) ** (1 + BETA))

def cost(s):
    """补贴总支出 = sum R0 * s * (1-s)^beta，销量用补贴后的"""
    return np.sum(R0 * s * (1 - s) ** BETA)

SCALE = R0.sum()   # 归一化因子：把目标和约束缩到 0-1 量级

def solve(budget, smax=S_MAX):
    """SLSQP 求解。目标函数与约束都除以 SCALE。
    不做归一化时目标值在 1e7 量级，而 s 在 0-0.1，有限差分梯度会被数值噪声淹没，
    求解器会在初值处误判收敛。"""
    res = minimize(
        lambda s: -gmv(s) / SCALE,                           # 最大化 GMV = 最小化 -GMV
        x0=np.full(len(R0), 0.02),                           # 初值：均匀小额补贴
        method="SLSQP",
        bounds=[(0.0, smax)] * len(R0),                      # 0 <= s_i <= s_max
        constraints=[{"type": "ineq",
                      "fun": lambda s: (budget - cost(s)) / SCALE}],
        options={"maxiter": 500, "ftol": 1e-10},
    )
    return res


def grid_check(budget, smax=S_MAX, n=41):
    """粗网格暴力搜索，用来交叉验证 SLSQP 的解没有落在局部最优。"""
    best, best_v = None, -np.inf
    grid = np.linspace(0, smax, n)
    for a in grid:
        for b_ in grid:
            for c in [0.0, smax / 2, smax]:
                s = np.array([a, b_, c])
                if cost(s) <= budget and gmv(s) > best_v:
                    best, best_v = s, gmv(s)
    return best

# ---------- 3. 基线：均匀补贴（所有组同一个补贴率，花光同样预算） ----------
from scipy.optimize import brentq
uniform_rate = brentq(lambda x: cost(np.full(len(R0), x)) - B, 1e-9, S_MAX)
s_uniform = np.full(len(R0), uniform_rate)

# ---------- 4. 求解并对比 ----------
res = solve(B)
s_opt = res.x
base_gmv = gmv(np.zeros(len(R0)))

print("=== 最优补贴分配（目标：最大化 GMV）===")
out = pd.DataFrame({
    "组": g.标签,
    "弹性beta": BETA,
    "基准GMV": R0.round(0),
    "最优补贴率": (s_opt * 100).round(2),
    "分配预算": (R0 * s_opt * (1 - s_opt) ** BETA).round(0),
    "预算占比%": (R0 * s_opt * (1 - s_opt) ** BETA / B * 100).round(1),
    "GMV增量": (R0 * ((1 - s_opt) ** (1 + BETA) - 1)).round(0),
    "补贴ROI": np.where(s_opt > 1e-6,
                       R0 * ((1 - s_opt) ** (1 + BETA) - 1)
                       / np.maximum(R0 * s_opt * (1 - s_opt) ** BETA, 1e-9), 0).round(2),
})
print(out.to_string(index=False))

print("\n=== 优化 vs 均匀分配 ===")
print("不补贴基准 GMV      %.0f" % base_gmv)
print("均匀补贴 %.2f%%      GMV %.0f  (%+.2f%%)"
      % (uniform_rate * 100, gmv(s_uniform), (gmv(s_uniform) / base_gmv - 1) * 100))
print("优化分配            GMV %.0f  (%+.2f%%)"
      % (gmv(s_opt), (gmv(s_opt) / base_gmv - 1) * 100))
print("优化相对均匀提升    %+.2f%%" % ((gmv(s_opt) / gmv(s_uniform) - 1) * 100))
print("实际花掉预算        %.0f / %.0f" % (cost(s_opt), B))
print("求解状态            %s" % res.message)

# 角点解检查
corner = [g.标签.iloc[i] for i in range(len(R0)) if s_opt[i] > S_MAX - 1e-4]
print("触及补贴上限的组    %s" % (corner if corner else "无"))

gc = grid_check(B)
print("\n网格搜索交叉验证    s = %s  GMV %+.3f%%"
      % (np.round(gc, 4), (gmv(gc) / base_gmv - 1) * 100))
print("SLSQP 解            s = %s  GMV %+.3f%%"
      % (np.round(s_opt, 4), (gmv(s_opt) / base_gmv - 1) * 100))
print("整体补贴 ROI        %.2f  （每 1 美元补贴换来的 GMV 增量）"
      % ((gmv(s_opt) - base_gmv) / cost(s_opt)))

# ---------- 5. 敏感性分析：三档预算 ----------
print("\n=== 预算敏感性 ===")
rows = []
for pct in [0.03, 0.05, 0.08]:
    b = pct * R0.sum()
    r = solve(b)
    u = brentq(lambda x: cost(np.full(len(R0), x)) - b, 1e-9, S_MAX)
    rows.append({
        "预算档": "%.0f%%" % (pct * 100),
        "预算额": round(b),
        **{("补贴率_" + g.标签.iloc[i]): round(r.x[i] * 100, 2) for i in range(len(R0))},
        "优化GMV增幅%": round((gmv(r.x) / base_gmv - 1) * 100, 2),
        "均匀GMV增幅%": round((gmv(np.full(len(R0), u)) / base_gmv - 1) * 100, 2),
    })
sens = pd.DataFrame(rows)
print(sens.to_string(index=False))

os.makedirs(os.path.join(ROOT, "output"), exist_ok=True)
out.to_csv(os.path.join(ROOT, "output", "subsidy_allocation.csv"), index=False)
sens.to_csv(os.path.join(ROOT, "output", "subsidy_sensitivity.csv"), index=False)
print("\n已保存 -> output/subsidy_allocation.csv, subsidy_sensitivity.csv")
