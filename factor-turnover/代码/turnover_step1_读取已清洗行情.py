# -*- coding: utf-8 -*-
"""Step 1: 载入已清洗的行情面板。

股票池统一由 EP 的 ``ep_step1_样本筛选.py`` 生成。本步骤只做复制与口径校验，
不重新清洗，确保与其它因子使用完全相同的股票池。
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

from factor_paths import TURNOVER_DIR, load_market_panel  # noqa: E402

load_market_panel(TURNOVER_DIR)
