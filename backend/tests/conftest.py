"""Pytest configuration: kr 모듈 루트를 sys.path에 추가하여 api/domain/core 등 import 해결."""
import sys
from pathlib import Path

_backend_root = Path(__file__).resolve().parent.parent
_kr_root = _backend_root / "api" / "ohgun" / "kr"
if str(_kr_root) not in sys.path:
    sys.path.insert(0, str(_kr_root))
