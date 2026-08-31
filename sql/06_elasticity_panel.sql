-- 06 弹性面板底表
-- 回答：明天的价格弹性回归要用什么数据？
-- 输出：商品 × 日期 面板（均价、当日购买数、品类），已做两道预筛

WITH cand AS (
    -- 月内购买次数 >= 5 的商品，太冷门的噪声大
    SELECT product_id
    FROM events
    WHERE event_type = 'purchase' AND price > 0
    GROUP BY product_id
    HAVING COUNT(*) >= 5
),
panel AS (
    -- 价格取当日所有事件均价（浏览事件也带价格，所以无购买日也有价格）
    SELECT
        e.product_id,
        DATE(e.event_time) AS 日期,
        AVG(e.price) AS 均价,
        SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) AS 购买数,
        MAX(e.category_code) AS 品类
    FROM events e
    JOIN cand c ON e.product_id = c.product_id
    WHERE e.price > 0
    GROUP BY e.product_id, DATE(e.event_time)
),
varying AS (
    -- 月内价格波动幅度 > 0.5% 的商品，价格不动的提供不了识别变异
    SELECT product_id
    FROM panel
    GROUP BY product_id
    HAVING (MAX(均价) - MIN(均价)) / AVG(均价) > 0.005
)
SELECT p.product_id, p.日期, ROUND(p.均价, 2) AS 均价, p.购买数, p.品类
FROM panel p
JOIN varying v ON p.product_id = v.product_id
WHERE p.品类 IS NOT NULL
ORDER BY p.product_id, p.日期;
