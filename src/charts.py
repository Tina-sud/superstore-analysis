"""生成图表。

三张图对应三个结论，不追求数量：
  图 1 折扣-利润率曲线   —— 定位问题（利润被折扣吃掉）
  图 2 子品类利润贡献     —— 定位责任（哪个产品线在出血）
  图 3 销售额 vs 利润率   —— 给出判断（增长质量差）

关于中文字体：matplotlib 默认字体不含中文，不设置会显示成一排方块。
Windows 上用 Microsoft YaHei（微软雅黑），这是系统自带字体。

用法：
    python -m src.charts
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 无界面后端：只出文件，不弹窗。服务器上跑也不报错
import matplotlib.pyplot as plt
import pandas as pd

from src.db import FIG_DIR, TABLE_DIR

# ---- 全局样式 ----------------------------------------------------------
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False   # 让负号正常显示，否则会是方块
plt.rcParams["figure.dpi"] = 130
plt.rcParams["savefig.bbox"] = "tight"       # 自动裁掉多余留白

LOSS_COLOR = "#C0392B"     # 亏损：红
PROFIT_COLOR = "#2E6DA4"   # 盈利：蓝
ACCENT = "#E67E22"         # 强调色：橙


def _read(name: str) -> pd.DataFrame:
    """读取 analyze.py 导出的结果 CSV。"""
    path = TABLE_DIR / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(
            f"缺少中间结果 {path}\n请先运行：python -m src.analyze"
        )
    return pd.read_csv(path)


# ======================================================================
# 图 1：折扣档位 vs 利润率（核心图）
# ======================================================================
def chart_discount_impact() -> Path:
    df = _read("02_discount_impact")

    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    colors = [LOSS_COLOR if m < 0 else PROFIT_COLOR for m in df["margin_pct"]]
    bars = ax.bar(df["discount_band"], df["margin_pct"], color=colors, width=0.62)

    # 每根柱子顶部标出数值，读者不用去估高度
    for bar, val in zip(bars, df["margin_pct"]):
        offset = 1.6 if val >= 0 else -3.4
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            val + offset,
            f"{val:.1f}%",
            ha="center",
            fontsize=9,
            color=PROFIT_COLOR if val >= 0 else LOSS_COLOR,
            fontweight="bold",
        )

    ax.axhline(0, color="#555555", linewidth=1)
    # 标出 20% 这条分界线——它是整份分析的核心发现
    ax.axvline(2.5, color=ACCENT, linestyle="--", linewidth=1.4)
    ax.text(2.58, ax.get_ylim()[1] * 0.86, "折扣 20% 分水岭",
            color=ACCENT, fontsize=9, fontweight="bold")

    ax.set_title("折扣一旦超过 20%，每一单都在亏钱", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("折扣档位")
    ax.set_ylabel("利润率 (%)")
    ax.spines[["top", "right"]].set_visible(False)

    out = FIG_DIR / "01_discount_vs_margin.png"
    fig.savefig(out)
    plt.close(fig)
    return out


# ======================================================================
# 图 2：子品类利润贡献
# ======================================================================
def chart_subcategory_profit() -> Path:
    df = _read("03_profit_by_subcategory").sort_values("profit")

    fig, ax = plt.subplots(figsize=(8.2, 6.4))
    colors = [LOSS_COLOR if p < 0 else PROFIT_COLOR for p in df["profit"]]
    bars = ax.barh(df["sub_category"], df["profit"], color=colors, height=0.68)

    # 先扩大 x 轴范围，给条形末端的数值标签留出空间，
    # 否则最边上那个标签会被画布边缘裁掉
    pad = (df["profit"].max() - df["profit"].min()) * 0.16
    ax.set_xlim(df["profit"].min() - pad, df["profit"].max() + pad)

    for bar, val in zip(bars, df["profit"]):
        label = f"{val:,.0f}"
        y = bar.get_y() + bar.get_height() / 2
        if val < 0:
            # 负值：标签放在条形左端外侧，右对齐
            ax.text(val - pad * 0.06, y, label, va="center", ha="right",
                    fontsize=8, color=LOSS_COLOR)
        else:
            ax.text(val + pad * 0.06, y, label, va="center", ha="left",
                    fontsize=8, color=PROFIT_COLOR)

    ax.axvline(0, color="#555555", linewidth=1)
    ax.set_title("17 个子品类：3 个在亏钱，Tables 一个就亏掉 1.77 万",
                 fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("累计利润（美元）")
    ax.spines[["top", "right"]].set_visible(False)

    out = FIG_DIR / "02_subcategory_profit.png"
    fig.savefig(out)
    plt.close(fig)
    return out


# ======================================================================
# 图 3：销售额增长 vs 利润率停滞
# ======================================================================
def chart_growth_quality() -> Path:
    df = _read("04_yearly_trend")

    fig, ax1 = plt.subplots(figsize=(8.2, 4.6))

    ax1.bar(df["order_year"].astype(str), df["sales"],
            color="#B8CCE4", width=0.55, label="销售额")
    ax1.set_xlabel("年份")
    ax1.set_ylabel("销售额（美元）", color="#4A6E9E")
    ax1.tick_params(axis="y", labelcolor="#4A6E9E")
    ax1.spines[["top"]].set_visible(False)

    # 第二个纵轴：利润率
    ax2 = ax1.twinx()
    ax2.plot(df["order_year"].astype(str), df["margin_pct"],
             color=ACCENT, marker="o", linewidth=2.2, markersize=7, label="利润率")
    for x, val in zip(df["order_year"].astype(str), df["margin_pct"]):
        ax2.text(x, val + 0.55, f"{val:.2f}%", ha="center",
                 color=ACCENT, fontsize=9, fontweight="bold")

    ax2.set_ylabel("利润率 (%)", color=ACCENT)
    ax2.tick_params(axis="y", labelcolor=ACCENT)
    ax2.set_ylim(df["margin_pct"].min() - 3, df["margin_pct"].max() + 3)
    ax2.spines[["top"]].set_visible(False)

    ax1.set_title("销售额四年涨了 51%，利润率原地踏步", fontsize=13, fontweight="bold", pad=12)

    # 合并两个轴的图例
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False, fontsize=9)

    out = FIG_DIR / "03_growth_quality.png"
    fig.savefig(out)
    plt.close(fig)
    return out


CHARTS = [chart_discount_impact, chart_subcategory_profit, chart_growth_quality]


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    print("\n" + "=" * 68)
    print("生成图表")
    print("=" * 68)
    for fn in CHARTS:
        out = fn()
        print(f"[FIG ] {out.name}")
    print("[CHARTS] 完成")


if __name__ == "__main__":
    main()
