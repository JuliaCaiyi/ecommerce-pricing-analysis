"""价格弹性估计：商品固定效应 + 按商品聚类的稳健标准误"""
import os
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
panel = pd.read_csv(os.path.join(ROOT, "data", "elasticity_panel.csv"))

# 取对数需要正数，故只保留当天有购买的商品-日
# 局限：剔除零销量日本身是一种样本选择，可能与价格相关
d = panel[panel.qty > 0].copy()
d["lq"] = np.log(d.qty)
d["lp"] = np.log(d.price)
print("样本：%d 行，%d 个商品\n" % (len(d), d.product_id.nunique()))


def fe(df):
    """商品固定效应回归，标准误按商品聚类"""
    m = smf.ols("lq ~ lp + C(product_id)", data=df).fit(
        cov_type="cluster", cov_kwds={"groups": df["product_id"]})
    return m


# ---- 整体弹性 ----
m = fe(d)
print("=== 整体 ===")
print("beta %.3f  SE %.3f  t %.2f  p %.4f  n %d"
      % (m.params["lp"], m.bse["lp"], m.tvalues["lp"], m.pvalues["lp"], m.nobs))

# ---- 分品类弹性 ----
# 门槛：商品数 >= 10 且观测 >= 100。样本太小时固定效应估计几乎由个别商品驱动，
# 标准误大到没有意义，宁可剔除也不硬报。
rows = []
for cat, g in d.groupby("category"):
    if g.product_id.nunique() < 10 or len(g) < 100:
        continue
    r = fe(g)
    b, se = r.params["lp"], r.bse["lp"]
    rows.append({
        "品类": cat,
        "商品数": g.product_id.nunique(),
        "观测数": len(g),
        "弹性beta": round(b, 3),
        "聚类SE": round(se, 3),
        "t值": round(r.tvalues["lp"], 2),
        "p值": round(r.pvalues["lp"], 4),
        "CI下界": round(b - 1.96 * se, 2),
        "CI上界": round(b + 1.96 * se, 2),
    })

elas = pd.DataFrame(rows).sort_values("弹性beta")
print("\n=== 分品类 ===")
print(elas.to_string(index=False))

out = os.path.join(ROOT, "output", "elasticity_by_category.csv")
os.makedirs(os.path.dirname(out), exist_ok=True)
elas.to_csv(out, index=False)
print("\n已保存 -> %s" % out)


# ---- 把单独估不准的品类合并成「其他」组池化估计 ----
# 单个品类样本不足（SE 大于系数本身），但合并后样本量足以得到可靠的组级弹性。
# 直接剔除等于假装这些品类不存在，合并估计更诚实。
RELIABLE = ["electronics.video.tv", "electronics.smartphone"]
rest = d[~d.category.isin(RELIABLE)]
m_rest = fe(rest)
print("\n=== 其他品类合并 ===")
print("beta %.3f  SE %.3f  t %.2f  p %.4f  商品数 %d  观测 %d"
      % (m_rest.params["lp"], m_rest.bse["lp"], m_rest.tvalues["lp"],
         m_rest.pvalues["lp"], rest.product_id.nunique(), m_rest.nobs))

# ---- 优化模型要用的三组弹性 ----
groups = []
for name, sub, label in [
    ("electronics.video.tv", d[d.category == "electronics.video.tv"], "电视"),
    ("electronics.smartphone", d[d.category == "electronics.smartphone"], "智能手机"),
    ("other", rest, "其他品类合并"),
]:
    r = fe(sub)
    groups.append({
        "group": name, "标签": label,
        "beta": round(r.params["lp"], 3),
        "SE": round(r.bse["lp"], 3),
        "t": round(r.tvalues["lp"], 2),
        "商品数": sub.product_id.nunique(),
        "观测数": len(sub),
    })
gdf = pd.DataFrame(groups)
print("\n=== 进入优化模型的三组 ===")
print(gdf.to_string(index=False))
gdf.to_csv(os.path.join(ROOT, "output", "elasticity_groups.csv"), index=False)
print("已保存 -> output/elasticity_groups.csv")
