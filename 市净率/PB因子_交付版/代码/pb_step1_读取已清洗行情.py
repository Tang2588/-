# -*- coding: utf-8 -*-
"""Step 1: 载入已清洗的行情面板。

行情清洗（代码规范化、沪深 B 股排除、北交所新旧代码映射）统一由 EP 的
``step1_样本筛选.py`` 完成。本步骤只做复制与口径校验，确保四个因子使用
完全相同的股票池。
"""
import sys
from pathlib import Path

# 项目根目录：含 factor_paths.py 与 pure_factor_streaming.py
PROJECT_ROOT = next(
    (p for p in Path(__file__).resolve().parents if (p / "factor_paths.py").exists()),
    None,
)
if PROJECT_ROOT is None:
    raise RuntimeError(r"找不到项目根目录，请确认 D:\因子计算\factor_paths.py 存在")
sys.path.insert(0, str(PROJECT_ROOT))

from factor_paths import PB_DIR, load_market_panel  # noqa: E402

load_market_panel(PB_DIR)
