# -*- coding: utf-8 -*-
"""Step 2: 计算逐股票的原始规模因子。"""
import sys
from pathlib import Path

PROJECT_ROOT = next(
    (p for p in Path(__file__).resolve().parents if (p / "factor_paths.py").exists()),
    None,
)
if PROJECT_ROOT is None:
    raise RuntimeError(r"找不到项目根目录，请确认 D:\因子计算\factor_paths.py 存在")
sys.path.insert(0, str(PROJECT_ROOT))

from factor_paths import SIZE_DIR, data_dirs  # noqa: E402
from pure_factor_streaming import stream_size_raw  # noqa: E402

DATA, _ = data_dirs(SIZE_DIR)

totals = stream_size_raw(DATA / "_mkt_clean.parquet", DATA / "size_raw.parquet", DATA / "size_mask.parquet")
print(f"market rows: {totals['market_rows']:,}")
print(f"positive market-cap rows: {totals['positive_market_cap']:,}")
print(f"valid raw size rows: {totals['valid_raw']:,} ({totals['valid_raw'] / totals['market_rows'] * 100:.2f}%)")
print(f"saved: {DATA / 'size_raw.parquet'}")
print(f"saved: {DATA / 'size_mask.parquet'}")
