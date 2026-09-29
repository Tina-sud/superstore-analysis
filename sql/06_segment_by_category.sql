-- SPDX-License-Identifier: MIT
-- SPDX-FileCopyrightText: 2026 Tina-sud

-- ============================================================
-- 06_segment_by_category.sql
-- ------------------------------------------------------------
-- 业务问题：三类客户（个人 Consumer / 企业 Corporate / 居家办公 Home Office）
--           在各品类上的盈利能力有什么差别？资源该往哪倾斜？
--
-- 这个查询演示两个常用手法：
--   1) 条件聚合做"透视表"（把行转成列）
--   2) 用两个维度交叉，找出结构性差异
--
-- 实际结论：Home Office 客户利润率最高（14.03%），
--           但它在 Furniture 上同样不赚钱——说明
--           Furniture 的问题不是"客户选错了"，而是产品线本身定价有问题。
--           这个交叉验证很重要：它能排除一个错误假设。
--
-- 语法要点：
--   SUM(CASE WHEN ... THEN x END) —— 条件聚合。
--     CASE 不匹配时返回 NULL，SUM 自动忽略 NULL，所以不用写 ELSE 0。
--     这就把"某类客户在某品类上的销售"变成了一列。
--   GROUP BY ROLLUP 没用这里——它会产生小计行，
--     对初学者来说容易在后续 join 时踩坑，需要时再加。
-- ============================================================

SELECT
    segment,

    -- 各品类的销售额：行转列
    ROUND(SUM(CASE WHEN category = 'Furniture'       THEN sales  END), 0) AS furniture_sales,
    ROUND(SUM(CASE WHEN category = 'Office Supplies' THEN sales  END), 0) AS office_sales,
    ROUND(SUM(CASE WHEN category = 'Technology'      THEN sales  END), 0) AS tech_sales,

    -- 各品类的利润率：这才是决策依据
    ROUND(100.0 * SUM(CASE WHEN category = 'Furniture'       THEN profit END)
                / NULLIF(SUM(CASE WHEN category = 'Furniture'       THEN sales END), 0), 1) AS furniture_margin,
    ROUND(100.0 * SUM(CASE WHEN category = 'Office Supplies' THEN profit END)
                / NULLIF(SUM(CASE WHEN category = 'Office Supplies' THEN sales END), 0), 1) AS office_margin,
    ROUND(100.0 * SUM(CASE WHEN category = 'Technology'      THEN profit END)
                / NULLIF(SUM(CASE WHEN category = 'Technology'      THEN sales END), 0), 1) AS tech_margin,

    -- 整体
    ROUND(SUM(sales), 0)                                            AS total_sales,
    ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 2)           AS overall_margin

FROM staging.stg_orders
GROUP BY segment
ORDER BY overall_margin DESC;
