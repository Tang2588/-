# -*- coding: utf-8 -*-
"""Step 3: 合并 EP 的 TTM 事件与 PB 的点时权益，计算 ROE 事件表。

ROE = TTM 归母净利润 / 平均归母权益，平均权益取本期与去年同期权益的均值。
本期或去年同期权益任一非正时 ROE 置为缺失，并在掩码中记录负权益。
"""
import math
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

from factor_paths import PB_BALANCE_VERSIONS, ROE_DIR, data_dirs  # noqa: E402

DATA, _ = data_dirs(ROE_DIR)
ttm = pd.read_parquet(DATA / "reports_ttm_reused.parquet")

balance = pd.read_parquet(PB_BALANCE_VERSIONS)
balance.to_parquet(DATA / "balance_versions_reused.parquet", index=False)

for frame in [ttm, balance]:
    frame["code6"] = frame["code6"].astype("string")
    frame["END_DATE"] = pd.to_datetime(frame["END_DATE"])
    frame["VERSION_TIME"] = pd.to_datetime(frame["VERSION_TIME"])

required_ttm = {"code6", "END_DATE", "VERSION_TIME", "TTM_ni"}
required_balance = {"code6", "END_DATE", "VERSION_TIME", "T_EQUITY_ATTR_P"}
if not required_ttm.issubset(ttm.columns):
    raise ValueError("reports_ttm_reused is missing required columns")
if not required_balance.issubset(balance.columns):
    raise ValueError("balance_versions is missing required columns")


def previous_year_end(end_date: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(end_date.year - 1, end_date.month, 1) + pd.offsets.MonthEnd(0)


ttm_groups = {code: group for code, group in ttm.groupby("code6", sort=False)}
balance_groups = {
    code: group for code, group in balance.groupby("code6", sort=False)
}
codes = sorted(set(ttm_groups).intersection(balance_groups))


def build_code_events(code: str) -> pd.DataFrame:
    ttm_group = ttm_groups[code].sort_values("VERSION_TIME")
    balance_group = balance_groups[code].sort_values("VERSION_TIME")
    ttm_by_time = {
        t: g for t, g in ttm_group.groupby("VERSION_TIME", sort=True)
    }
    balance_by_time = {
        t: g for t, g in balance_group.groupby("VERSION_TIME", sort=True)
    }
    times = sorted(set(ttm_by_time).union(balance_by_time))
    ttm_state = {}
    equity_state = {}
    rows = []

    for version_time in times:
        ttm_batch = ttm_by_time.get(version_time)
        if ttm_batch is not None:
            for row in ttm_batch.itertuples():
                ttm_state[row.END_DATE] = (
                    float(row.TTM_ni) if pd.notna(row.TTM_ni) else math.nan
                )
        balance_batch = balance_by_time.get(version_time)
        if balance_batch is not None:
            for row in balance_batch.itertuples():
                equity_state[row.END_DATE] = float(row.T_EQUITY_ATTR_P)

        if not ttm_state:
            continue
        latest_end = max(ttm_state)
        ttm_ni = ttm_state[latest_end]
        prior_end = previous_year_end(latest_end)
        current_equity = equity_state.get(latest_end, math.nan)
        prior_equity = equity_state.get(prior_end, math.nan)
        average_equity = math.nan
        roe = math.nan
        if pd.notna(current_equity) and pd.notna(prior_equity):
            average_equity = (current_equity + prior_equity) / 2.0
            if (
                pd.notna(ttm_ni)
                and current_equity > 0
                and prior_equity > 0
            ):
                roe = ttm_ni / average_equity

        negative_equity = int(
            (pd.notna(current_equity) and current_equity <= 0)
            or (pd.notna(prior_equity) and prior_equity <= 0)
        )
        rows.append(
            {
                "code6": code,
                "END_DATE": latest_end,
                "PRIOR_END_DATE": prior_end,
                "VERSION_TIME": version_time,
                "TTM_ni": ttm_ni,
                "equity_current": current_equity,
                "equity_prior": prior_equity,
                "average_equity": average_equity,
                "negative_equity": negative_equity,
                "ROE": roe,
            }
        )
    return pd.DataFrame(rows)


events = pd.concat(
    [build_code_events(code) for code in codes], ignore_index=True
)
events = events.sort_values(["code6", "VERSION_TIME"]).reset_index(drop=True)
if events.duplicated(["code6", "VERSION_TIME"]).any():
    raise ValueError("ROE event table has duplicate code6 + VERSION_TIME")

events.to_parquet(DATA / "roe_events.parquet", index=False)
print(f"codes with both statements: {len(codes):,}")
print(f"ROE events: {len(events):,}")
print(f"TTM valid events: {int(events['TTM_ni'].notna().sum()):,}")
print(f"average equity valid events: {int(events['average_equity'].notna().sum()):,}")
print(f"ROE valid events: {int(events['ROE'].notna().sum()):,}")
print(f"negative-equity events: {int(events['negative_equity'].eq(1).sum()):,}")
print(f"saved: {DATA / 'roe_events.parquet'}")
