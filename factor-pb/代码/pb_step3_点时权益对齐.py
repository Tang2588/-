# -*- coding: utf-8 -*-
"""Step 3: 生成点时归母权益快照。

资产负债表是报告期末的时点数据，不做 TTM。按版本时间推进状态，
每次版本事件取报告期最新的权益值。
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

from factor_paths import PB_DIR, data_dirs  # noqa: E402

DATA, _ = data_dirs(PB_DIR)
bs = pd.read_parquet(DATA / "balance_versions.parquet")
bs["END_DATE"] = pd.to_datetime(bs["END_DATE"])
bs["ACT_PUBTIME"] = pd.to_datetime(bs["ACT_PUBTIME"])
bs["VERSION_TIME"] = pd.to_datetime(bs["VERSION_TIME"])
bs = bs.sort_values(["code6", "VERSION_TIME", "ACT_PUBTIME", "END_DATE"])


def build_code_snapshot(group: pd.DataFrame) -> pd.DataFrame:
    state = {}
    rows = []
    for version_time, batch in group.groupby("VERSION_TIME", sort=True):
        for row in batch.itertuples(index=False):
            state[row.END_DATE] = float(row.T_EQUITY_ATTR_P)
        latest_end = max(state)
        rows.append(
            {
                "code6": group["code6"].iat[0],
                "END_DATE": latest_end,
                "ACT_PUBTIME": batch["ACT_PUBTIME"].max(),
                "VERSION_TIME": version_time,
                "book_equity_parent": state[latest_end],
            }
        )
    return pd.DataFrame(rows)


snap = pd.concat(
    [build_code_snapshot(g) for _, g in bs.groupby("code6", sort=False)],
    ignore_index=True,
)
snap = snap.sort_values(["code6", "VERSION_TIME"]).reset_index(drop=True)
if snap.duplicated(["code6", "VERSION_TIME"]).any():
    raise ValueError("点时权益表存在重复的 code6 + VERSION_TIME")
snap.to_parquet(DATA / "book_equity_snapshots.parquet", index=False)
print(f"snapshot events: {len(snap):,}")
print(f"negative equity events: {int(snap['book_equity_parent'].lt(0).sum()):,}")
print(f"saved: {DATA / 'book_equity_snapshots.parquet'}")
