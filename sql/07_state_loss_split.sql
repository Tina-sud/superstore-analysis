-- SPDX-License-Identifier: MIT
-- SPDX-FileCopyrightText: 2026 Tina-sud

-- ============================================================
-- 07_state_loss_split.sql   ★ 州级亏损拆解
-- ------------------------------------------------------------
-- 业务问题：建议里说"把折扣卡在 20%"，那么各州的亏损，
--           是不是全部由超过 20% 的折扣造成的？
--
-- 为什么值得单独做这一问：
--   05_region_performance 只到"区域"层级（Central/East/South/West），
--   但区域是管理层划分的，卡折扣这个动作却发生在州一级。
--   要判断建议能不能落地，必须下沉到州——这是"把结论翻译成可执行动作"。
--
-- 拆法：把每个州的利润拆成两段
--   低折扣段（discount <= 0.20）：建议执行后仍然存在的部分
--   高折扣段（discount >  0.20）：建议要砍掉的部分
--
-- 判读规则（这才是这条查询的价值所在）：
--   低折扣段为正 -> 卡折扣能救这个州
--   低折扣段为负 -> 卡折扣救不了，问题在定价或成本，需要另外的措施
--
-- 实际结论：10 个净亏损州，低折扣段全部盈利（合计 +31,409），
--   亏损全部来自高折扣段（合计 -129,655）。
--   但 Pennsylvania 低折扣段利润率只有 1.34%（其余州 6%-13.7%），
--   说明它即便卡掉高折扣也只是"不再亏"，离全域 12.47% 还差得远。
--
-- 语法要点：
--   SUM(x) FILTER (WHERE 条件)  —— 条件聚合：一次扫描同时算两段，
--                                  比写两个子查询再 join 快且好读
--   RANK() OVER (ORDER BY ...)  —— 窗口函数排名，不折叠行
-- ============================================================

WITH split AS (
    SELECT
        state,
        SUM(sales)                                    AS sales,
        SUM(profit)                                   AS profit,

        -- 低折扣段：卡折扣之后还留下的部分
        SUM(sales)  FILTER (WHERE discount <= 0.20)   AS low_band_sales,
        SUM(profit) FILTER (WHERE discount <= 0.20)   AS low_band_profit,

        -- 高折扣段：建议要砍掉的部分
        SUM(profit) FILTER (WHERE discount >  0.20)   AS high_band_profit,

        COUNT(*)                                      AS lines,
        COUNT(*)    FILTER (WHERE discount >  0.20)   AS high_band_lines
    FROM staging.stg_orders
    GROUP BY state
),

ranked AS (
    SELECT
        *,
        -- 按净亏损排名：1 = 亏得最狠的州
        RANK() OVER (ORDER BY profit ASC) AS loss_rank
    FROM split
)

SELECT
    loss_rank,
    state,
    ROUND(sales, 0)                                             AS sales,
    ROUND(profit, 0)                                            AS profit,
    ROUND(100.0 * profit / NULLIF(sales, 0), 2)                 AS margin_pct,
    ROUND(low_band_profit, 0)                                   AS low_band_profit,
    ROUND(100.0 * low_band_profit / NULLIF(low_band_sales, 0), 2) AS low_band_margin_pct,
    ROUND(high_band_profit, 0)                                  AS high_band_profit,
    ROUND(100.0 * high_band_lines / lines, 1)                   AS high_band_line_pct
FROM ranked
WHERE profit < 0            -- 只看净亏损的州，共 10 个
ORDER BY profit;
