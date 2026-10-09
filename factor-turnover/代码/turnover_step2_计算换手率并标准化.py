# -*- coding: utf-8 -*-
"""Step 2: 计算换手率因子，并做 MAD 去极值与 Z 标准化。

因子定义
--------
    换手率因子 = 过去 WINDOW 个交易日的平均换手率

口径说明
--------
- 换手率直接取行情表现成字段：``turnover`` = 成交量 / 流通股本，
  换成 ``turnover_free``（自由流通股本口径）只需改 ``TURNOVER_COLUMN``；
- 按统一证券身份 ``security_id`` 计算滚动均值，北交所换码不打断连续性；
- 停牌日置为缺失；
- 上市不足 WINDOW 个交易日的新股返回缺失；
- 最后逐日横截面 MAD 去极值与 Z 标准化，与其它因子使用同一套实现
  （``pure_factor_streaming.standardize_factor``）。

输出（与其它因子同格式）
------------------------
    因子结果/turnover.parquet    index = [date, stock_code], columns = [signal]

直接运行：``python turnover_step2_计算换手率并标准化.py``（需先跑过 step1）
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = next(
    (p for p in Path(__file__).resolve().parents if (p / "factor_paths.py").exists()),
    None,
)
if PROJECT_ROOT is None:
    raise RuntimeError(r"找不到项目根目录，请确认 D:\因子计算\factor_paths.py 存在")
sys.path.insert(0, str(PROJECT_ROOT))

from factor_paths import MARKET_PANEL, MARKET_SOURCE, TURNOVER_DIR, data_dirs  # noqa: E402
from pure_factor_streaming import standardize_factor  # noqa: E402

WINDOW = 20                      # 滚动窗口（交易日）
TURNOVER_COLUMN = "turnover"     # 或 "turnover_free"

MID, FINAL = data_dirs(TURNOVER_DIR)


def build_raw() -> pd.DataFrame:
    """按股票池对齐行情表中的换手率，算滚动均值，返回原始因子。"""
    panel = pd.read_parquet(
        MARKET_PANEL,
        columns=["date", "code6", "market_code", "security_id", "suspended"],
    )

    market = pd.read_parquet(MARKET_SOURCE, columns=["date", "stock_code", TURNOVER_COLUMN])
    market["market_code"] = market["stock_code"].astype("string").str.strip().str.upper()
    market["raw_turnover"] = pd.to_numeric(market[TURNOVER_COLUMN], errors="coerce")
    # 换手率不可能为负。行情表里有 17 行（2025-06-27）把它写成了缺失哨兵 -9999，
    # 若不剔除会被 20 日滚动均值放大成 -500 量级，因此统一把负值视为缺失。
    market.loc[market["raw_turnover"] < 0, "raw_turnover"] = np.nan
    market = market[["date", "market_code", "raw_turnover"]].drop_duplicates(["date", "market_code"])

    merged = panel.merge(market, on=["date", "market_code"], how="left")
    merged = merged.sort_values(["security_id", "date"], kind="stable")

    signal = (
        merged.groupby("security_id", sort=False)["raw_turnover"]
        .transform(lambda values: values.rolling(WINDOW, min_periods=WINDOW).mean())
        .astype("float64")
    )
    signal.loc[merged["suspended"].eq(1)] = np.nan

    raw = pd.DataFrame(
        {"date": merged["date"], "stock_code": merged["code6"], "signal": signal}
    ).set_index(["date", "stock_code"])
    # standardize_factor 是流式分块读的，靠「最后一行所属日期」判断哪一天已读全，
    # 因此必须按日期排序后再写出。上面为了算滚动均值是按 security_id 排的，
    # 这里要换回 (date, stock_code) 顺序，否则同一天会被拆成多个碎片横截面。
    return raw.sort_index()


def main() -> None:
    if not MARKET_PANEL.exists():
        raise FileNotFoundError(
            "找不到行情面板：{}\n请先跑 factor-ep 的 ep_step1_样本筛选.py，"
            "再跑本因子的 turnover_step1_读取已清洗行情.py。".format(MARKET_PANEL)
        )

    print("计算换手率因子：窗口 {} 个交易日，字段 {}".format(WINDOW, TURNOVER_COLUMN))
    raw = build_raw()
    raw.to_parquet(MID / "turnover_raw.parquet")

    valid = raw["signal"].notna()
    print("  面板行数      : {:,}".format(len(raw)))
    print("  原始有效行    : {:,}".format(int(valid.sum())))
    print("  原始缺失行    : {:,}".format(int((~valid).sum())))
    print("  原始取值范围  : {:.6f} ~ {:.6f}".format(raw["signal"].min(), raw["signal"].max()))
    print("  覆盖股票数    : {:,}".format(raw.index.get_level_values("stock_code").nunique()))

    totals = standardize_factor(
        MID / "turnover_raw.parquet",
        MID / "turnover_mad.parquet",
        MID / "turnover.parquet",
        MID / "turnover_processing_stats.parquet",
        FINAL / "turnover.parquet",
    )
    print("MAD 去极值与 Z 标准化：")
    print("  原始有效行    : {:,}".format(totals["raw_valid"]))
    print("  MAD 截断行    : {:,}".format(totals["mad_clipped"]))
    print("  常数截面天数  : {:,}".format(totals["constant_cross_sections"]))
    print("  最终有效 Z 行 : {:,}".format(totals["final_valid_z"]))
    print("  已保存        : {}".format(FINAL / "turnover.parquet"))


if __name__ == "__main__":
    main()
