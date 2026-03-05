from abc import ABC, abstractmethod

# 1. 전략 인터페이스 정의
class PDFExtractionStrategy(ABC):
    @abstractmethod
    def extract(self, file_path: str) -> str:
        pass

