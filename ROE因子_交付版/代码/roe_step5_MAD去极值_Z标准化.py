# -*- coding: utf-8 -*-
"""Step 5: 每日横截面 MAD 去极值与 Z 标准化。"""
import sys
from pathlib import Path

PROJECT_ROOT = next(
    (p for p in Path(__file__).resolve().parents if (p / "factor_paths.py").exists()),
    None,
)
if PROJECT_ROOT is None:
    raise RuntimeError(r"找不到项目根目录，请确认 D:\因子计算\factor_paths.py 存在")
sys.path.insert(0, str(PROJECT_ROOT))

from factor_paths import ROE_DIR, data_dirs  # noqa: E402
from pure_factor_streaming import standardize_factor  # noqa: E402

DATA, FINAL = data_dirs(ROE_DIR)

totals = standardize_factor(
    DATA / "roe_raw.parquet",
    DATA / "roe_mad.parquet",
    DATA / "roe.parquet",
    DATA / "roe_processing_stats.parquet",
    FINAL / "roe.parquet",
)
print(f"raw valid rows: {totals['raw_valid']:,}")
print(f"MAD clipped rows: {totals['mad_clipped']:,}")
print(f"constant cross-sections: {totals['constant_cross_sections']:,}")
print(f"final valid Z rows: {totals['final_valid_z']:,}")
print(f"saved: {DATA / 'roe_mad.parquet'}")
print(f"saved: {DATA / 'roe.parquet'}")
print(f"saved: {FINAL / 'roe.parquet'}")
