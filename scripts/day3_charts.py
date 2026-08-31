"""生成七张核心图表。数据全部从 ecommerce.db 与 Day 2 的 CSV 读取，可复现。"""
import os
import sqlite3
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "output")
os.makedirs(OUT, exist_ok=True)
conn = sqlite3.connect(os.path.join(ROOT, "data", "ecommerce.db"))

# ---- 统一视觉：一套配色 + 克制的网格 ----
TEAL, AMBER, INK, INK2, INK3, RULE = "#008B7E", "#B57200", "#1C2321", "#4A534F", "#77807B", "#E1E2DB"
plt.rcParams.update({
    "figure.dpi": 160, "savefig.dpi": 160, "savefig.bbox": "tight",
    "font.family": "DejaVu Sans", "font.size": 10,
    "axes.edgecolor": RULE, "axes.labelcolor": INK2, "axes.titlecolor": INK,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.titlepad": 14, "xtick.color": INK3, "ytick.color": INK3,
    "axes.grid": True, "grid.color": RULE, "grid.linewidth": 0.8,
    "figure.facecolor": "white", "axes.facecolor": "white",
})

def tidy(ax, xgrid=False):
    """只留必要的轴线和一个方向的网格"""
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="x" if xgrid else "y")
    ax.grid(axis="y" if xgrid else "x", visible=False)

def save(fig, name, note):
    fig.savefig(os.path.join(OUT, name))
    plt.close(fig)
    print("  %-34s %s" % (name, note))

print("生成图表 ...")

# ============ 1. 转化漏斗 ============
f = pd.read_sql("""
    SELECT COUNT(DISTINCT CASE WHEN event_type='view'     THEN user_id END) AS v,
           COUNT(DISTINCT CASE WHEN event_type='cart'     THEN user_id END) AS c,
           COUNT(DISTINCT CASE WHEN event_type='purchase' THEN user_id END) AS p
    FROM events""", conn).iloc[0]
skip = pd.read_sql("""
    WITH uf AS (SELECT user_id,
        MAX(CASE WHEN event_type='cart' THEN 1 ELSE 0 END) AS carted,
        MAX(CASE WHEN event_type='purchase' THEN 1 ELSE 0 END) AS bought
        FROM events GROUP BY user_id)
    SELECT SUM(CASE WHEN bought=1 AND carted=0 THEN 1 ELSE 0 END) AS skipped,
           SUM(bought) AS buyers FROM uf""", conn).iloc[0]

fig, ax = plt.subplots(figsize=(8, 3.4))
stages = ["Viewed", "Added to cart", "Purchased"]
vals = [f.v, f.c, f.p]
ax.barh(stages[::-1], vals[::-1], height=0.55, color=[TEAL, TEAL, TEAL],
        alpha=1, zorder=3)
for i, (s, v) in enumerate(zip(stages[::-1], vals[::-1])):
    ax.text(v + f.v * 0.012, i, f"{v:,}", va="center", color=INK, fontsize=10)
ax.set_xlim(0, f.v * 1.22)
ax.xaxis.set_major_formatter(lambda v, _: f"{int(v):,}")
ax.set_title("Conversion funnel is not sequential")
ax.set_xlabel("Distinct users")
pct = skip.skipped / skip.buyers * 100
ax.text(f.v * 0.30, 0.42, f"{skip.skipped:,} purchasers ({pct:.0f}%) never used the cart\n"
        f"→ cart-abandonment campaigns reach at most {100-pct:.0f}% of conversion paths",
        color=AMBER, fontsize=9.5, va="bottom")
tidy(ax, xgrid=True)
save(fig, "fig1_funnel.png", "浏览 %s / 加购 %s / 下单 %s" % (f"{f.v:,}", f"{f.c:,}", f"{f.p:,}"))

# ============ 2. 价格带转化（手机品类） ============
pb = pd.read_sql("""
WITH prod AS (
    SELECT product_id, AVG(price) AS ap,
           COUNT(DISTINCT CASE WHEN event_type='view' THEN user_id END) AS vw,
           COUNT(DISTINCT CASE WHEN event_type='cart' THEN user_id END) AS ct,
           COUNT(DISTINCT CASE WHEN event_type='purchase' THEN user_id END) AS pu
    FROM events WHERE price>0 AND category_code='electronics.smartphone'
    GROUP BY product_id),
b AS (SELECT *, NTILE(10) OVER (ORDER BY ap) AS band FROM prod)
SELECT band, MIN(ap) AS lo, MAX(ap) AS hi,
       SUM(ct)*100.0/SUM(vw) AS cart_rate,
       SUM(pu)*100.0/SUM(vw) AS buy_rate
FROM b GROUP BY band ORDER BY band""", conn)

fig, ax = plt.subplots(figsize=(8.4, 4.2))
x = np.arange(len(pb))
ax.plot(x, pb.cart_rate, "-o", color=TEAL, lw=2, ms=7, mec="white", mew=1.6,
        label="View → Cart", zorder=3)
ax.plot(x, pb.buy_rate, "-o", color=AMBER, lw=2, ms=7, mec="white", mew=1.6,
        label="View → Purchase", zorder=3)
cliff = 5.5
ax.axvline(cliff, color=AMBER, ls="--", lw=1.4, alpha=.8, zorder=2)
ax.text(cliff + .12, ax.get_ylim()[1] * .96, "≈ $300 cliff", color=AMBER, fontsize=9.5, va="top")
ax.annotate(f"{pb.cart_rate[3]:.2f}%", (3, pb.cart_rate[3]),
            textcoords="offset points", xytext=(0, 12), ha="center", color=TEAL, fontsize=9.5)
ax.annotate(f"{pb.cart_rate[6]:.2f}%", (6, pb.cart_rate[6]),
            textcoords="offset points", xytext=(16, -6), ha="left", color=TEAL, fontsize=9.5)
ax.set_xticks(x)
ax.set_xticklabels([f"{lo:.0f}–{hi:.0f}" for lo, hi in zip(pb.lo, pb.hi)],
                   rotation=35, ha="right", fontsize=8.5)
ax.set_xlabel("Product average price band (USD, deciles)")
ax.set_ylabel("Conversion rate (%)")
ax.set_title("Smartphones: conversion halves above $300")
ax.legend(frameon=False, loc="upper left", fontsize=9.5)
tidy(ax)
save(fig, "fig2_price_band.png", "断崖点 $300 附近，加购率 6.70% → 3.48%")

# ============ 3. 品类弹性（森林图） ============
el = pd.read_csv(os.path.join(OUT, "elasticity_by_category.csv")).sort_values("弹性beta", ascending=False)
fig, ax = plt.subplots(figsize=(8.4, 4.6))
y = np.arange(len(el))
for i in range(len(el)):
    row = el.iloc[i]
    ok = row["p值"] < 0.05
    col = TEAL if ok else INK3
    ax.plot([row["CI下界"], row["CI上界"]], [i, i], color=col, lw=2.2 if ok else 1.4,
            alpha=1 if ok else .55, zorder=3, solid_capstyle="round")
    ax.plot(row["弹性beta"], i, "o", color=col if ok else "white",
            mec=col, mew=1.8, ms=9 if ok else 7, zorder=4)
ax.axvline(0, color=INK3, lw=1.2, zorder=2)
ax.axvline(-1, color=AMBER, ls="--", lw=1.4, zorder=2)
ax.set_ylim(-0.9, len(el) - 0.2)
ax.annotate("β = −1  subsidy break-even", xy=(-1, len(el) - 0.45),
            xytext=(-1.15, len(el) - 0.45), color=AMBER, fontsize=9,
            ha="right", va="center")
ax.set_yticks(y)
ax.set_yticklabels([c.replace("electronics.", "").replace("appliances.", "").replace("computers.", "")
                    for c in el.品类], fontsize=9)
ax.set_xlabel("Price elasticity β  (95% CI)")
ax.set_title("Only two categories are statistically identified")
fig.text(.5, -.03, "filled = significant (p<0.05)      hollow = not significant, dropped from the optimisation",
         ha="center", color=INK3, fontsize=8.5)
tidy(ax, xgrid=True)
save(fig, "fig3_elasticity.png", "9 个品类，2 个显著")

# ============ 4. 最优 vs 均匀分配 ============
al = pd.read_csv(os.path.join(OUT, "subsidy_allocation.csv"))
sen = pd.read_csv(os.path.join(OUT, "subsidy_sensitivity.csv"))
row5 = sen[sen.预算档 == "5%"].iloc[0]
fig, ax = plt.subplots(figsize=(7.2, 3.0))
labels = ["Uniform split", "Optimised split"]
vals = [row5["均匀GMV增幅%"], row5["优化GMV增幅%"]]
bars = ax.barh(labels, vals, height=.42, color=[INK3, TEAL], zorder=3)
bars[0].set_alpha(.5)
for i, v in enumerate(vals):
    ax.text(v + .04, i, f"+{v:.2f}%", va="center", color=INK, fontsize=11)
ax.set_xlim(0, max(vals) * 1.35)
ax.set_xlabel("GMV lift vs no subsidy (%)")
ax.set_title("Same budget, %.1f× the GMV lift" % (vals[1] / vals[0]))
ax.text(0.02, .5, "both plans spend the identical $%s budget" % f"{row5.预算额:,.0f}",
        color=AMBER, fontsize=9.5, va="center", ha="left")
tidy(ax, xgrid=True)
save(fig, "fig4_alloc.png", "优化 +%.2f%% vs 均匀 +%.2f%%" % (vals[1], vals[0]))

# ============ 5. 预算敏感性 ============
fig, ax = plt.subplots(figsize=(7.6, 4.0))
bx = [int(p.strip("%")) for p in sen.预算档]
ax.plot(bx, sen["优化GMV增幅%"], "-o", color=TEAL, lw=2, ms=8, mec="white", mew=1.6,
        label="Optimised", zorder=3)
ax.plot(bx, sen["均匀GMV增幅%"], "-o", color=INK3, lw=2, ms=8, mec="white", mew=1.6,
        label="Uniform", zorder=3, alpha=.7)
for j, (xx, yy) in enumerate(zip(bx, sen["优化GMV增幅%"])):
    ax.annotate(f"+{yy:.2f}%", (xx, yy), textcoords="offset points",
                xytext=(8 if j == 0 else 0, -18 if j == 0 else 11),
                ha="left" if j == 0 else "center", color=TEAL, fontsize=9)
ax.annotate("TV stays capped at 10%;\nextra budget leaks to smartphones",
            xy=(6.5, 1.0), color=INK3, fontsize=9, ha="center")
ax.set_xticks(bx)
ax.set_xlabel("Subsidy budget (% of baseline GMV)")
ax.set_ylabel("GMV lift (%)")
ax.set_xlim(2.5, 8.5)
ax.set_title("Diminishing returns on a bigger budget")
ax.legend(frameon=False, fontsize=9.5)
tidy(ax)
save(fig, "fig5_budget.png", "3%/5%/8% 三档，边际回报递减")

# ============ 6. 留存热力图 ============
ret = pd.read_sql("""
WITH fs AS (SELECT user_id, MIN(DATE(event_time)) AS d0 FROM events GROUP BY user_id),
uw AS (SELECT f.user_id,
        CAST((JULIANDAY(f.d0)-JULIANDAY('2019-10-01'))/7 AS INT) AS c,
        CAST((JULIANDAY(DATE(e.event_time))-JULIANDAY(f.d0))/7 AS INT) AS w
       FROM events e JOIN fs f ON e.user_id=f.user_id)
SELECT c, w, COUNT(DISTINCT user_id) AS n FROM uw GROUP BY c, w""", conn)
piv = ret.pivot(index="c", columns="w", values="n")
size = piv[0]
rate = piv.div(size, axis=0) * 100
rate = rate.loc[0:3, 0:3]
# 观察窗口完整性：cohort c 的最后一天 L=min(7(c+1),31)，第 w 周需 L+7w+6 <= 31
complete = np.array([[w == 0 or min(7 * (c + 1), 31) + 7 * w + 6 <= 31 for w in range(4)] for c in range(4)])

fig, ax = plt.subplots(figsize=(7.2, 4.2))
ax.grid(False)
vmax = 100
for c in range(4):
    for w in range(4):
        v = rate.iloc[c, w] if not pd.isna(rate.iloc[c, w]) else None
        if v is None:
            continue
        ok = complete[c, w]
        shade = (v / vmax) ** .55
        face = (0.0, 0.545, 0.494, shade) if ok else (0.47, 0.50, 0.48, .13)
        ax.add_patch(Rectangle((w, 3 - c), 1, 1, facecolor=face,
                               edgecolor="white", lw=2.5,
                               hatch=None if ok else "///"))
        txt = f"{v:.1f}%" if ok else f"({v:.1f}%)"
        ax.text(w + .5, 3 - c + .5, txt, ha="center", va="center",
                color="white" if (ok and shade > .5) else (INK if ok else INK3),
                fontsize=10.5 if ok else 9, fontweight="bold" if ok else "normal")
ax.set_xlim(0, 4); ax.set_ylim(0, 4)
ax.set_xticks(np.arange(4) + .5); ax.set_xticklabels([f"Week {w}" for w in range(4)])
ax.set_yticks(np.arange(4) + .5)
ax.set_yticklabels([f"Cohort {c}\n(n={int(size[c]):,})" for c in range(3, -1, -1)], fontsize=9)
for s in ax.spines.values():
    s.set_visible(False)
ax.tick_params(length=0)
ax.set_title("Retention: the first week decides")
ax.text(0, -.55, "hatched cells in ( ) have an incomplete observation window "
        "(data ends 2019-10-31) and are not comparable",
        color=INK3, fontsize=8.5)
save(fig, "fig6_retention.png", "首周 cohort 32.8% → 29.6%，截断格已标注")

# ============ 7. RFM 分群 ============
seg = pd.read_csv(os.path.join(OUT, "rfm_segments.csv")).sort_values("GMV占比%", ascending=True)
fig, ax = plt.subplots(figsize=(8.6, 4.8))
y = np.arange(len(seg)); h = .36
EN = {"重要价值客户": "Champions", "重要保持客户": "At-risk high value",
      "重要挽留客户": "Lapsed high spender", "重要发展客户": "New high spender",
      "一般挽留客户": "Lapsed low value", "一般发展客户": "New low value",
      "一般价值客户": "Loyal low spender", "一般保持客户": "Cooling low value"}
hot = seg.分群 == "重要保持客户"
ax.barh(y + h/2, seg["用户占比%"], height=h, color=INK3, alpha=.45,
        label="Share of users", zorder=3)
ax.barh(y - h/2, seg["GMV占比%"], height=h,
        color=[AMBER if x else TEAL for x in hot], label="Share of GMV", zorder=3)
for i in range(len(seg)):
    u, gm = seg.iloc[i]["用户占比%"], seg.iloc[i]["GMV占比%"]
    ax.text(max(u, gm) + .9, i, "%.1f×" % (gm / u), va="center", color=INK2, fontsize=9)
ax.set_yticks(y)
ax.set_yticklabels([EN[s] for s in seg.分群], fontsize=9.5)
ax.set_xlabel("Share (%)　·　right label = GMV share ÷ user share")
ax.set_title("19% of buyers generate 52.7% of GMV")
from matplotlib.patches import Patch
handles = [Patch(facecolor=INK3, alpha=.45, label="Share of users"),
           Patch(facecolor=TEAL, label="Share of GMV"),
           Patch(facecolor=AMBER, label="Share of GMV — priority segment")]
ax.legend(handles=handles, frameon=False, fontsize=9.5, loc="lower right")
ax.set_xlim(0, 60)
tidy(ax, xgrid=True)
save(fig, "fig7_rfm.png", "重要保持客户（橙色）为优先干预人群")

conn.close()
print("\n七张图已保存到 output/")
