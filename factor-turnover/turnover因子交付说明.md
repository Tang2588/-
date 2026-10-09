# 换手率因子计算交付说明

## 1. 交付内容

仓库目录：`D:\因子计算\factor-turnover`

代码：

```text
turnover_step1_读取已清洗行情.py
turnover_step2_计算换手率并标准化.py
```

正式交付物：

```text
D:\因子计算\factor-turnover\因子结果\turnover.parquet
```

输出格式（与 EP / PB / ROE / Size 完全一致）：

```text
index   = ['date', 'stock_code']
columns = ['signal']
```

中间结果文件（在 `中间结果\`）：

```text
_mkt_clean.parquet                 从 factor-ep 复制的行情面板
turnover_raw.parquet               原始换手率因子（未去极值、未标准化）
turnover_mad.parquet               MAD 去极值后的因子
turnover.parquet                   Z 标准化后的因子（与正式交付物同源）
turnover_processing_stats.parquet  逐日处理统计（中位数 / MAD / 上下界 / 截断数）
```

## 2. 数据来源

- 股票池、停牌标记、统一证券身份：复用 EP 已清洗好的行情面板
  `D:\因子计算\factor-ep\中间结果\_mkt_clean.parquet`
- 换手率本身：直接从原始行情表 `chn_equ_mkt_quotation.parquet` 的现成字段读取，
  **不用成交金额重新推算**。

## 3. 字段口径

| 字段 | 含义 |
| --- | --- |
| `turnover` | 成交量 / 流通股本，行情表内已算好 |
| `turnover_free` | 成交量 / 自由流通股本 |

已逐行用 `volume / share_float` 与 `turnover` 比对，两者完全一致，
因此直接使用现成字段。默认 `TURNOVER_COLUMN = "turnover"`，
若要用自由流通口径，改成 `"turnover_free"` 即可。

## 4. 原始因子定义

```text
T 日换手率因子 = 过去 20 个交易日（含 T 日）的平均换手率
```

实现要点：

- 按统一证券身份 `security_id` 分组做滚动均值，而不是按 6 位代码，
  避免北交所 2025 年换代码时把同一只股票的序列打断。
- 停牌日（`suspended == 1`）：因子置为缺失。
- 上市不足 20 个交易日（有效值不满 20 个）：返回缺失。
- 负值（`-9999` 缺失哨兵）：置为缺失，详见第 10 节。

判定换手率口径时只使用 T 日及以前的信息，不涉及未来数据。

## 5. 时间口径

T 日收盘后即可算出因子值，T+1 日建仓使用，与 EP 口径一致：

```text
signal_cutoff = T 日 + 1 日 - 1 纳秒
```

## 6. MAD 去极值与 Z 标准化

与 EP / PB / ROE / Size 共用同一个函数（`pure_factor_streaming.standardize_factor`），
逐日横截面处理：

```text
median = 当日原始因子的中位数
MAD    = median(|raw - median|)
scale  = 1.4826 * MAD
下界   = median - 3 * scale
上界   = median + 3 * scale
```

先把超出上下界的原始值截断，再计算：

```text
signal = (MAD 截断后的 raw - 当日均值) / 当日标准差
```

**写入 `turnover_raw.parquet` 之前必须按 `(date, stock_code)` 排序。**
标准化函数是流式分块处理的，靠「最后一行的日期」判断哪一天已经读全；
顺序不对会把同一天的横截面拆成多段，结果是错的，而且会慢到十几分钟。
所以 `build_raw()` 最后一行是 `return raw.sort_index()`。

## 7. 运行顺序

```text
python turnover_step1_读取已清洗行情.py
python turnover_step2_计算换手率并标准化.py
```

step2 可以直接跑（内部会读 step1 的产物），前提是 EP 的
`_mkt_clean.parquet` 已经生成。运行时会打印面板行数、原始有效/缺失行数、
原始取值范围、覆盖股票数、MAD 截断行数等，方便直接核对。

## 8. 本次运行结果

```text
面板行数      : 7,081,800
原始有效行    : 6,952,036
原始缺失行    : 129,764
原始取值范围  : 0.000000 ~ 0.620090
覆盖股票数    : 5,927
MAD 截断行    : 707,149
常数截面天数  : 0
最终有效 Z 行 : 6,952,036
耗时          : 28.2 秒
```

Z 标准化后取值范围约 `-1.44 ~ 2.45`，即上下界 3 倍 MAD 截断后的结果。

## 9. 验证方法

1. 输出行数是否等于行情面板行数（7,081,800）。
2. `(date, stock_code)` 是否唯一、是否与 EP 的股票池一致。
3. 原始换手率是否全部非负。
4. 原始缺失行数是否等于「停牌行 + 上市不足 20 日行 + 负值哨兵污染传播行」。
5. 逐日 Z 值均值是否接近 0、标准差是否接近 1。

## 10. 已知数据问题

行情表有 17 行（全部在 2025-06-27）`turnover`、`me_float`、`share_float`
取 `-9999`（缺失哨兵）。单个 -9999 会被 20 日均值放大成约 -500 的假极值，
污染整段序列。脚本已把负的换手率统一置为缺失，20 日窗口内包含该日的观测
一并变成缺失（17 × 20 = 340 行），所以有效行数比修复前少 340。

全表扫描确认只有这三个字段存在该问题，`volume`、`amount`、`me_total`、
`share_total`、`close` 均无异常。
