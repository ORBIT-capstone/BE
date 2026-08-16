import sys
from pathlib import Path

BACKTEST_DIR = Path(__file__).resolve().parent.parent
FASTAPI_ROOT = BACKTEST_DIR.parent

for path in (BACKTEST_DIR / "scripts", BACKTEST_DIR / "config", FASTAPI_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
