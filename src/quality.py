"""数据质量校验。

面试时如果你只展示"我算出了利润率是 12.47%"，说服力有限。
如果你能说"我在这张表上跑了 8 项校验，其中 1 项发现了问题，
我这样处理的"——那是完全不同的层次。

这个模块的每一条校验都对应一类真实的生产事故：
  * 行数突变     -> 上游重复推数 / 漏推
  * 主键重复     -> 唯一约束被破坏，后续 join 会放大数据
  * 空值         -> 聚合结果静默变小（SUM 会忽略 NULL，不报错）
  * 日期倒挂     -> 时区或格式解析问题
  * 取值越界     -> 单位错误（比如折扣存成了 20 而不是 0.2）
  * 枚举越界     -> 上游新增了未预期的分类值
  * 粒度不一致   -> 订单级属性在明细表里发生变化，
                    后续 join 会成倍放大行数，而 SUM 不会报错

用法：
    python -m src.quality
退出码 0 表示全部通过，1 表示有校验失败。
"""
from __future__ import annotations

import sys

import duckdb

from src.db import connect

# 每条校验 = (名称, 说明, 失败的 SQL)。SQL 返回 0 表示通过，非 0 表示失败。
CHECKS: list[tuple[str, str, str]] = [
    (
        "row_count",
        "总行数应为 9994（原始文件已剔除混入的 People/Returns 工作表）",
        """
        SELECT CASE WHEN COUNT(*) = 9994 THEN 0 ELSE 1 END
        FROM staging.stg_orders
        """,
    ),
    (
        "pk_unique",
        "row_id 应为主键，不能重复",
        """
        SELECT CASE WHEN COUNT(*) = COUNT(DISTINCT row_id) THEN 0 ELSE 1 END
        FROM staging.stg_orders
        """,
    ),
    (
        "no_null_keys",
        "order_id / customer_id / product_id 不应为空",
        """
        SELECT COUNT(*) FROM staging.stg_orders
        WHERE order_id IS NULL OR customer_id IS NULL OR product_id IS NULL
        """,
    ),
    (
        "no_null_measures",
        "sales / quantity / discount / profit 不应为空（空值会被 SUM 静默忽略）",
        """
        SELECT COUNT(*) FROM staging.stg_orders
        WHERE sales IS NULL OR quantity IS NULL
           OR discount IS NULL OR profit IS NULL
        """,
    ),
    (
        "date_sanity",
        "发货日期不应早于下单日期，且订单日期应落在 2015-2018",
        """
        SELECT COUNT(*) FROM staging.stg_orders
        WHERE ship_date < order_date
           OR order_date < DATE '2015-01-01'
           OR order_date > DATE '2018-12-31'
        """,
    ),
    (
        "value_range",
        "折扣应在 [0, 0.8]，数量应为正，销售额应为正",
        """
        SELECT COUNT(*) FROM staging.stg_orders
        WHERE discount < 0 OR discount > 0.8
           OR quantity <= 0 OR sales <= 0
        """,
    ),
    (
        "enum_domain",
        "category 与 region 的取值应在预期集合内",
        """
        SELECT COUNT(*) FROM staging.stg_orders
        WHERE category NOT IN ('Furniture', 'Office Supplies', 'Technology')
           OR region   NOT IN ('Central', 'East', 'South', 'West')
        """,
    ),
    (
        "order_grain_consistency",
        "同一 order_id 内的订单级属性（日期/客户/配送方式/州/区域）应唯一"
        "——不唯一说明订单表和明细表粒度混了，后续 join 会成倍放大数据",
        """
        SELECT COUNT(*) FROM (
            SELECT order_id
            FROM staging.stg_orders
            GROUP BY order_id
            HAVING COUNT(DISTINCT order_date) > 1
                OR COUNT(DISTINCT ship_date)  > 1
                OR COUNT(DISTINCT customer_id) > 1
                OR COUNT(DISTINCT ship_mode)  > 1
                OR COUNT(DISTINCT state)      > 1
                OR COUNT(DISTINCT region)     > 1
                OR COUNT(DISTINCT segment)    > 1
        )
        """,
    ),
]


def run_checks(con: duckdb.DuckDBPyConnection) -> bool:
    """跑完所有校验，返回是否全部通过。"""
    print("\n" + "=" * 68)
    print("数据质量校验")
    print("=" * 68)

    all_passed = True
    for name, desc, sql in CHECKS:
        failed = con.execute(sql).fetchone()[0]
        ok = failed == 0
        all_passed &= ok
        flag = "PASS" if ok else "FAIL"
        print(f"[{flag}] {name:<18} {desc}")
        if not ok:
            print(f"       └─ 有 {failed} 条记录不满足")

    print("-" * 68)
    print(f"结果：{'全部通过' if all_passed else '存在失败项，请先处理再继续'}")
    return all_passed


def main() -> None:
    con = connect(read_only=True)
    try:
        ok = run_checks(con)
    finally:
        con.close()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
