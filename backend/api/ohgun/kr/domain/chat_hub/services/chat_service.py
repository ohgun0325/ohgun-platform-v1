"""Chat 서비스 - Gemini API를 사용한 대화형 챗봇 서비스

Gemini API 호출 로직을 캡슐화합니다.
"""

from typing import Optional, TYPE_CHECKING

from core.llm.gemini import get_chat_model
from langchain_core.messages import HumanMessage

if TYPE_CHECKING:
    from langchain_google_genai import ChatGoogleGenerativeAI


class ChatService:
    """Gemini API를 사용한 챗봇 서비스 클래스"""

    def __init__(self):
        """서비스 초기화"""
        self._chat_model: Optional["ChatGoogleGenerativeAI"] = None

    @property
    def chat_model(self) -> Optional["ChatGoogleGenerativeAI"]:
        """Gemini 챗 모델 인스턴스 (lazy loading)"""
        if self._chat_model is None:
            self._chat_model = get_chat_model()
        return self._chat_model

    def reload_model(self) -> None:
        """모델 다시 로드"""
        self._chat_model = None
        _ = self.chat_model  # 강제 로드

    def chat(self, message: str) -> str:
        """사용자 메시지에 대한 Gemini 응답 생성

        Args:
            message: 사용자 메시지

        Returns:
            Gemini API의 응답 텍스트

        Raises:
            ValueError: 모델이 사용 불가능하거나 메시지가 비어있을 때
            Exception: Gemini API 호출 중 오류 발생 시
        """
        if not message.strip():
            raise ValueError("메시지가 비어있습니다")

        if self.chat_model is None:
            raise ValueError("Gemini API를 사용할 수 없습니다. API 키를 확인하세요.")

        # Gemini API로 메시지 전송
        messages = [HumanMessage(content=message)]
        response = self.chat_model.invoke(messages)

        # 응답 추출
        if hasattr(response, 'content'):
            return response.content
        elif isinstance(response, str):
            return response
        else:
            return str(response)

    def is_available(self) -> bool:
        """Gemini API 사용 가능 여부 확인"""
        return self.chat_model is not None
