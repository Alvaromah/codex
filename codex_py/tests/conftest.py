import sys
from pathlib import Path

# Ensure the repository root is on sys.path when tests are run from outside
# tests/ is inside codex_py/, so we need the repository root two levels up
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
