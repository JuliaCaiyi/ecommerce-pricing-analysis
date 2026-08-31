"""RFM 用户分群。第一步：先看 R/F/M 的分布，再定分档阈值。"""
import os
import sqlite3
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OBS_END = "2019-10-31"          # 观察期末，R 从这天往回数

conn = sqlite3.connect(os.path.join(ROOT, "data", "ecommerce.db"))
rfm = pd.read_sql(f"""
    SELECT user_id,
           CAST(JULIANDAY('{OBS_END}') - JULIANDAY(MAX(DATE(event_time))) AS INT) AS R,
           COUNT(*)   AS F,
           SUM(price) AS M
    FROM events
    WHERE event_type = 'purchase' AND price > 0
    GROUP BY user_id
""", conn)
conn.close()

print("购买过的用户数：%d\n" % len(rfm))
print("=== R / F / M 分布 ===")
print(rfm[["R", "F", "M"]].describe(
    percentiles=[.25, .5, .75, .9]).round(2).to_string())

print("\n=== F（购买次数）的具体分布 ===")
fc = rfm.F.value_counts().sort_index().head(8)
print(pd.DataFrame({"购买次数": fc.index, "用户数": fc.values,
                    "占比%": (fc.values / len(rfm) * 100).round(1)}).to_string(index=False))
print("买过 2 次及以上的用户占比：%.1f%%" % ((rfm.F >= 2).mean() * 100))

print("\n=== R（最后一次购买距 10/31 天数）分布 ===")
print("中位数 %d 天，25%% 分位 %d 天，75%% 分位 %d 天"
      % (rfm.R.median(), rfm.R.quantile(.25), rfm.R.quantile(.75)))

rfm.to_csv(os.path.join(ROOT, "output", "rfm_raw.csv"), index=False)
print("\n已保存 -> output/rfm_raw.csv")


# ---------- 第二步：按分布定阈值，做八分类 ----------
# R：分布均匀，用中位数 13 天
# F：中位数是 1（61% 用户只买过一次），按中位数切不开，改用「是否有复购」F>=2，
#    这个阈值本身有业务含义：复购用户 vs 一次性用户
# M：极度右偏（均值 627 是中位数 247 的 2.5 倍），用均值会让高价值组只剩四分之一，故用中位数
R_CUT = rfm.R.median()
F_CUT = 2
M_CUT = rfm.M.median()
print("\n阈值：R <= %.0f 天为近期 | F >= %d 为复购 | M > %.2f 为高额"
      % (R_CUT, F_CUT, M_CUT))

rfm["R高"] = rfm.R <= R_CUT      # 越小越好，所以是 <=
rfm["F高"] = rfm.F >= F_CUT
rfm["M高"] = rfm.M > M_CUT

NAME = {
    (1, 1, 1): "重要价值客户", (0, 1, 1): "重要保持客户",
    (1, 0, 1): "重要发展客户", (0, 0, 1): "重要挽留客户",
    (1, 1, 0): "一般价值客户", (0, 1, 0): "一般保持客户",
    (1, 0, 0): "一般发展客户", (0, 0, 0): "一般挽留客户",
}
ACTION = {
    "重要价值客户": "重点维护：VIP 权益、专属客服、新品优先",
    "重要保持客户": "流失预警，优先召回：定向高额券 + 唤醒推送",
    "重要发展客户": "提频：复购引导、搭配推荐、会员体系",
    "重要挽留客户": "高价值召回：人工触达 + 大额挽留权益",
    "一般价值客户": "提客单价：满减、组合装、升级推荐",
    "一般保持客户": "低成本触达：站内消息、内容种草",
    "一般发展客户": "培育新客：新人券、次单激励",
    "一般挽留客户": "不重点投入：仅纳入大促普发",
}
rfm["分群"] = [NAME[(int(a), int(b), int(c))]
              for a, b, c in zip(rfm.R高, rfm.F高, rfm.M高)]

seg = rfm.groupby("分群").agg(
    用户数=("user_id", "count"),
    平均R=("R", "mean"), 平均F=("F", "mean"), 平均M=("M", "mean"),
    贡献GMV=("M", "sum")).reset_index()
seg["用户占比%"] = (seg.用户数 / len(rfm) * 100).round(1)
seg["GMV占比%"] = (seg.贡献GMV / rfm.M.sum() * 100).round(1)
seg["人均价值倍数"] = (seg.平均M / rfm.M.mean()).round(2)
seg["运营动作"] = seg.分群.map(ACTION)
seg = seg.sort_values("贡献GMV", ascending=False)

print("\n=== RFM 八分群 ===")
print(seg[["分群", "用户数", "用户占比%", "GMV占比%", "人均价值倍数",
           "平均R", "平均F", "平均M"]].round(1).to_string(index=False))
print("\n=== 运营动作 ===")
for _, r in seg.iterrows():
    print("  %-8s %s" % (r.分群, r.运营动作))

rfm.to_csv(os.path.join(ROOT, "output", "rfm_users.csv"), index=False)
seg.to_csv(os.path.join(ROOT, "output", "rfm_segments.csv"), index=False)
print("\n已保存 -> output/rfm_users.csv, rfm_segments.csv")
