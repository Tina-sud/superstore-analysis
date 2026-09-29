-- SPDX-License-Identifier: MIT
-- SPDX-FileCopyrightText: 2026 Tina-sud

-- ============================================================
-- 02_discount_impact.sql   ★ 核心查询
-- ------------------------------------------------------------
-- 业务问题：利润被什么吃掉了？
--
-- 这是整份分析里最重要的一个查询。它把订单按折扣力度分档，
-- 看每档的利润率。如果折扣和利润的关系是"温和下降"，
-- 那只是定价策略偏松；如果是"断崖式转负"，那是亏损性增长。
--
-- 实际结论：折扣一过 20%，利润率断崖转负。
--   折扣 ≤ 20% 时利润率还有 11–30%；
--   折扣 > 20% 时利润率为负，45% 以上档位 100% 的订单在亏钱。
--
-- ⚠ 表述上的一个坑（由 08_threshold_sensitivity.sql 发现）：
--   本数据集的 discount 不是连续变量，只有 12 个离散档位，
--   且在 0.20 与 0.30 之间没有任何观测。所以阈值取 20% 和取 25%
--   会得到完全相同的结果——严谨的说法是"分水岭位于 20%–30% 之间，
--   本数据无法进一步定位"，不能说成"20% 是一条清晰的分界线"。
--   分档标签因此也按真实取值改写（原标签"21-30%"实为 227 行全部 30%）。
--
-- 语法要点：
--   CASE WHEN ... THEN ... END  —— 手写分档（比 NTILE 更可控，
--                                  因为业务阈值是人定的，不是均分）
--   COUNT(*) FILTER (WHERE ...) —— 条件计数，比 SUM(CASE WHEN...) 好读
--   ORDER BY MIN(discount)      —— 按折扣大小排序，而不是按分档名的字母序
-- ============================================================

WITH bucketed AS (
    SELECT
        -- 把连续的 discount 值映射到业务能讨论的档位。
        -- 标签按数据里的真实取值写，不写"区间"——区间会让人误以为范围内有数据。
        CASE
            WHEN discount = 0        THEN '1. 无折扣'
            WHEN discount <= 0.10    THEN '2. 10%'
            WHEN discount <= 0.20    THEN '3. 15%/20%'
            WHEN discount <= 0.30    THEN '4. 30%'
            WHEN discount <= 0.40    THEN '5. 32%/40%'
            ELSE                          '6. 45% 以上'
        END                       AS discount_band,
        discount,
        sales,
        profit
    FROM staging.stg_orders
)

SELECT
    discount_band,

    COUNT(*)                                                  AS order_lines,
    ROUND(SUM(sales), 0)                                      AS sales,

    -- 这一档总共赚了还是亏了
    ROUND(SUM(profit), 0)                                     AS profit,

    -- 这一档的利润率——最关键的一列
    ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 2)     AS margin_pct,

    -- 这一档里亏损订单行占多少比例
    ROUND(100.0 * COUNT(*) FILTER (WHERE profit < 0) / COUNT(*), 1) AS loss_line_pct,

    -- 这一档占全部销售额的比重：用来判断"问题有多大"
    ROUND(100.0 * SUM(sales) / (SELECT SUM(sales) FROM staging.stg_orders), 1) AS sales_share_pct

FROM bucketed
GROUP BY discount_band
ORDER BY MIN(discount);
