# 四因子计算项目

EP、PB、ROE、Size 四个股票横截面因子的计算代码与交付文档。数据区间
2020-01-02 至 2025-12-31，统一采用「T 日因子用于 T+1 日交易」的点时间口径。

## 一、目录结构

```text
因子计算/
├── factor_paths.py              共用路径常量 + 行情面板加载与口径校验
├── pure_factor_streaming.py     共用流式计算助手（分块读写、点时对齐、MAD+Z）
│
├── 市盈率/EP因子_交付版/         EP（独立仓库，见下方说明）
├── 市净率/PB因子_交付版/         PB
├── ROE因子_交付版/               ROE
├── 规模因子_交付版/              Size
│
└── 财务报表披露与更新规律统计.md  财报披露时间规律的研究记录
```

`市盈率/EP因子_交付版` 是一个 **git submodule**，指向
<https://github.com/Tang2588/factor-test>。克隆本仓库时请使用：

```bash
git clone --recursive https://github.com/Tang2588/-.git

# 已克隆但忘记加 --recursive
git submodule update --init --recursive
```

## 二、四个因子

| 因子 | 公式 | 需要的数据 | 说明 |
|---|---|---|---|
| **EP** | TTM 归母净利润 ÷ 总市值 | 利润表 + 行情 | 主因子，方向为正 |
| **PB** | 总市值 ÷ 归母股东权益 | 资产负债表 + 行情 | 负净资产保留为负 PB |
| **ROE** | TTM 归母净利润 ÷ 平均归母权益 | 利润表 + 资产负债表 + 行情 | 平均权益取本期与去年同期均值 |
| **Size** | ln(总市值) | 仅行情 | 越大表示市值越大 |

四个因子的正式结果都是同一格式：

```text
index   = ['date', 'stock_code']
columns = ['signal']
```

`signal` 为经过每日横截面 MAD 去极值与 Z 标准化后的因子值。

## 三、统一口径

四个因子共用同一套处理规则，规则定义在 `factor_paths.py` 与
`pure_factor_streaming.py` 中，不在各脚本里重复实现。

| 项目 | 口径 |
|---|---|
| 时间 | T 日收盘后使用截至 T 日可获得的数据；T 日因子用于 T+1 日交易 |
| 财报可用时间 | `VERSION_TIME = max(ACT_PUBTIME, UPDATE_TIME)`，晚于 T 日则不可用 |
| 报表口径 | 合并报表（`MERGED_FLAG=1`），保留累计报告期 |
| 股票池 | 沪深 A 股 + 北交所，排除 89 只沪深 B 股（沪市 900xxx 50 只、深市 200/201xxx 39 只） |
| ST / 次新股 | 不筛除；历史 ST 标记缺失，次新股仅在掩码中记录 |
| 停牌 | T 日停牌则因子置为缺失 |
| 去极值与标准化 | 每日横截面：`median ± 3 × 1.4826 × MAD` 截断后做 Z 标准化 |

### 股票池的单一来源

行情清洗（代码规范化、B 股排除、北交所新旧代码映射）只在 EP 的
`step1_样本筛选.py` 中做一次。其余三个因子通过
`factor_paths.load_market_panel()` 复制使用，该函数会强制校验：

1. 行情面板不含 B 股，否则报错；
2. 行情面板含 `financial_code6` 字段，否则报错。

这样四个因子不可能再用到不同版本的行情表。

## 四、2026-09-22 的修复

### 问题：三个因子用的是旧版行情，缺少北交所代码映射

北交所在 2025 年 10 月把 242 只股票的六位代码从 `43/83/87xxxx` 改为 `920xxx`。
换代码之后，行情表用新代码，但财报仍然挂在旧代码下，必须通过映射列才能连接。

EP 在 2026-09-14 的改造中给行情表加了 `financial_code6`（财报连接代码）来解决
这个问题；PB / ROE / Size 当时用的还是 9 月 1 日的行情表，没有这个字段。

实测北交所股票的有效因子覆盖率。切换前指 2025-10-09 之前，切换后指此后：

| 因子 | 切换前 | 切换后（修复前） | 切换后（修复后） |
|---|---:|---:|---:|
| EP | 88.66% | 96.18% | 96.18%（未受影响） |
| PB | 92.07% | 80.63% | **99.65%** |
| **ROE** | 68.43% | **3.49%** | **22.44%** |
| Size | 99.69% | 99.73% | 99.73%（不连接财报） |

修复后四个因子的股票池完全一致：均为 7,081,800 行、5,927 个代码、0 只 B 股。

ROE 修复后仍低于其它因子，原因是它需要「本期权益 + 去年同期权益」两个值才能计算，
而北交所的权益数据本身稀疏：切换后的 475 条北交所事件中，有 404 条因缺少
`average_equity` 而无法计算，并非代码映射问题。

原因在代码层面很直接：ROE 的事件表里有 10,163 条挂在旧代码、仅 559 条挂新代码，
而行情表切换后有 288 个 `920xxx` 代码，两边按 `code6` 连接必然对不上。

### 修复内容

| 修复项 | 做法 |
|---|---|
| 财报连接 | PB 与 ROE 的 step4 传入 `market_event_code_column="financial_code6"` |
| 行情面板 | 三个因子的 step1 统一调用 `load_market_panel()`，带 B 股与字段校验 |
| 共享模块 | 顶层 `pure_factor_streaming.py` 升级到 EP 的新版，支持按指定列匹配事件 |
| ROE 数据源 | 行情面板直接从 EP 读取，不再经过 PB 中转，避免多级复制出偏差 |

### 尚未解决：财报代码在切换后也变了

供应商在换代码之后把**新披露的财报也挂到新代码下**。以 2025-09-30 报告期为例：

| 挂在哪 | 条数 |
|---|---:|
| 旧代码 43/83/87xxxx | 8 |
| 新代码 920xxx | 541 |

而 920 代码的公告集中在 2025-10 月，共 1,122 条。

当前的 `financial_code6` 是**单向往回映射**（920 → 旧代码），因此对切换后新披露的
财报无法命中，只能取到旧代码下的历史版本。这会带来两个后果：

1. 北交所股票在切换后可能使用**稍旧一期**的财报；
2. ROE 这类依赖多期数据的因子受影响最大。

彻底解决需要把映射改成**双向按证券身份匹配**（同一证券的新旧代码都能命中同一份
财报历史）。目前 EP 与 PB 的覆盖率仍然很高，说明旧代码路径还能取到可用数据，
属于「可能用到稍旧版本」的风险，不是断崖式缺失，因此本次未处理。

### 可读性改进

原来的脚本用向上搜索 `pure_factor_streaming.py` 来定位项目根目录，写法晦涩，
而且不同深度的脚本会解析到不同文件。现在统一为：

```python
PROJECT_ROOT = next(
    (p for p in Path(__file__).resolve().parents if (p / "factor_paths.py").exists()),
    None,
)
if PROJECT_ROOT is None:
    raise RuntimeError(r"找不到项目根目录，请确认 D:\因子计算\factor_paths.py 存在")
sys.path.insert(0, str(PROJECT_ROOT))
```

同时把散落在各脚本里的硬编码路径集中到 `factor_paths.py`，注释与 docstring
统一为中文。

## 五、运行顺序

各因子脚本都在自己的 `代码/` 目录下，按编号顺序执行。

```powershell
# EP（在 市盈率\EP因子_交付版\代码 下）
python step1_样本筛选.py
python step2_利润表处理.py
python step3_TTM计算.py
python step4_点时间对齐_计算PE.py
python step5_MAD去极值_Z标准化.py
python factor_verify.py

# PB（在 市净率\PB因子_交付版\代码 下）
python pb_step1_读取已清洗行情.py
python pb_step2_资产负债表处理.py
python pb_step3_点时权益对齐.py
python pb_step4_点时间对齐_计算PB.py
python pb_step5_MAD去极值_Z标准化.py
python verify_pb.py

# ROE（在 ROE因子_交付版\代码 下）
python roe_step1_读取已清洗行情.py
python roe_step2_利润表处理.py
python roe_step3_TTM和平均权益.py
python roe_step4_点时间对齐_计算ROE.py
python roe_step5_MAD去极值_Z标准化.py
python verify_roe.py

# Size（在 规模因子_交付版\代码 下）
python size_step1_复用EP行情.py
python size_step2_计算对数市值.py
python size_step3_MAD去极值_Z标准化.py
python verify_size.py
```

顺序约束：EP 的 step1 必须先跑，它产出的行情面板是其余三个因子的输入；
PB 的 step2 与 step3 产出的权益版本被 ROE 的 step3 复用。

## 六、数据说明

以下目录体积大且可由代码重新生成，不纳入版本管理：

```text
**/中间结果/
**/因子结果/
*.parquet
```

基础数据来自 `D:\实习生学习项目\基础数据\`：

| 文件 | 内容 |
|---|---|
| `chn_equ_mkt_quotation.parquet` | 行情 |
| `vw_fdmt_is_new.parquet` | 利润表 |
| `vw_fdmt_bs_new.parquet` | 资产负债表 |

路径常量集中在 `factor_paths.py`，换机器只需改这一个文件。

## 七、运行环境

```text
Python 3.12
pandas / numpy / pyarrow
```

## 八、已知限制

1. 历史 ST/PT 标记缺失，当前不能声称已完成历史 ST/PT 过滤；
2. 官方上市日期缺失，次新股用行情表首次出现日期作为代理；
3. 2020 年初财报覆盖不足，早期因子覆盖率偏低；
4. 只有因子计算，不含实际成交、涨跌停、成交量、滑点和交易成本的模拟；
5. EP 的 `pure_factor_streaming.py` 与本仓库根目录下的是两份副本，逻辑一致但
   需要人工保持同步。EP 保留自己的一份是为了让它作为独立仓库能单独运行。
