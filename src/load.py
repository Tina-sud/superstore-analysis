"""数据加载：raw 层 + staging 层。

为什么要有两层？（这是数据开发岗的核心概念，务必理解）

  raw 层      —— 原始数据原样入库，不做任何加工。列名保留空格、
                 所有字段都当字符串。它存在的意义是"可以随时重跑"：
                 清洗逻辑写错了，不影响原始数据。
  staging 层  —— 清洗后可直接分析的数据。列名改成 snake_case，
                 字段转成正确的类型，日期转成真正的 DATE。

生产环境里通常还有第三层 mart 层（面向具体报表预聚合的表），
这个项目规模小，分析 SQL 直接查 staging 就够，不为了分层而分层。

用法：
    python -m src.load
"""
from __future__ import annotations

import duckdb

from src.db import RAW_DIR, connect

RAW_CSV = RAW_DIR / "superstore.csv"

# ---------------------------------------------------------------
# staging 层的字段映射：原始列名 -> (新列名, 目标类型)
# 显式写出来而不是靠自动推断，是因为自动推断会随数据变化，
# 今天推断成 INTEGER，明天数据里多了个小数点就变成 DOUBLE，很脆弱。
# ---------------------------------------------------------------
STAGING_COLUMNS = [
    ("Row ID",        "row_id",        "INTEGER"),
    ("Order ID",      "order_id",      "VARCHAR"),
    ("Order Date",    "order_date",    "DATE"),
    ("Ship Date",     "ship_date",     "DATE"),
    ("Ship Mode",     "ship_mode",     "VARCHAR"),
    ("Customer ID",   "customer_id",   "VARCHAR"),
    ("Customer Name", "customer_name", "VARCHAR"),
    ("Segment",       "segment",       "VARCHAR"),
    ("Country",       "country",       "VARCHAR"),
    ("City",          "city",          "VARCHAR"),
    ("State",         "state",         "VARCHAR"),
    ("Postal Code",   "postal_code",   "VARCHAR"),
    ("Region",        "region",        "VARCHAR"),
    ("Product ID",    "product_id",    "VARCHAR"),
    ("Category",      "category",      "VARCHAR"),
    ("Sub-Category",  "sub_category",  "VARCHAR"),
    ("Product Name",  "product_name",  "VARCHAR"),
    ("Sales",         "sales",         "DOUBLE"),
    ("Quantity",      "quantity",      "INTEGER"),
    ("Discount",      "discount",      "DOUBLE"),
    ("Profit",        "profit",        "DOUBLE"),
]

# 日期列需要特殊处理：源文件里是 11/8/2017 这种美式格式（月/日/年），
# 必须显式指定格式，否则 DuckDB 可能按 日/月/年 解析——
# 那样 11/8 会变成 8 月 11 日，整份分析的时间维度全错且不会报错。
DATE_COLUMNS = {"order_date", "ship_date"}
DATE_FORMAT = "%m/%d/%Y"


def build_raw(con: duckdb.DuckDBPyConnection) -> None:
    """raw 层：原样装载，所有字段先当字符串。"""
    csv_path = RAW_CSV.as_posix()
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")

    # all_varchar=true 是刻意的：让 raw 层完全不依赖类型推断。
    # 这样即使 Source 数据格式有变，raw 层也不会加载失败。
    con.execute(
        f"""
        CREATE OR REPLACE TABLE raw.superstore AS
        SELECT * FROM read_csv_auto('{csv_path}', all_varchar = true)
        """
    )
    n = con.execute("SELECT COUNT(*) FROM raw.superstore").fetchone()[0]
    print(f"[LOAD] raw.superstore            {n:>7,} 行（全部按字符串读入）")


def build_staging(con: duckdb.DuckDBPyConnection) -> None:
    """staging 层：列名规范化 + 类型转换 + 日期解析。"""
    selects = []
    for src_name, new_name, dtype in STAGING_COLUMNS:
        if new_name in DATE_COLUMNS:
            # strptime 把字符串按指定格式转成时间戳，再取日期部分
            expr = f"strptime(\"{src_name}\", '{DATE_FORMAT}')::DATE"
        else:
            expr = f'CAST("{src_name}" AS {dtype})'
        selects.append(f"    {expr} AS {new_name}")

    con.execute("CREATE SCHEMA IF NOT EXISTS staging")
    con.execute(
        "CREATE OR REPLACE TABLE staging.stg_orders AS\nSELECT\n"
        + ",\n".join(selects)
        + "\nFROM raw.superstore"
    )
    n = con.execute("SELECT COUNT(*) FROM staging.stg_orders").fetchone()[0]
    print(f"[LOAD] staging.stg_orders        {n:>7,} 行（列名规范化 + 类型转换完成）")


def main() -> None:
    if not RAW_CSV.exists():
        raise FileNotFoundError(
            f"找不到原始数据 {RAW_CSV}\n"
            f"请先运行：python -m src.fetch_data"
        )

    con = connect()
    try:
        build_raw(con)
        build_staging(con)
    finally:
        con.close()

    print("[LOAD] 完成")


if __name__ == "__main__":
    main()
