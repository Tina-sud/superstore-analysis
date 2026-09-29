# Superstore 经营诊断：销售额涨了 51%，利润率为什么原地踏步？

用 SQL 对 4 年、5,009 笔零售订单做了一次利润归因分析，
找出了"增长质量差"的根因，并给出可执行的建议。

> **数据**：Tableau Sample Superstore，2015–2018，9,994 行
> **技术栈**：DuckDB（SQL 分析）· pandas · matplotlib · Python
> **完整结论**：见 [reports/findings.md](reports/findings.md)

---

## 核心结论（30 秒版）

**折扣 20% 是这家公司的盈亏分界线。**

| 折扣档位 | 利润率 | 亏损订单占比 |
|---|---:|---:|
| 无折扣 | +29.51% | 0% |
| 11–20% | +11.58% | 14.0% |
| 21–30% | **−10.05%** | 91.6% |
| 40% 以上 | **−77.40%** | **100%** |

折扣 > 20% 的订单只占 13.9%，却造成 −13.5 万美元的利润损失——
**相当于全年利润的 47%**。同时销售额四年涨了 51%，利润率却始终停在 10%–13%。

## 三张图看懂全部分析

### 1. 折扣一旦超过 20%，每一单都在亏钱

![折扣 vs 利润率](reports/figures/01_discount_vs_margin.png)

### 2. 三个产品线在出血，Tables 是最大出血点

![子品类利润](reports/figures/02_subcategory_profit.png)

### 3. 销售额涨了 51%，利润率原地踏步

![增长质量](reports/figures/03_growth_quality.png)

## 这个项目展示了什么

**SQL 能力**（全部查询在 [`sql/`](sql/) 目录，每条带业务问题注释）：

- 分档聚合 + 条件聚合（`CASE WHEN`、`COUNT FILTER`）做折扣归因
- 窗口函数：`RANK() OVER` 做子品类排名、`SUM() OVER` 做累计帕累托、
  `LAG()` 算同比增长率
- `SUM(x) OVER ()` 窗口合计代替子查询算销售占比
- 条件聚合实现行转列（客户细分 × 品类透视）

**数据工程意识**：

- raw → staging 两层建模：raw 层全字段按字符串原样入库（可随时重跑），
  staging 层显式做列名规范化和类型转换
- **日期格式坑**：源文件日期是 `11/8/2017` 美式格式，必须显式指定
  `%m/%d/%Y` 解析，否则按日/月/年误读后时间维度全错且不报错
- **数据源校验**：下载源文件实际混入了 Tableau 示例的另外两张工作表
  （People 4 行 + Returns 800 行），加载前按字段数校验剔除了 806 行
- 7 项数据质量校验（主键唯一性、空值、日期倒挂、取值越界、枚举域），
  失败即中止流水线

**分析判断力**：每个结论都做了反向验证——
比如确认 Furniture 亏损不是"某类客户爱买便宜家具"造成的
（三类客户在 Furniture 上的利润率全部低于 3.5%），
以及明确写出这份分析的 4 条局限（见 findings.md 第四节）。

## 快速开始

```bash
# 1. 安装依赖（建议在虚拟环境里）
pip install -r requirements.txt

# 2. 一键跑完整条流水线（数据已在仓库里，无需另外下载）
python run_all.py
```

跑完会在 `reports/` 下生成：

```
reports/
├── tables/    6 个分析查询的结果 CSV
└── figures/   3 张图表 PNG
```

也可以分步执行：

```bash
python -m src.load       # 装载 raw + staging 两层
python -m src.quality    # 跑 7 项数据质量校验
python -m src.analyze    # 执行 sql/ 目录下的全部查询，导出 CSV
python -m src.charts     # 生成图表
```

## 项目结构

```
superstore-analysis/
├── run_all.py                 # 一键跑通全流程
├── requirements.txt
├── data/
│   └── raw/superstore.csv     # 原始数据（已含 schema 校验，可复现）
├── sql/                       # 6 个分析查询，每条对应一个业务问题
│   ├── 01_overview.sql                整体经营 KPI
│   ├── 02_discount_impact.sql         ★ 折扣档位 vs 利润率（核心归因）
│   ├── 03_profit_by_subcategory.sql   子品类利润排名 + 累计帕累托
│   ├── 04_yearly_trend.sql            年度趋势 + 同比（LAG 窗口函数）
│   ├── 05_region_performance.sql      区域表现 + 加权折扣率
│   └── 06_segment_by_category.sql     客户细分 × 品类透视
├── src/
│   ├── db.py                  # 路径常量与数据库连接
│   ├── fetch_data.py          # 数据下载 + schema 校验（记录了数据源陷阱）
│   ├── load.py                # raw → staging 两层装载
│   ├── quality.py             # 7 项数据质量校验
│   ├── analyze.py             # 执行 SQL 并导出结果
│   └── charts.py              # 生成 3 张图
└── reports/
    ├── findings.md            # ★ 完整分析备忘录（含建议与局限）
    ├── tables/                # 查询结果 CSV
    └── figures/               # 图表 PNG
```

## 数据说明

- 来源：Tableau 官方示例 Superstore 数据集（GitHub 公开镜像）
- 时间跨度：2015-01-03 ~ 2018-12-30
- 粒度：订单行（一行 = 一张订单里的一种商品），9,994 行 / 5,009 笔订单
- 关键字段：`Sales` 销售额、`Profit` 利润、`Discount` 折扣（0–0.8 小数）

> 已知数据源问题：GitHub 上的常见镜像把 Tableau 工作簿的
> Orders / People / Returns 三张表拼在了同一个 CSV 里。
> 本项目在 `src/fetch_data.py` 中按字段数校验剔除，只保留订单表。
