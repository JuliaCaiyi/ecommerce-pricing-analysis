-- 04 价格带转化
-- 回答：商品贵到什么程度，用户开始不加购了？

-- Q1 全平台按价格十分位分档
-- 分档用 NTILE 而非固定区间：价格分布极度右偏，固定区间会导致各档商品数悬殊，无法横向比较
WITH prod AS (
    SELECT
        product_id,
        AVG(price) AS 均价,
        COUNT(DISTINCT CASE WHEN event_type = 'view' THEN user_id END) AS 浏览人数,
        COUNT(DISTINCT CASE WHEN event_type = 'cart' THEN user_id END) AS 加购人数,
        COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) AS 下单人数
    FROM events
    WHERE price > 0
    GROUP BY product_id
),
banded AS (
    SELECT *, NTILE(10) OVER (ORDER BY 均价) AS 价格档 FROM prod
)
SELECT
    价格档,
    ROUND(MIN(均价), 2) AS 档内最低价,
    ROUND(MAX(均价), 2) AS 档内最高价,
    SUM(浏览人数) AS 浏览人次,
    SUM(加购人数) AS 加购人次,
    SUM(下单人数) AS 下单人次,
    ROUND(SUM(加购人数) * 100.0 / SUM(浏览人数), 2) AS 浏览转加购率,
    ROUND(SUM(下单人数) * 100.0 / SUM(浏览人数), 2) AS 浏览转下单率
FROM banded
GROUP BY 价格档
ORDER BY 价格档;

-- Q2 同一品类内部再看一次
-- 全平台口径受品类构成干扰（手机占 46% 成交且集中在中高价位），固定品类后才是价格本身的效应
WITH prod AS (
    SELECT
        product_id,
        AVG(price) AS 均价,
        COUNT(DISTINCT CASE WHEN event_type = 'view' THEN user_id END) AS 浏览人数,
        COUNT(DISTINCT CASE WHEN event_type = 'cart' THEN user_id END) AS 加购人数,
        COUNT(DISTINCT CASE WHEN event_type = 'purchase' THEN user_id END) AS 下单人数
    FROM events
    WHERE price > 0 AND category_code = 'electronics.smartphone'
    GROUP BY product_id
),
banded AS (
    SELECT *, NTILE(10) OVER (ORDER BY 均价) AS 价格档 FROM prod
)
SELECT
    价格档,
    ROUND(MIN(均价), 2) AS 档内最低价,
    ROUND(MAX(均价), 2) AS 档内最高价,
    SUM(浏览人数) AS 浏览人次,
    SUM(加购人数) AS 加购人次,
    SUM(下单人数) AS 下单人次,
    ROUND(SUM(加购人数) * 100.0 / SUM(浏览人数), 2) AS 浏览转加购率,
    ROUND(SUM(下单人数) * 100.0 / SUM(浏览人数), 2) AS 浏览转下单率
FROM banded
GROUP BY 价格档
ORDER BY 价格档;
