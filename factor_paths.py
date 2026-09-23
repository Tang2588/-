# -*- coding: utf-8 -*-
"""四个因子项目共用的路径常量与共用数据加载。

放在 ``D:\\因子计算`` 下，所有步骤脚本从这里取路径，避免把目录写死在每个文件里。

**股票池单一来源**：行情面板统一由 EP 的 ``step1_样本筛选.py`` 生成，
其余三个因子通过 :func:`load_market_panel` 复制使用，并强制校验口径一致。
"""
from __future__ import annotations

import re
from pathlib import Path
from shutil import copyfile

import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parent
BASE_DATA = Path(r"D:\实习生学习项目\基础数据")

# 四个交付目录
EP_DIR = PROJECT_ROOT / "市盈率" / "EP因子_交付版"
PB_DIR = PROJECT_ROOT / "市净率" / "PB因子_交付版"
ROE_DIR = PROJECT_ROOT / "ROE因子_交付版"
SIZE_DIR = PROJECT_ROOT / "规模因子_交付版"

# 基础数据源
MARKET_SOURCE = BASE_DATA / "chn_equ_mkt_quotation.parquet"
INCOME_SOURCE = BASE_DATA / "vw_fdmt_is_new.parquet"
BALANCE_SOURCE = BASE_DATA / "vw_fdmt_bs_new.parquet"

# EP 产出的中间结果，其余因子直接复用
EP_DATA = EP_DIR / "中间结果"
MARKET_PANEL = EP_DATA / "_mkt_clean.parquet"
EP_REPORTS = EP_DATA / "reports.parquet"
EP_REPORTS_TTM = EP_DATA / "reports_ttm.parquet"

# PB 产出的中间结果，ROE 复用权益
PB_DATA = PB_DIR / "中间结果"
PB_BALANCE_VERSIONS = PB_DATA / "balance_versions.parquet"

# 沪深 B 股：沪市 900xxx、深市 200/201xxx
B_SHARE_PATTERN = re.compile(r"^(900\d{3}|20[01]\d{3})$")


def data_dirs(root: Path) -> tuple[Path, Path]:
    """返回 (中间结果目录, 因子结果目录)，不存在时创建。"""
    mid = root / "中间结果"
    final = root / "因子结果"
    mid.mkdir(parents=True, exist_ok=True)
    final.mkdir(parents=True, exist_ok=True)
    return mid, final


def load_market_panel(dest_root: Path) -> Path:
    """把 EP 生成的行情面板复制到本因子目录，并校验口径。

    校验两点，任一不满足直接报错：

    1. 已排除沪深 B 股（EP 口径为 89 只）；
    2. 含 ``financial_code6`` 字段，用于北交所代码切换后的财报连接。

    这样四个因子必然使用同一股票池，不会再出现某个因子用旧版行情表的情况。
    """
    if not MARKET_PANEL.exists():
        raise FileNotFoundError(f"找不到 EP 行情面板：{MARKET_PANEL}")

    dest = dest_root / "中间结果" / "_mkt_clean.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    copyfile(MARKET_PANEL, dest)

    schema = pq.ParquetFile(dest).schema_arrow.names
    if "financial_code6" not in schema:
        raise ValueError(
            f"行情面板缺少 financial_code6，无法处理北交所代码切换：{MARKET_PANEL}"
        )

    frame = pq.ParquetFile(dest).read(columns=["code6"]).to_pandas()
    codes = frame["code6"].astype("string")
    b_shares = codes.str.match(B_SHARE_PATTERN, na=False)
    if b_shares.any():
        raise ValueError(
            f"行情面板仍含沪深 B 股 {int(b_shares.sum()):,} 行，"
            f"与 EP 口径不一致：{MARKET_PANEL}"
        )
    print(f"market panel: {len(frame):,} rows, B shares excluded, financial_code6 available")
    print(f"saved: {dest}")
    return dest
