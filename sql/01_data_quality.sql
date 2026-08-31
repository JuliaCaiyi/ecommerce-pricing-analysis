-- 01 数据质量检查
-- 回答：这份数据靠不靠谱？规模多大？有哪些字段不能直接用？

-- Q1 基础规模与时间范围
SELECT
    COUNT(*) AS 总行数,
    COUNT(DISTINCT user_id) AS 用户数,
    COUNT(DISTINCT product_id) AS 商品数,
    COUNT(DISTINCT user_session) AS 会话数,
    MIN(event_time) AS 最早时间,
    MAX(event_time) AS 最晚时间
FROM events;

-- Q2 关键字段缺失率
SELECT
    ROUND(SUM(CASE WHEN category_code IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS category缺失率,
    ROUND(SUM(CASE WHEN brand IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS brand缺失率,
    ROUND(SUM(CASE WHEN price IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS price缺失率
FROM events;

-- Q3 事件类型分布（注意：这是事件占比，不是转化率，转化率见 03）
SELECT
    event_type,
    COUNT(*) AS 事件数,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM events), 2) AS 占比
FROM events
GROUP BY event_type;

-- Q4 价格异常值
SELECT
    SUM(CASE WHEN price <= 0 THEN 1 ELSE 0 END) AS 价格异常行数,
    MIN(price) AS 最低价,
    MAX(price) AS 最高价
FROM events;
