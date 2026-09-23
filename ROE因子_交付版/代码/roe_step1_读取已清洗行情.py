# -*- coding: utf-8 -*-
"""Step 1: 载入已清洗的行情面板。

行情清洗统一由 EP 的 ``step1_样本筛选.py`` 完成。这里直接从 EP 读取，
不再经过 PB 中转，避免多级复制导致某个环节停留在旧版本。
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

from factor_paths import ROE_DIR, load_market_panel  # noqa: E402

load_market_panel(ROE_DIR)
