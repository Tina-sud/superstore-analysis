"""一键跑通整条流水线。

    python run_all.py

流程：
    原始 CSV -> raw 层 -> staging 层 -> 数据质量校验 -> 分析查询 -> 图表

任何一步失败都会立即停下并说明原因，不会带着脏数据往下跑。
"""
from __future__ import annotations

import sys
import time

# 让 src 能被导入。直接 python run_all.py 时，Python 把脚本所在目录
# 加进 sys.path，所以 src 包是可用的。
from src import analyze, charts, fetch_data, load, quality
from src.db import DB_PATH, FIG_DIR, RAW_DIR, TABLE_DIR, connect, ensure_dirs


def banner(text: str) -> None:
    print("\n" + "#" * 68)
    print(f"#  {text}")
    print("#" * 68)


def main() -> int:
    started = time.perf_counter()
    ensure_dirs()

    # ---- 步骤 1：确保原始数据存在 ------------------------------------
    banner("步骤 1/5  检查原始数据")
    raw_csv = RAW_DIR / "superstore.csv"
    if raw_csv.exists():
        print(f"[OK  ] 已存在 {raw_csv}  ({raw_csv.stat().st_size:,} 字节)")
    else:
        print("[WARN] 原始数据不存在，开始下载……")
        fetch_data.main()

    # ---- 步骤 2：装载 raw + staging ----------------------------------
    banner("步骤 2/5  装载数据（raw -> staging）")
    con = connect()
    try:
        load.build_raw(con)
        load.build_staging(con)

        # ---- 步骤 3：数据质量校验 ------------------------------------
        banner("步骤 3/5  数据质量校验")
        if not quality.run_checks(con):
            print("\n[ABORT] 数据质量不达标，流水线中止。")
            return 1

        # ---- 步骤 4：跑分析查询 --------------------------------------
        banner("步骤 4/5  执行分析查询")
        analyze.run_all_queries(con)
    finally:
        con.close()

    # ---- 步骤 5：出图 -------------------------------------------------
    banner("步骤 5/5  生成图表")
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for fn in charts.CHARTS:
        out = fn()
        print(f"[FIG ] {out.name}")

    elapsed = time.perf_counter() - started
    banner("完成")
    print(f"总耗时 {elapsed:.1f} 秒")
    print(f"  数据库   {DB_PATH}")
    print(f"  结果表   {TABLE_DIR}")
    print(f"  图表     {FIG_DIR}")
    print(f"\n下一步：打开 reports/findings.md，把里面的数字和你的判断对照一遍。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
