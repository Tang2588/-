# -*- coding: utf-8 -*-
"""Step 2: 清洗合并资产负债表的财报版本，构造点时权益快照的输入。"""
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

from factor_paths import BALANCE_SOURCE, PB_DIR, data_dirs  # noqa: E402

OUT, _ = data_dirs(PB_DIR)
SOURCE = BALANCE_SOURCE

columns = [
    "TICKER_SYMBOL", "ACT_PUBTIME", "UPDATE_TIME", "END_DATE",
    "FISCAL_PERIOD", "MERGED_FLAG", "T_EQUITY_ATTR_P",
]
bs = pd.read_parquet(SOURCE, columns=columns).rename(
    columns={"TICKER_SYMBOL": "code6"}
)
bs["code6"] = bs["code6"].astype("string").str.extract(r"(\d{6})", expand=False)
bs["ACT_PUBTIME"] = pd.to_datetime(bs["ACT_PUBTIME"], errors="coerce")
bs["UPDATE_TIME"] = pd.to_datetime(bs["UPDATE_TIME"], errors="coerce")
bs["END_DATE"] = pd.to_datetime(bs["END_DATE"], errors="coerce")
bs["FISCAL_PERIOD"] = pd.to_numeric(bs["FISCAL_PERIOD"], errors="coerce")
bs["T_EQUITY_ATTR_P"] = pd.to_numeric(bs["T_EQUITY_ATTR_P"], errors="coerce")
bs = bs.dropna(
    subset=["code6", "ACT_PUBTIME", "END_DATE", "FISCAL_PERIOD", "T_EQUITY_ATTR_P"]
).copy()
bs = bs[bs["MERGED_FLAG"].astype("string").str.strip().eq("1")].copy()
bs["report_month"] = bs["END_DATE"].dt.month
bs = bs[bs["report_month"].eq(bs["FISCAL_PERIOD"])].copy()

# Use UPDATE_TIME to distinguish source corrections sharing ACT_PUBTIME.
bs["VERSION_TIME"] = bs[["ACT_PUBTIME", "UPDATE_TIME"]].max(axis=1)
version_cols = [
    "code6", "END_DATE", "FISCAL_PERIOD", "ACT_PUBTIME", "UPDATE_TIME",
    "T_EQUITY_ATTR_P",
]
bs = bs.drop_duplicates(version_cols, keep="first")
key = ["code6", "END_DATE", "ACT_PUBTIME", "UPDATE_TIME"]
if bs.duplicated(key).any():
    raise ValueError("资产负债表仍存在重复版本键")

effective_key = ["code6", "END_DATE", "VERSION_TIME"]
conflict = bs.groupby(effective_key)["T_EQUITY_ATTR_P"].nunique(dropna=False).gt(1)
if conflict.any():
    raise ValueError("同一有效版本时间存在不同归母股东权益，无法确定版本")

bs = bs[
    [
        "code6", "END_DATE", "FISCAL_PERIOD", "ACT_PUBTIME", "UPDATE_TIME",
        "VERSION_TIME", "T_EQUITY_ATTR_P",
    ]
].sort_values(["code6", "VERSION_TIME", "END_DATE"])
bs.to_parquet(OUT / "balance_versions.parquet", index=False)
print(f"balance versions: {len(bs):,}")
print(f"report periods: {bs[['code6', 'END_DATE']].drop_duplicates().shape[0]:,}")
print(f"periods with multiple versions: {int((bs.groupby(['code6', 'END_DATE']).size() > 1).sum()):,}")
print(f"negative parent equity: {int(bs['T_EQUITY_ATTR_P'].lt(0).sum()):,}")
print(f"saved: {OUT / 'balance_versions.parquet'}")
