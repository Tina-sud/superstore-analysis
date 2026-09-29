# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Tina-sud

"""下载原始数据集。

项目已经把 data/raw/superstore.csv 一起放进仓库了，正常情况下
你不需要运行这个脚本。它存在的意义有三个：

1. 证明数据是有出处、可复现的（面试官会问"数据哪来的"）
2. 记录一个真实的数据源陷阱——见下面 SANITY 部分
3. 保留一条"数据可重新获取"的路径——万一仓库里的数据副本因授权原因被移除，
   执行本脚本即可重新拿到数据，代码本身不受影响

数据出处与授权状态（重要，勿删）：
    数据集的作者与权利人是 Tableau Software（Salesforce, Inc.）。
    官方在 Tableau Public → Learn → Sample Data 页面公开发布该数据，供学习与教学使用，
    并说明它描述的是一个虚构公司。
    **该数据集不属于本项目，也不受本仓库 MIT 许可证的覆盖。**
    完整的出处、授权状态与使用限制见仓库根目录的 NOTICE.md 第 1 节。

用法：
    python -m src.fetch_data                 # 下载 + schema 校验
    python -m src.fetch_data --strip-only    # 只对已存在的文件做 schema 校验
"""
from __future__ import annotations

import csv
import os
import sys
import urllib.request
from pathlib import Path

from src.db import RAW_DIR

# 数据集的官方来源（出处登记，不是下载地址）：
#   Tableau Public → Learn → Sample Data
#   https://public.tableau.com/app/learn/sample-data
#   条目 "Superstore Sales"，官方同时提供 xls / csv / xlsx 下载。
#
# 下面这个地址只是 GitHub 上的一份公开镜像，用于脚本化下载。
# 注意两点：该镜像**未声明任何 License**；且文件里混入了另外两张工作表
# （见 NOTICE.md 第 1 节，与下方 _strip_extra_sheets 的说明）。
#
# 这里**刻意只保留一个源**：多个镜像可能各自是不同版本的数据集，
# 一旦前一个失败、后一个顶上，分析结果会在你不知情的情况下改变。
# 与其"能下载就行"，不如失败时明确告诉你手动去哪拿。
SOURCES = [
    "https://raw.githubusercontent.com/leonism/sample-superstore/master/data/superstore.csv",
]

FILENAME = "superstore.csv"

# 单个源的重试次数。这类镜像偶尔会掐断连接，重试通常就能过。
RETRIES = 3


def _download(url: str, dest: Path) -> None:
    """下载到临时文件，完整拿到内容后再原子替换。

    为什么不直接写 dest：如果连接在传输中途断掉，直接写会把仓库里
    唯一的数据副本截断成半截文件——而这份数据正是"移除后如何恢复"的那条路径，
    不能被自己毁掉。先写 .part，成功后用 os.replace 一步换名，
    结果只可能是两种：完整的新文件，或原封不动的旧文件。
    """
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = resp.read()  # 内容全部读完才算成功
    if not payload:
        raise ValueError("服务端返回空内容")
    tmp.write_bytes(payload)
    os.replace(tmp, dest)
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
        try:
            header = next(reader)
        except StopIteration:
            raise SystemExit(
                f"[SANITY] {src} 是空文件，无法校验。请确认下载是否完整，"
                f"或从官方页面 https://public.tableau.com/app/learn/sample-data 手动获取。"
            )
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
    existed_before = dest.exists()

    last_err: Exception | None = None
    for url in SOURCES:
        for attempt in range(1, RETRIES + 1):
            try:
                print(f"[FETCH] 下载 {url}  （第 {attempt}/{RETRIES} 次）")
                _download(url, dest)
                last_err = None
                break
            except Exception as exc:  # noqa: BLE001 - 换下一个源重试
                last_err = exc
                print(f"[FETCH] 失败：{exc}")
        if last_err is None:
            break

    if last_err is not None:
        # 下载失败时，仓库里那份数据必须完好无损（_download 保证了这一点）
        print()
        print("[FETCH] 自动下载失败：镜像不可达或被限流。")
        if existed_before:
            print(f"[FETCH] 仓库里已有的数据副本**未被改动**：{dest}")
        print("[FETCH] 手动获取方式：")
        print('        1. 打开 Tableau 官方示例数据页  https://public.tableau.com/app/learn/sample-data')
        print('        2. 找到 "Superstore Sales"，下载 CSV 或 Excel 版本')
        print(f'        3. 保存为 {dest}')
        print('        4. 执行  python -m src.fetch_data --strip-only  完成 schema 校验剔除')
        sys.exit(1)

    _strip_extra_sheets(dest)
    print("[FETCH] 完成")


if __name__ == "__main__":
    if "--strip-only" in sys.argv:
        _strip_extra_sheets(RAW_DIR / FILENAME)
    else:
        main()
