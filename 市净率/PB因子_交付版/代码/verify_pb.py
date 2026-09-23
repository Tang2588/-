# -*- coding: utf-8 -*-
"""PB 交付验证：索引格式、MAD 处理记录数、原始与最终结果一致性。"""
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

from factor_paths import PB_DIR  # noqa: E402

ROOT = PB_DIR
raw_path = next(ROOT.rglob("pb_raw.parquet"))
final_path = next(ROOT.rglob("pb.parquet"))
data = raw_path.parent
raw = pd.read_parquet(raw_path)
mad = pd.read_parquet(data / "pb_mad.parquet")
final = pd.read_parquet(final_path)
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
