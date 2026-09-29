-- ============================================================
-- 08_threshold_sensitivity.sql   ★ 稳健性检验（挑战自己的结论）
-- ------------------------------------------------------------
-- 业务问题：20% 这条分界线，是我从数据里"看"出来的，
--           还是它本来就那么清楚？把线挪一挪，结论会不会塌？
--
-- 做法：把阈值从 10% 逐档挪到 35%，每一档都重算"线上/线下"的利润率，
--       看断崖是否一直在同一个位置出现。
--
-- 为什么必须做这一步：
--   任何一个"阈值型结论"都会面对同一个质疑——"这个数是不是你挑的？"
--   主动把敏感性测试摆出来，等于提前把这个质疑拆掉。
--
-- 实际结论（重要）：
--   阈值取 20% 和取 25%，六个指标完全相同 —— 因为数据集里
--   20% 到 30% 之间**没有任何一条订单**。discount 只有 12 个离散档位：
--   0 / 0.10 / 0.15 / 0.20 / 0.30 / 0.32 / 0.40 / 0.45 / 0.50 / 0.60 / 0.70 / 0.80
--   所以严谨的表述是"分水岭位于 20%-30% 之间，本数据无法进一步定位"，
--   而不是"20% 是一条清晰的分界线"。
--   要回答"17% 会怎样"，只能做价格实验——公司从来没打过 17% 的折。
--
-- 语法要点：
--   VALUES (0.10),(0.15)...   —— 用字面量直接构造一张"参数表"
--   CROSS JOIN                —— 参数表 × 明细表，一个查询扫完所有阈值
--                                （比复制粘贴 6 段 SQL 更不容易出错）
-- ============================================================

WITH thresholds(t) AS (
    VALUES (0.10), (0.15), (0.20), (0.25), (0.30), (0.35)
)

SELECT
    CAST(ROUND(t * 100) AS INTEGER)                              AS threshold_pct,

    -- 线以下（折扣 <= 阈值）：温和让利的部分
    ROUND(100.0 * SUM(profit) FILTER (WHERE discount <= t)
          / NULLIF(SUM(sales) FILTER (WHERE discount <= t), 0), 2) AS low_margin_pct,

    -- 线以上（折扣 > 阈值）：断崖部分
    ROUND(100.0 * SUM(profit) FILTER (WHERE discount > t)
          / NULLIF(SUM(sales) FILTER (WHERE discount > t), 0), 2)  AS high_margin_pct,

    -- 这一档要砍掉多少钱
    ROUND(SUM(profit) FILTER (WHERE discount > t), 0)            AS high_band_profit,

    -- 相当于全年利润的多大比例（分母是全域总利润 286,397）
    ROUND(100.0 * SUM(profit) FILTER (WHERE discount > t)
          / (SELECT SUM(profit) FROM staging.stg_orders), 1)     AS high_loss_pct_of_total_profit

FROM thresholds
CROSS JOIN staging.stg_orders
GROUP BY t
ORDER BY t;
