-- SPDX-License-Identifier: MIT
-- SPDX-FileCopyrightText: 2026 Tina-sud

-- ============================================================
-- 04_yearly_trend.sql
-- ------------------------------------------------------------
-- 业务问题：增长是真的在变好，还是只是规模变大？
--
-- 看销售额增长会得出"很好"的结论；看利润率才知道真相。
-- 这个查询同时给出两个维度，并算同比增长率。
--
-- 实际结论：销售四年增长 51%，利润率在 10.2%–13.4% 区间来回，
--           2018 年利润率还比 2017 年下降了 0.7 个百分点。
--
-- 语法要点：
--   LAG(x, 1) OVER (ORDER BY year) —— 取"上一行"的值，做同比的核心工具
--   必须先算好年度汇总，再在外面套一层查 LAG
--   （因为窗口函数不能直接引用同一层的聚合结果）
-- ============================================================

WITH yearly AS (
    SELECT
        YEAR(order_date)                                  AS order_year,
        COUNT(DISTINCT order_id)                          AS orders,
        ROUND(SUM(sales), 0)                              AS sales,
        ROUND(SUM(profit), 0)                             AS profit,
        ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 2) AS margin_pct
    FROM staging.stg_orders
    GROUP BY YEAR(order_date)
)

SELECT
    order_year,
    orders,
    sales,
    profit,
    margin_pct,

    -- 上一年销售额：LAG 取前一行的 sales
    LAG(sales) OVER (ORDER BY order_year)                 AS prev_year_sales,

    -- 销售同比增长率
    ROUND(
        100.0 * (sales - LAG(sales) OVER (ORDER BY order_year))
        / NULLIF(LAG(sales) OVER (ORDER BY order_year), 0), 1
    )                                                     AS sales_yoy_pct,

    -- 利润率同比变化（百分点，不是百分比）
    ROUND(margin_pct - LAG(margin_pct) OVER (ORDER BY order_year), 2) AS margin_yoy_pp

FROM yearly
ORDER BY order_year;
