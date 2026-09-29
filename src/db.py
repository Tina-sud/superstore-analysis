"""数据库连接与全局路径常量。

整个项目所有文件都从这里取路径，避免出现"在我机器上能跑"的问题。
"""
from pathlib import Path

import duckdb

# ROOT 指向项目根目录（src 的上一级）。
# __file__ 是当前文件的路径，parents[1] 就是上两级目录。
ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"          # 原始 CSV，只读不改
DB_PATH = DATA_DIR / "superstore.duckdb"   # DuckDB 单文件数据库

SQL_DIR = ROOT / "sql"

REPORT_DIR = ROOT / "reports"
TABLE_DIR = REPORT_DIR / "tables"   # SQL 查询结果导出为 CSV
FIG_DIR = REPORT_DIR / "figures"    # matplotlib 生成的图片


def connect(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """打开 DuckDB 连接。

    参数
    ----
    read_only : bool
        为 True 时以只读方式打开。绘图脚本只用它读数据，
        这样即使同时有别的进程写入也不会冲突。
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def ensure_dirs() -> None:
    """确保输出目录存在。第一次运行时用得上。"""
    for d in (RAW_DIR, TABLE_DIR, FIG_DIR):
        d.mkdir(parents=True, exist_ok=True)
