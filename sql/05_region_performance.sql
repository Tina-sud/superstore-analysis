-- SPDX-License-Identifier: MIT
-- SPDX-FileCopyrightText: 2026 Tina-sud

-- ============================================================
-- 05_region_performance.sql
-- ------------------------------------------------------------
-- 业务问题：四个大区里，哪个在拖后腿？问题出在"卖得少"还是"定价松"？
--
-- 这个查询同时算两个指标，逼自己回答"为什么"而不是只报数字：
--   - 销售占比：是不是这个区本身规模就小？
--   - 利润率  ：还是规模不小但赚不到钱？
--
-- 实际结论：Central 区销售额排第三（50.1 万），不算小，
--           但利润率 7.92% 是四区最低，只有 West 的一半。
--           而且 Central 的折扣率（下面 discount_pct）明显高于其他区——
--           这就把"区域问题"和"折扣问题"连成了一条因果链。
--
-- 语法要点：
--   SUM(sales) / SUM(sales) OVER () —— 分母是"全表合计"，
--     窗口函数里 OVER () 什么都不写，表示"整张表当一个分区"。
--     这比自己再写一个子查询干净得多。
-- ============================================================

SELECT
    region,

    COUNT(DISTINCT order_id)                                  AS orders,
    ROUND(SUM(sales), 0)                                      AS sales,
    ROUND(SUM(profit), 0)                                     AS profit,
    ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 2)     AS margin_pct,

    -- 销售占比：排除"这个区本来就小"的解释
    ROUND(100.0 * SUM(sales) / SUM(SUM(sales)) OVER (), 1)    AS sales_share_pct,

    -- 平均折扣率：加权平均（按销售额加权），比简单 AVG 更贴近真实让利
    -- 简单 AVG(discount) 会让一笔 5 美元的小单和一笔 5000 美元的大单权重相同
    ROUND(100.0 * SUM(discount * sales) / NULLIF(SUM(sales), 0), 2) AS weighted_discount_pct,

    -- 高折扣订单行占比（> 20%）
    ROUND(100.0 * COUNT(*) FILTER (WHERE discount > 0.20) / COUNT(*), 1) AS high_discount_line_pct,

    -- 亏损订单行占比
    ROUND(100.0 * COUNT(*) FILTER (WHERE profit < 0) / COUNT(*), 1) AS loss_line_pct

FROM staging.stg_orders
GROUP BY region
ORDER BY margin_pct ASC;
