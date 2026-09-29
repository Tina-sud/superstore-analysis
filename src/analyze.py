# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Tina-sud

"""执行 sql/ 目录下的所有查询，把结果导出成 CSV。

设计上刻意把 SQL 放在独立文件里，而不是写成 Python 字符串：
  * SQL 文件能单独丢进任何数据库客户端跑，方便调试和交付
  * 面试官直接点开 sql/ 目录就能看到你的查询能力（语法高亮都正常）
  * Python 只负责"编排"，不掺业务逻辑——这是数据开发的标准分工

用法：
    python -m src.analyze
"""
from __future__ import annotations

import duckdb

from src.db import SQL_DIR, TABLE_DIR, connect

def load_query(path) -> str:
    """读取一个 .sql 文件。"""
    return path.read_text(encoding="utf-8")


def run_all_queries(con: duckdb.DuckDBPyConnection) -> list[str]:
    """按文件名顺序执行全部查询，返回生成的文件名列表。"""
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    sql_files = sorted(SQL_DIR.glob("*.sql"))
    if not sql_files:
        raise FileNotFoundError(f"{SQL_DIR} 下没有找到任何 .sql 文件")

    produced: list[str] = []
    print("\n" + "=" * 68)
    print("执行分析查询")
    print("=" * 68)

    for path in sql_files:
        sql = load_query(path)
        # .df() 直接把结果转成 pandas DataFrame，省掉手工拼字段名
        df = con.execute(sql).df()

        # 导出的 CSV 用 utf-8-sig 编码：带 BOM，Excel 打开中文不乱码
        out = TABLE_DIR / f"{path.stem}.csv"
        df.to_csv(out, index=False, encoding="utf-8-sig")

        produced.append(path.stem)
        print(f"[RUN ] {path.name:<32} -> {len(df):>3} 行 × {len(df.columns)} 列")

    print("-" * 68)
    print(f"共 {len(produced)} 个查询，结果已导出到 {TABLE_DIR.relative_to(SQL_DIR.parent)}")
    return produced


def main() -> None:
    con = connect()
    try:
        run_all_queries(con)
    finally:
        con.close()
    print("[ANALYZE] 完成")


if __name__ == "__main__":
    main()
