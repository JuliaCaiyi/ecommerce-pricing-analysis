-- 05 同期群留存
-- 回答：新用户来了之后，隔一周、两周还回来多少？
-- 注意：数据止于 10/31，越靠右下的格子观察窗口越不完整，不能横向比较

WITH first_seen AS (
    SELECT user_id, MIN(DATE(event_time)) AS 首次日期
    FROM events
    GROUP BY user_id
),
user_week AS (
    SELECT
        f.user_id,
        CAST((JULIANDAY(f.首次日期) - JULIANDAY('2019-10-01')) / 7 AS INT) AS 首次周,
        CAST((JULIANDAY(DATE(e.event_time)) - JULIANDAY(f.首次日期)) / 7 AS INT) AS 第几周
    FROM events e
    JOIN first_seen f ON e.user_id = f.user_id
),
cohort AS (
    SELECT 首次周, 第几周, COUNT(DISTINCT user_id) AS 活跃人数
    FROM user_week
    GROUP BY 首次周, 第几周
)
SELECT
    首次周,
    MAX(CASE WHEN 第几周 = 0 THEN 活跃人数 END) AS 本群人数,
    ROUND(MAX(CASE WHEN 第几周 = 1 THEN 活跃人数 END) * 100.0 / MAX(CASE WHEN 第几周 = 0 THEN 活跃人数 END), 1) AS 第1周留存率,
    ROUND(MAX(CASE WHEN 第几周 = 2 THEN 活跃人数 END) * 100.0 / MAX(CASE WHEN 第几周 = 0 THEN 活跃人数 END), 1) AS 第2周留存率,
    ROUND(MAX(CASE WHEN 第几周 = 3 THEN 活跃人数 END) * 100.0 / MAX(CASE WHEN 第几周 = 0 THEN 活跃人数 END), 1) AS 第3周留存率
FROM cohort
GROUP BY 首次周
ORDER BY 首次周;

-- 附：用 ROW_NUMBER() 取每个用户的首次事件明细（首次进入时看的是什么品类/价位）
WITH ranked AS (
    SELECT user_id, event_time, event_type, category_code, price,
           ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY event_time) AS 第几次
    FROM events
)
SELECT category_code AS 首次浏览品类, COUNT(*) AS 用户数
FROM ranked
WHERE 第几次 = 1 AND category_code IS NOT NULL
GROUP BY category_code
ORDER BY 用户数 DESC
LIMIT 10;
