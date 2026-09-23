# -*- coding: utf-8 -*-
"""Validate the PB delivery folder."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
data = ROOT / "中间结果"
raw = pd.read_parquet(data / "pb_raw.parquet")
mad = pd.read_parquet(data / "pb_mad.parquet")
final = pd.read_parquet(ROOT / "因子结果" / "pb.parquet")
stats = pd.read_parquet(data / "pb_processing_stats.parquet")
for name, frame in [("raw", raw), ("mad", mad), ("final", final)]:
    assert frame.index.names == ["date", "stock_code"]
    assert list(frame.columns) == ["signal"]
    assert not frame.index.duplicated().any(), f"{name}: duplicate index"
    assert np.isfinite(frame["signal"].dropna()).all(), f"{name}: non-finite"
assert len(raw) == len(mad) == len(final)
assert raw.index.equals(mad.index) and raw.index.equals(final.index)
changed = raw["signal"].notna() & raw["signal"].ne(mad["signal"])
assert int(changed.sum()) == int(stats["n_clipped"].sum())
print(f"rows: {len(final):,}")
print(f"raw_valid: {int(raw['signal'].notna().sum()):,}")
print(f"mad_clipped: {int(changed.sum()):,}")
print(f"final_valid: {int(final['signal'].notna().sum()):,}")
print("validation: PASS")
