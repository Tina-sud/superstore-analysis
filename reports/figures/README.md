# reports/figures — 图表来源说明

本目录下的**全部图片均由本项目代码在运行时生成**，不含任何第三方素材。

| 文件 | 生成代码 | 数据来源 |
|---|---|---|
| `01_discount_vs_margin.png` | `src/charts.py` → `chart_discount_impact()` | `reports/tables/02_discount_impact.csv` |
| `02_subcategory_profit.png` | `src/charts.py` → `chart_subcategory_profit()` | `reports/tables/03_profit_by_subcategory.csv` |
| `03_growth_quality.png` | `src/charts.py` → `chart_growth_quality()` | `reports/tables/04_yearly_trend.csv` |

## 复现方式

```bash
python -m src.charts      # 只重新生成图表
python run_all.py         # 从原始数据完整重跑（含图表）
```

## 声明

- 这 3 张图是 **matplotlib 绘制的程序化图表**，不是截图、不是素材库图片、
  也不是他人作品的转发或二次修改。
- 仓库内**不包含**任何字体文件；渲染使用本机系统字体
  （优先 Microsoft YaHei / SimHei，缺失时回退 DejaVu Sans）。
- 未使用任何第三方 Logo、图标或徽章。
- 图表覆盖的 MIT 许可证（见根目录 `LICENSE`）；数据本身的出处与授权状态见
  根目录 [`NOTICE.md`](../../NOTICE.md) 第 1 节。

> 换一台电脑重新运行上面的命令，你会得到内容相同的图（字体渲染的像素细节可能略有差异）。
> 这也是"图表是自己生成的"最直接的证明。
