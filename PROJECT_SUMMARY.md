# 电商用户行为与定价策略分析 · 项目总结

> 数据：Kaggle *eCommerce behavior data from multi category store*（2019 年 10 月）
> 工具：SQL (SQLite) · Python (pandas / statsmodels / scipy / matplotlib)
> 代码与图表：见本仓库 `/sql`、`/scripts`、`/output`

---

## Problem｜要回答什么

某多品类电商平台希望通过补贴拉动增长，但不清楚钱该往哪里投。平台面临三个连在一起的问题：**用户在转化链路的哪一步流失最严重、价格在其中起了多大作用、以及一笔固定的补贴预算该如何分配才最划算。**

## Approach｜怎么做的

基于该平台 2019 年 10 月的全量用户行为日志（4,244 万条），按 `user_id` 哈希抽样 5% 至 210 万条——用哈希而非随机抽行，以保证单个用户的「浏览—加购—下单」行为链完整。

**数据准备。** 用 SQL 完成两件事：一是数据质量体检——确认时间窗完整、量化三个关键字段的缺失率、识别并剔除 3,206 条价格异常记录；二是指标体系搭建，产出三张供下游复用的底表：**用户行为标记表**（一个用户一行，标记其是否浏览、加购、下单）、**价格带转化表**（商品按均价分十档，逐档计算转化率）、**同期群留存宽表**（按首次到访周分群，追踪各周回访率）。

**弹性估计。** 采用商品固定效应的对数-对数回归。取对数使系数直接等于弹性（百分比对百分比，跨品类可比）；加入商品固定效应后，弹性仅由同一商品自身在不同时间的价格变动识别，「贵商品天生受众更窄」这类商品固有差异被完全吸收，从而排除构成偏差。标准误按商品聚类，因为同一商品相邻几天的需求存在惯性，若假设观测独立会低估标准误、高估显著性。

**优化模型。** 以弹性为参数，建立预算约束下的补贴分配优化模型（`scipy.optimize` SLSQP，并用网格搜索交叉验证解的正确性），分别以最大化 GMV 与最大化毛利两种目标求解，检验结论对目标函数选择的稳健性。

## Findings｜发现了什么

1. **转化漏斗并非串行结构。** 17,302 名下单用户中有 7,094 人（**41%**）从未使用购物车，意味着现行的购物车召回策略最多只能覆盖六成成交路径。

2. **智能手机品类存在明确的价格断崖。** 客单价越过约 **300 美元**后，浏览转加购率由 6.70% 骤降至 3.48%，浏览转下单率相对下降 40%。

3. **价格弹性呈三个层级，以补贴盈亏临界线 β = −1 为参照：电视显著超过，智能手机紧贴临界线，其余品类明显低于。** 电视 −2.65、智能手机 −1.18，二者各自显著异于零（p=0.0008 / 0.0017）；其余七个品类因样本不足被明确剔除，合并估计为 −0.24（p=0.093，不显著异于零）。补贴要拉高 GMV 的条件是 |β| > 1，因此真正需要检验的是 β 与 **−1** 的距离：电视显著突破（H₀: β=−1，p=0.036，95% CI [−4.19, −1.11] 完全落在 −1 左侧）；智能手机点估计 −1.179 略超过 1，但 95% CI [−1.92, −0.44] 跨过 −1（p=0.634）——既不能断言它够得上门槛，也不能断言它够不上；其余品类显著弱于 −1（t=5.31，p<0.0001，CI 完全落在 −1 右侧）。**不主张品类间弹性的倍数关系**——该比值的分母不显著，区间不稳定。平台整体弹性 −0.67 且显著（p=0.0002），属缺乏弹性——**全平台无差别降价 10% 会使 GMV 下降约 4%。**

4. **最优分配由电视主导，手机只是预算溢出，整体仍不划算。** 5% 的预算下，优化分配带来 +1.51% 的 GMV，其余品类最优补贴率为零；但整体补贴 ROI 只有 0.30，仅电视超过 1（1.44）。需要说明的是，**智能手机拿到 5.49% 的补贴并不是因为模型判定它划算，而是电视在 10% 补贴率上限封顶后、预算花不完的溢出**——手机吸收了 90% 的预算却只贡献 ROI 0.17。这正是建议把补贴规模压缩到 GMV 0.5% 左右的直接依据。该结论对「其他品类」那个不显著的估计不敏感：β 取 −0.24 / 0 / −0.52（CI 下界）三种设定，最优补贴率均为 电视 10% / 智能手机 5.49% / 其他 0%，GMV 增幅与 ROI 完全相同。

5. **目标函数的选择直接改变结论。** 以毛利为目标时，三个品类的最优补贴率均为零——最大化 GMV 的方案需付出 **18.5% 的毛利**换取 1.51% 的 GMV。补贴划算的临界条件为 |β| > 1/毛利率，电视需毛利率达 **37.8%** 才值得补贴。

6. **用户价值高度集中。** 19% 的买家贡献 52.7% 的 GMV；其中 **1,924 名**「高价值流失预警」用户（人均消费为大盘 1.8 倍、平均已 20 天未购买）是干预优先级最高的人群。

## Recommendations｜建议做什么

1. **不做全品类价格补贴，把补贴规模压缩至 GMV 的 0.5% 左右并集中投向电视品类。** 该规模内 ROI 为 1.44；超出部分只能流向弹性不足的手机品类，边际 ROI 仅 0.17。

2. **将补贴从「价格策略」改为「定向策略」。** 品类维度只有一个品类的弹性够得上补贴门槛、人群维度人均价值相差 10 倍，无差别降价在两个维度上同时浪费预算。优先对 1,924 名高价值流失预警用户定向触达，成本远低于全品类降价且不侵蚀正常购买用户的毛利。

3. **针对 300 美元以上的高价商品，改用不侵蚀毛利的转化手段。** 价格断崖反映的是「高价商品缺乏购买信心」而非「价格绝对值过高」，应优先测试分期免息、以旧换新、延保与评价背书；同时新用户运营资源应集中于首次访问后的 7 天内（首周留存 32.8%，此后曲线迅速走平）。

## Limitations｜已知局限

价格弹性基于观察性数据估计，商品固定效应吸收了不随时间变化的商品属性，但无法排除随时间变化的混淆因素（如预期需求上升前提价），故结论定位为方向性参考，落地需 A/B 实验验证；优化模型假设品类间需求独立，忽略替代效应，因此 GMV 增量为上界；恒弹性假设仅在数据覆盖的价格波动范围（商品内月均 8.6%）内成立，故补贴率上限保守设为 10%；毛利率为外生假设，已通过四档敏感性分析缓解；数据仅一个月，无法识别季节性，留存最多观察至第 4 周。

---
---

# E-Commerce Behavioural & Pricing Strategy Analysis — Executive Summary

> Data: Kaggle *eCommerce behavior data from multi category store* (October 2019)
> Stack: SQL (SQLite) · Python (pandas / statsmodels / scipy / matplotlib)
> Code and charts: see `/sql`, `/scripts`, `/output` in this repository

---

## Problem

A multi-category e-commerce platform wants to drive growth through subsidies but does not know where the money should go. Three linked questions had to be answered: **where in the conversion path users drop off, how much of that is driven by price, and how a fixed subsidy budget should be allocated to deliver the most value.**

## Approach

The analysis is based on the platform's complete October 2019 behavioural log (42.4M events), hash-sampled on `user_id` down to 2.1M rows. Sampling by user hash rather than by row preserves each user's full view → cart → purchase sequence; random row sampling would fragment those chains and distort every funnel and retention metric.

**Data preparation.** SQL served two purposes. First, a data-quality audit: confirming the observation window was complete, quantifying missingness in the three key fields, and removing 3,206 records with invalid prices. Second, building three reusable base tables: a **user-level behaviour flag table** (one row per user, flagging whether they viewed, carted and purchased), a **price-band conversion table** (products bucketed into average-price deciles with conversion rates per band), and a **cohort retention matrix** (users grouped by first-visit week, tracking return rates by week).

**Elasticity estimation.** A log-log regression with product fixed effects. Taking logs makes the coefficient the elasticity itself — a percentage-to-percentage ratio that is unit-free and comparable across categories. Product fixed effects mean the elasticity is identified purely from within-product price variation over time, so time-invariant product characteristics — the fact that premium products inherently reach a narrower audience — are absorbed entirely, eliminating composition bias. Standard errors are clustered by product, because demand for the same product persists across adjacent days; treating observations as independent would understate standard errors and overstate significance.

**Optimisation.** Using the estimated elasticities as parameters, a budget-constrained subsidy allocation model was solved with `scipy.optimize` (SLSQP), cross-validated against a brute-force grid search. The model was solved twice — maximising GMV and maximising gross profit — to test how sensitive the conclusion is to the choice of objective.

## Findings

1. **The conversion funnel is not sequential.** Of 17,302 purchasers, 7,094 (**41%**) never used the cart, meaning existing cart-abandonment campaigns can reach at most 60% of conversion paths.

2. **Smartphones show a clear price cliff.** Above roughly **$300**, view-to-cart conversion drops from 6.70% to 3.48%, and view-to-purchase conversion falls 40% in relative terms.

3. **Elasticity falls into three tiers relative to the break-even threshold β = −1: TV clears it decisively, smartphones sit right on it, and everything else falls clearly short.** TV −2.65 and smartphones −1.18 are each significantly different from zero (p = 0.0008 / 0.0017); the remaining seven were explicitly dropped for insufficient power and pool to −0.24 (p = 0.093, not significantly different from zero). Because a subsidy only raises GMV when |β| > 1, the relevant test is the distance from **−1**, not from 0: TV clears it (H₀: β = −1, p = 0.036; 95% CI [−4.19, −1.11] lies entirely below −1); smartphones have a point estimate of −1.179, marginally past the threshold, but a 95% CI of [−1.92, −0.44] that straddles −1 (p = 0.634) — so neither clearing nor missing the threshold can be asserted; the pooled remainder is significantly weaker than −1 (t = 5.31, p < 0.0001). **No claim is made about the ratio of elasticities across categories** — the denominator of that ratio is not significant, so the ratio is unstable. Platform-wide elasticity is −0.67 and significant (p = 0.0002) — inelastic, meaning **an across-the-board 10% price cut would reduce GMV by roughly 4%.**

4. **Optimal allocation is driven by TV; smartphones only absorb the overflow, and the programme is still not worthwhile overall.** On a 5% budget, optimised allocation delivers +1.51% GMV with a zero optimal subsidy for every other category — but overall subsidy ROI is only 0.30 and TV is the sole category above 1 (1.44). Smartphones receive a 5.49% subsidy not because the model judges it worthwhile, but because TV hits its 10% rate cap and the budget must go somewhere: smartphones absorb 90% of the spend at an ROI of just 0.17. This is the direct basis for recommending the programme be cut to roughly 0.5% of GMV. This conclusion is insensitive to the non-significant pooled estimate: setting β to −0.24, 0, or −0.52 (the CI lower bound) yields the identical optimum of 10% / 5.49% / 0%.

5. **The choice of objective function changes the conclusion outright.** Maximising gross profit yields an optimal subsidy rate of zero for all three groups: the GMV-maximising plan costs **18.5% of gross profit** to buy 1.51% of GMV. The break-even condition is |β| > 1/margin, so subsidising TV only pays off at a gross margin above **37.8%**.

6. **Customer value is highly concentrated.** 19% of buyers generate 52.7% of GMV. Within that, **1,924 "at-risk high-value" customers** — averaging 1.8x platform-average spend but 20 days since their last purchase — are the highest-priority intervention group.

## Recommendations

1. **Do not run an across-the-board price subsidy. Cut the programme to roughly 0.5% of GMV and concentrate it on the TV category.** ROI within that scale is 1.44; anything beyond it can only flow to smartphones, where marginal ROI is 0.17.

2. **Shift subsidy from a pricing lever to a targeting lever.** Only one category clears the elasticity threshold for a subsidy, and customer value varies 10x across segments — undifferentiated discounting wastes budget on both dimensions simultaneously. Prioritise direct outreach to the 1,924 at-risk high-value customers: far cheaper than category-wide discounting, and it does not erode margin on customers who would have paid full price.

3. **For products above $300, use conversion levers that do not erode margin.** The price cliff reflects a confidence gap on high-ticket items rather than absolute price resistance, so instalment plans, trade-in programmes, extended warranties and review social proof should be tested first. In parallel, concentrate new-user resources in the first seven days after acquisition — week-1 retention is 32.8%, after which the curve flattens sharply.

## Limitations

Elasticity is estimated from observational data. Product fixed effects absorb time-invariant product characteristics but cannot rule out time-varying confounders, such as prices being raised ahead of anticipated demand; the estimates are therefore directional and require A/B validation before rollout. The optimisation assumes independent demand across categories and ignores substitution, so the GMV gain is an upper bound. The constant-elasticity assumption holds only within the price variation observed in the data (8.6% average within-product monthly range), which is why the subsidy cap is set conservatively at 10%. Gross margin is an exogenous assumption, mitigated by a four-level sensitivity analysis. With only one month of data, seasonality cannot be identified and retention is observable only to week 4.
