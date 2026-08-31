-- 02 基础业务指标
-- 回答：平台每天有多少人？有没有周内规律？主要在卖什么？

-- Q1 按天 DAU 与事件量
SELECT
    DATE(event_time) AS 日期,
    COUNT(*) AS 事件数,
    COUNT(DISTINCT user_id) AS DAU
FROM events
GROUP BY DATE(event_time)
ORDER BY DATE(event_time);

-- Q2 周内波动
-- 注意：不能直接按星期几分组数总量。10 月里周二/三/四各有 5 天，其余只有 4 天，
-- 直接比总量会得出"周二最高"的错误结论。必须先算每日 DAU，再按星期几求平均。
WITH daily AS (
    SELECT DATE(event_time) AS 日期, COUNT(*) AS 事件数, COUNT(DISTINCT user_id) AS DAU
    FROM events
    GROUP BY DATE(event_time)
)
SELECT
    strftime('%w', 日期) AS 星期,
    ROUND(AVG(DAU), 0) AS 平均DAU,
    ROUND(AVG(事件数), 0) AS 平均事件数
FROM daily
GROUP BY 星期
ORDER BY 星期;

-- Q3 Top 10 品类的浏览量与下单量
SELECT
    category_code AS 品类,
    SUM(CASE WHEN event_type = 'view' THEN 1 ELSE 0 END) AS 浏览量,
    SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS 下单量
FROM events
WHERE category_code IS NOT NULL
GROUP BY category_code
ORDER BY 浏览量 DESC
LIMIT 10;
