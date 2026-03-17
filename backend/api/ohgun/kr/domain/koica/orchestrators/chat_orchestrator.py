"""KOICA 도메인 질문용 오케스트레이터 (재노출).

실제 구현은 domain.koica.hub.orchestrators.koica_orchestrator 에 있습니다.
기존 import 경로 호환을 위해 재노출합니다.
"""

from domain.koica.hub.orchestrators.koica_orchestrator import (
    KoicaOrchestrator,
)

# 기존 클래스명 호환을 위한 별칭
KoicaChatOrchestrator = KoicaOrchestrator

__all__ = ["KoicaChatOrchestrator", "KoicaOrchestrator"]

