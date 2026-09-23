# -*- coding: utf-8 -*-
"""规模因子交付验证：索引格式、MAD 处理记录数、结果一致性。"""
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

from factor_paths import SIZE_DIR, data_dirs  # noqa: E402

ROOT = SIZE_DIR
DATA, _ = data_dirs(ROOT)
raw = pd.read_parquet(DATA / "size_raw.parquet")
mad = pd.read_parquet(DATA / "size_mad.parquet")
z = pd.read_parquet(DATA / "size.parquet")
final = pd.read_parquet(ROOT / "因子结果" / "size.parquet")
stats = pd.read_parquet(DATA / "size_processing_stats.parquet")
mask = pd.read_parquet(DATA / "size_mask.parquet")
mkt = pd.read_parquet(DATA / "_mkt_clean.parquet")

for name, frame in [("raw", raw), ("mad", mad), ("z", z), ("final", final)]:
    assert frame.index.names == ["date", "stock_code"], (name, frame.index.names)
    assert list(frame.columns) == ["signal"], (name, frame.columns)
    assert not frame.index.duplicated().any(), f"{name}: duplicate index"
    assert np.isfinite(frame["signal"].dropna()).all(), f"{name}: non-finite"

assert len(raw) == len(mkt) == len(mask) == len(mad) == len(z) == len(final)
assert raw.index.equals(mad.index) and raw.index.equals(z.index)
assert raw.index.equals(final.index)
assert z.equals(final)

raw_valid = raw["signal"].notna()
mad_valid = mad["signal"].notna()
z_valid = z["signal"].notna()
assert raw_valid.sum() == mad_valid.sum()
assert z_valid.sum() <= raw_valid.sum()

joined = raw.rename(columns={"signal": "raw"}).join(
    mad.rename(columns={"signal": "mad"})
).join(z.rename(columns={"signal": "z"}))
changed = joined["raw"].notna() & joined["raw"].ne(joined["mad"])
assert int(changed.sum()) == int(stats["n_clipped"].sum())

sample = joined.loc[joined["raw"].notna(), ["raw", "mad", "z"]].reset_index()
limits = stats.reset_index()[["date", "lower", "upper"]]
sample = sample.merge(limits, on="date", how="left", validate="many_to_one")
bounded = sample["lower"].ne(-np.inf) & sample["upper"].ne(np.inf)
assert (sample.loc[bounded, "mad"] >= sample.loc[bounded, "lower"]).all()
assert (sample.loc[bounded, "mad"] <= sample.loc[bounded, "upper"]).all()

daily = z[z["signal"].notna()].reset_index().groupby("date")["signal"]
daily_mean = daily.mean()
daily_std = daily.std(ddof=0)
nonconstant = daily_std.gt(0)
if nonconstant.any():
    assert np.nanmax(np.abs(daily_mean[nonconstant])) < 1e-10
    assert np.nanmax(np.abs(daily_std[nonconstant] - 1)) < 1e-10

assert mask.index.equals(raw.index)
positive = mask["me_total"].gt(0)
assert raw.loc[~positive, "signal"].isna().all()
expected = np.log(mask.loc[positive, "me_total"])
raw_positive = raw.loc[positive, "signal"]
assert np.nanmax(np.abs(expected.to_numpy() - raw_positive.to_numpy())) < 1e-12

print("formats: PASS")
print("rows:", len(z))
print("raw_valid:", int(raw_valid.sum()))
print("mad_clipped:", int(changed.sum()))
print("z_valid:", int(z_valid.sum()))
print(
    "daily_z_mean_max_abs:",
    float(np.nanmax(np.abs(daily_mean[nonconstant]))) if nonconstant.any() else 0.0,
)
print(
    "daily_z_std_max_abs_error:",
    float(np.nanmax(np.abs(daily_std[nonconstant] - 1))) if nonconstant.any() else 0.0,
)
print("validation: PASS")
