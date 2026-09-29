# Superstore 经营诊断：销售额涨了 51%，利润率为什么原地踏步？

用 SQL 对 4 年、5,009 笔零售订单做了一次利润归因分析，
找出了"增长质量差"的根因，并给出可执行的建议。

> **数据**：Tableau Sample Superstore，2015–2018，9,994 行（公开示例数据，**不属于本项目**）
> **技术栈**：DuckDB（SQL 分析）· pandas · matplotlib · Python
> **完整结论**：见 [reports/findings.md](reports/findings.md)
> **许可证**：[MIT](LICENSE)（仅覆盖本项目原创的代码与文档，**不含数据集**）
> **数据出处与授权状态**：[NOTICE.md](NOTICE.md) ← 关于数据的授权情况，请看这里

---

## 核心结论（30 秒版）

**折扣一过 20%，利润断崖转负——分水岭位于 20%–30% 之间。**

| 折扣档位（真实取值） | 利润率 | 亏损订单占比 |
|---|---:|---:|
| 无折扣 | +29.51% | 0% |
| 15% / 20% | +11.58% | 14.0% |
| 30% | **−10.05%** | 91.6% |
| 45% 以上 | **−77.40%** | **100%** |

折扣 > 20% 的订单只占 13.9%，却造成 −13.5 万美元的利润损失——
**相当于全年利润的 47%**。同时销售额四年涨了 51%，利润率却始终停在 10%–13%。

## 三张图看懂全部分析

### 1. 折扣一过 20%，利润断崖转负

![折扣 vs 利润率](reports/figures/01_discount_vs_margin.png)

### 2. 三个产品线在出血，Tables 是最大出血点

![子品类利润](reports/figures/02_subcategory_profit.png)

### 3. 销售额涨了 51%，利润率原地踏步

![增长质量](reports/figures/03_growth_quality.png)

## 这个项目展示了什么

**SQL 能力**（全部查询在 [`sql/`](sql/) 目录，每条带业务问题注释）：

- 分档聚合 + 条件聚合（`CASE WHEN`、`COUNT FILTER`）做折扣归因
- **条件聚合做区间拆分**：`SUM(x) FILTER (WHERE 条件)` 让一次扫描同时算出
  "折扣卡住前 / 后"两段利润（州级亏损拆解）
- **参数化扫描**：`VALUES` 构造参数表 + `CROSS JOIN`，一个查询算完全部阈值
  （阈值敏感性检验）
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
- 8 项数据质量校验（主键唯一性、空值、日期倒挂、取值越界、枚举域、订单粒度一致性），
  失败即中止流水线

**分析判断力**：每个结论都做了反向验证——
比如确认 Furniture 亏损不是"某类客户爱买便宜家具"造成的
（三类客户在 Furniture 上的利润率全部低于 3.5%）；
对最关键的"20% 阈值"做了敏感性检验，发现数据里 20%–30% 之间**没有任何订单**
（折扣只有 12 个离散档位），于是把结论从"20% 是分界线"修正为
"分水岭位于 20%–30% 之间，本数据无法进一步定位"；
还做了州一级的下沉，验证"卡折扣"这条建议在各州是否真的可落地。
并明确写出这份分析的 5 条局限（见 findings.md 第四节）。

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
├── tables/    8 个分析查询的结果 CSV
└── figures/   3 张图表 PNG
```

也可以分步执行：

```bash
python -m src.load       # 装载 raw + staging 两层
python -m src.quality    # 跑 8 项数据质量校验
python -m src.analyze    # 执行 sql/ 目录下的全部查询，导出 CSV
python -m src.charts     # 生成图表
```

## 项目结构

```
superstore-analysis/
├── run_all.py                 # 一键跑通全流程
├── requirements.txt
├── LICENSE                    # MIT（仅覆盖本项目原创的代码与文档）
├── NOTICE.md                  # ★ 数据出处、授权状态、依赖许可证、原创性声明
├── data/
│   └── raw/superstore.csv     # 原始数据（已含 schema 校验）——版权属 Tableau，见 NOTICE.md
├── sql/                       # 8 个分析查询，每条对应一个业务问题
│   ├── 01_overview.sql                整体经营 KPI
│   ├── 02_discount_impact.sql         ★ 折扣档位 vs 利润率（核心归因）
│   ├── 03_profit_by_subcategory.sql   子品类利润排名 + 累计帕累托
│   ├── 04_yearly_trend.sql            年度趋势 + 同比（LAG 窗口函数）
│   ├── 05_region_performance.sql      区域表现 + 加权折扣率
│   ├── 06_segment_by_category.sql     客户细分 × 品类透视
│   ├── 07_state_loss_split.sql        州级亏损拆解（条件聚合做区间拆分）
│   └── 08_threshold_sensitivity.sql   阈值敏感性检验（参数化扫描）
├── src/                       # 源码（每个文件头部带 SPDX 许可证标识）
│   ├── db.py                  # 路径常量与数据库连接
│   ├── fetch_data.py          # 数据下载 + schema 校验（记录了数据源陷阱）
│   ├── load.py                # raw → staging 两层装载
│   ├── quality.py             # 8 项数据质量校验
│   ├── analyze.py             # 执行 SQL 并导出结果
│   └── charts.py              # 生成 3 张图
└── reports/
    ├── findings.md            # ★ 完整分析备忘录（含建议与局限）
    ├── tables/                # 查询结果 CSV
    └── figures/               # 图表 PNG（全部由 src/charts.py 生成）+ 来源说明 README
```

## 数据说明

| 项 | 内容 |
|---|---|
| 数据集 | Sample Superstore（Tableau 官方示例数据） |
| 权利人 | **Tableau Software** —— 数据**不属于本项目**，不由本仓库的 MIT 许可证覆盖 |
| 官方发布页 | Tableau Public → Learn → Sample Data |
| 时间跨度 | 2015-01-03 ~ 2018-12-30 |
| 粒度 | 订单行（一行 = 一张订单里的一种商品），9,994 行 / 5,009 笔订单 |
| 关键字段 | `Sales` 销售额、`Profit` 利润、`Discount` 折扣（0–0.8 小数） |

> **已知数据源问题**：GitHub 上的常见镜像把 Tableau 工作簿的
> Orders / People / Returns 三张表拼在了同一个 CSV 里。
> 本项目在 `src/fetch_data.py` 中按字段数校验剔除，只保留订单表。

---

## 数据来源、授权与版权声明

> 完整声明见 [**NOTICE.md**](NOTICE.md)。这里给出要点。

### 1. 数据：不属于本项目

Sample Superstore 由 **Tableau Software** 在官方 Sample Data 页面公开发布，供学习与教学使用；
它描述的是一个**虚构公司**。本项目通过 GitHub 公开镜像获取，**仅用于非商业的学习与作品集演示**。

关于授权状态，需要如实说明——不做对己有利的推定：

- Tableau 官方发布该数据集时**未附 License 条款**；
- 本项目实际获取所用的那个 GitHub 镜像**也未声明 License**；
- 其他下游平台（如 Kaggle）上的镜像有的标注 `CC0: Public Domain`，有的标注"仅供教育用途"，
  但这些标注由**再分发者自行附加**，不能视为原始权利人的授权声明；
- 因此，**本项目不主张对该数据的任何权利，也不对其再分发的合法性作保证。**

**合规承诺。** 若权利人认为本仓库保留该数据副本的方式不妥，可随时提出，
本项目将**立即移除** `data/raw/superstore.csv` 及其派生结果文件。
该文件可通过 `python -m src.fetch_data` 重新获取，**移除不影响代码本身的价值**。
（说明：该镜像偶尔会掐断连接，脚本带 3 次重试；若仍失败，它会直接给出
Tableau 官方页面的手动获取步骤，并保证**不会损坏仓库里已有的数据副本**。）

### 2. 分析定位：「折扣侵蚀利润」不是本项目的新发现

「折扣侵蚀利润」是这个数据集**最常被讨论的标准教学课题**，Tableau 官方教程与大量公开文章
都做过类似分析。本项目**不是原创研究，也没有提出新发现**。把这句话写在这里是为了避免任何误解：

- 本项目的价值在于**完整走通一条分析链路**——
  数据获取与校验 → 分层建模 → SQL 归因 → 可视化 → 结论与局限，
  并在这个过程中处理了两个真实的数据源问题（多表拼接污染、美式日期格式）；
- 在此基础上补充了两个**该课题常见的分析里不常做**的交叉验证：
  区域加权折扣率与利润率的对应关系、客户细分 × 品类的交叉
  （用于排除「某类客户爱买便宜家具」这一替代假设）；
- 本项目**未引用、未复制、未改写**任何具体他人的代码、图表或结论表述；
  分析视角属于"被广泛讨论的通用分析思路"，而非某个特定他人的作品；
- 结论数字均可通过 `python run_all.py` 复现，便于任何读者独立核验。

### 3. 图表与素材：全部自己生成，无任何第三方内容

- `reports/figures/` 下的 **3 张图全部由本项目代码 [`src/charts.py`](src/charts.py)
  用 matplotlib 运行时绘制**，数据来自本项目自己的查询结果；
  另见 [`reports/figures/README.md`](reports/figures/README.md)。
- 本仓库**不包含**任何第三方的图片、截图、扫描件、插画、图标或 Logo，
  也**未使用**任何第三方徽章（badge）、追踪像素或外链图片。
- 图表渲染使用**本机系统字体**（优先 Microsoft YaHei / SimHei，缺失时回退 DejaVu Sans）；
  **仓库不包含、也不再分发任何字体文件**。
- 文档中提及 Tableau、DuckDB、pandas、matplotlib、GitHub、Kaggle 等名称，
  仅用于**事实性标注出处与技术栈**，**不代表任何关联、赞助或背书**。
  本项目与 Tableau / Salesforce 无隶属关系。

### 4. 代码原创性

- `src/`、`sql/`、README 与分析备忘录均为本项目**原创编写**，
  未从他人仓库、技术博客、Notebook 或问答社区复制代码片段；
  外部参考仅限于官方文档（DuckDB / pandas / matplotlib）与标准 SQL 语法。
- 本仓库**不包含任何 Jupyter Notebook**（`.ipynb`），因此不存在 Notebook 代码片段的引用问题；
  若将来新增，其中的代码同样必须为原创，任何外部引用须在 NOTICE.md 中登记出处与许可证。
- 每个源文件头部均带 `SPDX-License-Identifier: MIT` 标识，明确其许可证归属。

### 5. 第三方依赖的许可证

| 依赖 | 本项目使用版本 | 许可证 | 版权归属 |
|---|---|---|---|
| duckdb | 1.5.6 | **MIT** | Stichting DuckDB Foundation |
| pandas | 3.0.6 | **BSD 3-Clause** | AQR Capital Management / Lambda Foundry / PyData Dev Team；Open source contributors |
| matplotlib | 3.11.2 | **Matplotlib License**（PSF 派生的 BSD 兼容条款） | Matplotlib Development Team |
| numpy（间接依赖） | 2.4.6 | BSD-3-Clause 等 | NumPy Developers |

这些库通过 `pip` 安装、**不由本仓库分发源代码**，均为宽松许可证；
若你要再分发本项目，请一并遵守上述许可证。

### 6. 用途

本仓库为**个人学习与求职作品集**项目，**非商业用途**。上述声明旨在如实披露来源与授权状态，
**不构成法律意见**。如认为某处使用不妥，请通过 Issues 联系，本项目将核实后立即更正或移除。


