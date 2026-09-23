# -*- coding: utf-8 -*-
"""Step 4: 把点时 ROE 事件对齐到行情面板。

财报连接使用行情表的 ``financial_code6`` 而不是 ``code6``：北交所 2025 年
10 月换代码后，行情是新的 920xxx 代码、财报仍挂在旧的 43/83/87 代码下，
只有通过映射列才能连上。这与 EP 的口径一致。
"""
import sys
from pathlib import Path

PROJECT_ROOT = next(
    (p for p in Path(__file__).resolve().parents if (p / "factor_paths.py").exists()),
    None,
)
if PROJECT_ROOT is None:
    raise RuntimeError(r"找不到项目根目录，请确认 D:\因子计算\factor_paths.py 存在")
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from factor_paths import ROE_DIR, data_dirs  # noqa: E402
from pure_factor_streaming import stream_align_market_events  # noqa: E402

DATA, _ = data_dirs(ROE_DIR)
EVENT_COLUMNS = [
    "END_DATE", "PRIOR_END_DATE", "TTM_ni", "equity_current", "equity_prior",
    "average_equity", "negative_equity", "ROE",
]


def make_batch(merged: pd.DataFrame):
    signal = pd.to_numeric(merged["ROE"], errors="coerce")
    signal.loc[merged["suspended"].eq(1)] = np.nan
    raw = pd.DataFrame({"date": merged["date"], "stock_code": merged["code6"], "signal": signal})
    raw = raw.set_index(["date", "stock_code"])
    mask = merged[["date", "code6", "suspended", "suspended_unknown", "is_cixin", "VERSION_TIME", *EVENT_COLUMNS]].rename(columns={"code6": "stock_code"})
    mask = mask.set_index(["date", "stock_code"])
    mask["st_filter_applied"] = 0
    mask["st_filter_note"] = "historical ST/PT data unavailable"
    valid = raw["signal"].notna()
    values = raw.loc[valid, "signal"]
    return raw, mask, {
        "valid_roe": int(valid.sum()),
        "negative_roe": int(values.lt(0).sum()),
        "zero_roe": int(values.eq(0).sum()),
    }


totals = stream_align_market_events(
    DATA / "_mkt_clean.parquet",
    DATA / "roe_events.parquet",
    EVENT_COLUMNS,
    make_batch,
    DATA / "roe_raw.parquet",
    DATA / "roe_mask.parquet",
    market_event_code_column="financial_code6",
)
print(f"market rows: {totals['market_rows']:,}")
print(f"lookahead violations: {totals['lookahead']}")
print(f"valid raw ROE rows: {totals.get('valid_roe', 0):,} ({totals.get('valid_roe', 0) / totals['market_rows'] * 100:.2f}%)")
print(f"negative raw ROE rows: {totals.get('negative_roe', 0):,}")
print(f"zero raw ROE rows: {totals.get('zero_roe', 0):,}")
print(f"saved: {DATA / 'roe_raw.parquet'}")
print(f"saved: {DATA / 'roe_mask.parquet'}")
