-- SPDX-License-Identifier: MIT
-- SPDX-FileCopyrightText: 2026 Tina-sud

-- ============================================================
-- 01_overview.sql
-- ------------------------------------------------------------
-- 业务问题：这家零售公司四年的整体经营状况如何？
--          哪些数字需要管理层立刻关注？
--
-- 我用一句话概括结论：
--   销售额从 48.4 万涨到 73.3 万（+51%），但利润率始终卡在 12–13%，
--   增长没有转化为利润。这不是"卖得不够多"的问题。
--
-- 产出：整体 KPI 一行汇总（供 README 和备忘录引用）
-- ============================================================

SELECT
    -- 总销售额。ROUND(x, 0) 把小数抹掉，方便阅读
    ROUND(SUM(sales), 0)                                AS total_sales,

    -- 总利润
    ROUND(SUM(profit), 0)                               AS total_profit,

    -- 利润率 = 利润 / 销售额。乘 100 变成百分数，
    -- NULLIF 防止分母为 0 时除零报错
    ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 2) AS margin_pct,

    -- COUNT(DISTINCT ...) 去重计数：一个订单有多个商品行，所以订单数 < 行数
    COUNT(DISTINCT order_id)                            AS total_orders,

    COUNT(*)                                            AS total_rows,

    -- 客单价 = 销售额 / 订单数
    ROUND(SUM(sales) / NULLIF(COUNT(DISTINCT order_id), 0), 2) AS avg_order_value,

    -- 时间跨度
    MIN(order_date)                                     AS first_order_date,
    MAX(order_date)                                     AS last_order_date,

    -- 有多少比例的订单行其实在亏钱？这个数字是整份分析的引子
    ROUND(100.0 * COUNT(*) FILTER (WHERE profit < 0) / COUNT(*), 1) AS loss_row_pct

FROM staging.stg_orders;
