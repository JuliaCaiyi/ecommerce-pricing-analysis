-- 03 转化漏斗
-- 回答：15 万用户里，多少人浏览/加购/下单？漏斗在哪一步漏得最厉害？

-- Q1 三层去重用户数（分母口径：去重用户，不是事件数）
SELECT
    COUNT(DISTINCT CASE WHEN event_type = 'view' THEN user_id END) AS 浏览用户数,
    COUNT(DISTINCT CASE WHEN event_type = 'cart' THEN user_id END) AS 加购用户数,
    COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) AS 下单用户数
FROM events;

-- Q2 用户行为组合分布
-- 发现下单用户数 > 加购用户数，说明漏斗非严格串行，需拆开看每个人走到哪一步
WITH user_flag AS (
    SELECT
        user_id,
        MAX(CASE WHEN event_type = 'view' THEN 1 ELSE 0 END) AS 看过,
        MAX(CASE WHEN event_type = 'cart' THEN 1 ELSE 0 END) AS 加过购,
        MAX(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS 买过
    FROM events
    GROUP BY user_id
)
SELECT 看过, 加过购, 买过, COUNT(*) AS 用户数
FROM user_flag
GROUP BY 看过, 加过购, 买过
ORDER BY 用户数 DESC;
