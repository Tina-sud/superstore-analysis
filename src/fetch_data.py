"""下载原始数据集。

项目已经把 data/raw/superstore.csv 一起放进仓库了，正常情况下
你不需要运行这个脚本。它存在的意义有两个：

1. 证明数据是有出处、可复现的（面试官会问"数据哪来的"）
2. 记录一个真实的数据源陷阱——见下面 SANITY 部分

用法：
    python -m src.fetch_data
"""
from __future__ import annotations

import csv
import sys
import urllib.request
from pathlib import Path

from src.db import RAW_DIR

# 多个镜像地址，前面的失败了会自动试下一个
SOURCES = [
    "https://raw.githubusercontent.com/leonism/sample-superstore/master/data/superstore.csv",
]

FILENAME = "superstore.csv"


def _download(url: str, dest: Path) -> None:
    print(f"[FETCH] 下载 {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as fh:
        fh.write(resp.read())
    print(f"[FETCH] 已保存 {dest}  ({dest.stat().st_size:,} 字节)")


def _strip_extra_sheets(src: Path) -> None:
    """剔除文件里混入的其他工作表。

    为什么需要这一步（这段值得你在面试里讲）：
    这个镜像文件其实把 Tableau 官方示例的**三张工作表**拼成了一个 CSV：

        第 1     行    : 订单表表头（21 列）
        第 2~9995 行   : 订单表数据（9994 行）  ← 我们要的
        第 9996 行     : "Person,Region"      ← 人员表表头
        第 9997~10000 行: 人员表数据（4 行）
        第 10001 行    : "Returned,Order ID"  ← 退货表表头
        第 10002~10801行: 退货表数据（800 行）

    如果直接当作订单表读进来，会污染分析结果。
    这也是为什么"加载前先校验 schema"是数据开发的基本功——
    这次问题很显眼，但生产环境里的表结构漂移往往没这么友好。
    """
    with open(src, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        ncol = len(header)
        kept, dropped = [], 0
        for row in reader:
            # 只保留字段数与表头一致的行，其余一律丢弃
            if len(row) == ncol:
                kept.append(row)
            else:
                dropped += 1

    with open(src, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(kept)

    print(f"[SANITY] 表头 {ncol} 列 | 保留 {len(kept):,} 行 | 剔除异常行 {dropped:,} 行")


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    dest = RAW_DIR / FILENAME

    last_err: Exception | None = None
    for url in SOURCES:
        try:
            _download(url, dest)
            break
        except Exception as exc:  # noqa: BLE001 - 换下一个源重试
            last_err = exc
            print(f"[FETCH] 失败：{exc}")
    else:
        print(f"[FETCH] 所有镜像都失败了。最后一个错误：{last_err}")
        sys.exit(1)

    _strip_extra_sheets(dest)
    print("[FETCH] 完成")


if __name__ == "__main__":
    main()
