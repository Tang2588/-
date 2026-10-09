# -*- coding: utf-8 -*-
"""Step 4: 点时对齐归母权益并计算原始 PB。

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

from factor_paths import PB_DIR, data_dirs  # noqa: E402
from pure_factor_streaming import stream_align_market_events  # noqa: E402

DATA, _ = data_dirs(PB_DIR)


def make_batch(merged: pd.DataFrame):
    merged["me_total"] = pd.to_numeric(merged["me_total"], errors="coerce")
    merged["book_equity_parent"] = pd.to_numeric(merged["book_equity_parent"], errors="coerce")
    pb = pd.Series(np.nan, index=merged.index, dtype="float64")
    valid = merged["me_total"].gt(0) & merged["book_equity_parent"].notna() & merged["book_equity_parent"].ne(0)
    pb.loc[valid] = merged.loc[valid, "me_total"] / merged.loc[valid, "book_equity_parent"]
    pb.loc[merged["suspended"].eq(1)] = np.nan
    merged["negative_book_equity"] = merged["book_equity_parent"].lt(0).astype("int8")

    raw = pd.DataFrame({"date": merged["date"], "stock_code": merged["code6"], "signal": pb})
    raw = raw.set_index(["date", "stock_code"])
    mask = merged[["date", "code6", "suspended", "suspended_unknown", "is_cixin", "negative_book_equity"]].rename(columns={"code6": "stock_code"})
    mask = mask.set_index(["date", "stock_code"])
    mask["st_filter_applied"] = 0
    mask["st_filter_note"] = "historical ST/PT data unavailable"
    valid_pb = raw["signal"].notna()
    values = raw.loc[valid_pb, "signal"]
    return raw, mask, {
        "valid_pb": int(valid_pb.sum()),
        "negative_pb": int(values.lt(0).sum()),
        "zero_pb": int(values.eq(0).sum()),
    }


totals = stream_align_market_events(
    DATA / "_mkt_clean.parquet",
    DATA / "book_equity_snapshots.parquet",
    ["book_equity_parent"],
    make_batch,
    DATA / "pb_raw.parquet",
    DATA / "pb_mask.parquet",
    market_event_code_column="financial_code6",
)
print(f"market rows: {totals['market_rows']:,}")
print(f"lookahead violations: {totals['lookahead']}")
print(f"valid PB rows: {totals.get('valid_pb', 0):,} ({totals.get('valid_pb', 0) / totals['market_rows'] * 100:.2f}%)")
print(f"negative PB rows: {totals.get('negative_pb', 0):,}")
print(f"zero PB rows: {totals.get('zero_pb', 0):,}")
print(f"saved: {DATA / 'pb_raw.parquet'}")
print(f"saved: {DATA / 'pb_mask.parquet'}")
