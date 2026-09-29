-- ============================================================
-- 03_profit_by_subcategory.sql
-- ------------------------------------------------------------
-- 业务问题：如果只能砍掉一个产品线，砍哪个？
--
-- 光看销售额会选错。Furniture 卖了 74.2 万，看起来是支柱，
-- 但利润率只有 2.49%——几乎白干。
-- 必须看"利润"而不是"销售额"，才能找对方向。
--
-- 实际结论：Tables 一个子品类就亏掉 1.77 万，是最大的出血点。
--
-- 语法要点：
--   RANK() OVER (ORDER BY ...)  —— 窗口函数，按利润排名
--   SUM(...) OVER (ORDER BY ... ROWS UNBOUNDED PRECEDING)
--                              —— 累计求和（帕累托分析用）。
--                                 这是窗口函数与 GROUP BY 的本质区别：
--                                 GROUP BY 把多行压成一行，窗口函数保留每一行。
-- ============================================================

SELECT
    category,
    sub_category,

    COUNT(*)                                              AS order_lines,
    ROUND(SUM(sales), 0)                                  AS sales,
    ROUND(SUM(profit), 0)                                 AS profit,
    ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 2)  AS margin_pct,

    -- 按利润从低到高排名：第 1 名就是最亏的
    RANK() OVER (ORDER BY SUM(profit) ASC)                AS profit_rank_worst_first,

    -- 累计利润：用来找"砍掉亏损项后能省多少"
    ROUND(SUM(SUM(profit)) OVER (ORDER BY SUM(profit) ASC
                                 ROWS UNBOUNDED PRECEDING), 0) AS cumulative_profit

FROM staging.stg_orders
GROUP BY category, sub_category
ORDER BY profit ASC;
