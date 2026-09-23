# -*- coding: utf-8 -*-
"""Step 2: 复用 EP 已经清洗好的利润表版本与 TTM 结果。

注意复用 ``reports.parquet`` / ``reports_ttm.parquet`` 中间结果，而不是
``ep.parquet`` —— 后者已经是标准化后的 EP 信号，不能再当作利润数据使用。
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

import pandas as pd  # noqa: E402

from factor_paths import EP_DATA, ROE_DIR, data_dirs  # noqa: E402

OUT, _ = data_dirs(ROE_DIR)

reports = pd.read_parquet(EP_DATA / "reports.parquet")
ttm = pd.read_parquet(EP_DATA / "reports_ttm.parquet")
required_reports = {
    "code6", "END_DATE", "ACT_PUBTIME", "UPDATE_TIME", "VERSION_TIME",
    "N_INCOME_ATTR_P",
}
required_ttm = {"code6", "END_DATE", "ACT_PUBTIME", "VERSION_TIME", "TTM_ni"}
if not required_reports.issubset(reports.columns):
    raise ValueError("EP reports.parquet is missing required columns")
if not required_ttm.issubset(ttm.columns):
    raise ValueError("EP reports_ttm.parquet is missing required columns")

reports["code6"] = reports["code6"].astype("string")
ttm["code6"] = ttm["code6"].astype("string")
reports["END_DATE"] = pd.to_datetime(reports["END_DATE"])
ttm["END_DATE"] = pd.to_datetime(ttm["END_DATE"])
reports["VERSION_TIME"] = pd.to_datetime(reports["VERSION_TIME"])
ttm["VERSION_TIME"] = pd.to_datetime(ttm["VERSION_TIME"])

if reports.duplicated(["code6", "END_DATE", "ACT_PUBTIME", "UPDATE_TIME"]).any():
    raise ValueError("EP reports has duplicate version keys")
if ttm.duplicated(["code6", "VERSION_TIME"]).any():
    raise ValueError("EP reports_ttm has duplicate code6 + VERSION_TIME")

reports.to_parquet(OUT / "income_versions_reused.parquet", index=False)
ttm.to_parquet(OUT / "reports_ttm_reused.parquet", index=False)
print("income cleaning: reused from EP delivery")
print(f"income versions: {len(reports):,}")
print(f"TTM events: {len(ttm):,}")
print(f"TTM valid events: {int(ttm['TTM_ni'].notna().sum()):,}")
print(f"negative TTM events: {int(ttm['TTM_ni'].lt(0).sum()):,}")
print(f"saved: {OUT / 'income_versions_reused.parquet'}")
print(f"saved: {OUT / 'reports_ttm_reused.parquet'}")
