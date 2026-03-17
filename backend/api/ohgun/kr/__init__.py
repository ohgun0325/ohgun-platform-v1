"""LangChain RAG Application package."""

# kr 루트를 sys.path 맨 앞에 두고, 상위 'api'를 sys.modules에서 제거하여
# 이 패키지 내부의 "from api.xxx", "from core.xxx", "from domain.xxx"가
# backend/api/ohgun/kr 기준으로 해석되도록 함 (uvicorn api.ohgun.kr.main:app 호환)
import sys
from pathlib import Path

_kr_root = Path(__file__).resolve().parent
_kr_root_str = str(_kr_root)
if _kr_root_str not in sys.path:
    sys.path.insert(0, _kr_root_str)
if "api" in sys.modules:
    del sys.modules["api"]

__version__ = "1.0.0"
# Trigger deployment

