"""정책기반 vs 규칙기반 분류기 (훈련된 KoElectra 모델 사용)

artifacts_train/output/policy-rule-classifier 에 저장된 모델을 로드하여
사용자 요구사항이 정책기반(policy)으로 처리될지, 규칙기반(rule_based)으로 처리될지 판별합니다.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch

try:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
except ImportError:
    raise ImportError("transformers 패키지가 필요합니다: pip install transformers")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _default_model_path() -> Path:
    return _project_root() / "artifacts_train" / "output" / "policy-rule-classifier"


class PolicyRuleClassifier:
    """정책기반 vs 규칙기반 분류기 (훈련된 KoElectra)"""

    def __init__(self, model_path: Optional[Path] = None):
        """분류기 초기화

        Args:
            model_path: 모델 디렉토리 경로 (None이면 기본 경로 사용)
        """
        self.model_path = model_path or _default_model_path()
        self.model = None
        self.tokenizer = None
        self._is_loaded = False

    def is_available(self) -> bool:
        """모델이 사용 가능한지 확인 (파일 존재 여부)"""
        return self.model_path.exists() and (self.model_path / "config.json").exists()

    def load(self):
        """모델과 토크나이저 로드"""
        if self._is_loaded:
            return

        if not self.is_available():
            return  # 조용히 실패 (모델이 없어도 서버는 계속 실행)

        try:
            print(f"[PolicyRuleClassifier] 모델 로드 중: {self.model_path}")
            self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
            self.model = AutoModelForSequenceClassification.from_pretrained(
                str(self.model_path),
                torch_dtype=torch.float32,
            )
            self.model.eval()  # 평가 모드
            self._is_loaded = True
            print("[PolicyRuleClassifier] 모델 로드 완료")
        except Exception as e:
            print(f"⚠️ [PolicyRuleClassifier] 모델 로드 실패: {str(e)[:200]}")
            self._is_loaded = False

    def predict(self, text: str) -> Dict[str, Any]:
        """요구사항 텍스트가 정책기반인지 규칙기반인지 판별

        Args:
            text: 요구사항 텍스트

        Returns:
            {
                "label": 0(규칙기반) 또는 1(정책기반),
                "label_name": "rule_based" 또는 "policy",
                "confidence": 확신도 (0.0 ~ 1.0),
            }
        """
        if not self._is_loaded:
            self.load()

        if not self._is_loaded or self.model is None or self.tokenizer is None:
            # 모델이 없으면 기본값 반환 (fallback)
            return {
                "label": 1,  # 기본값: 정책기반
                "label_name": "policy",
                "confidence": 0.5,
            }

        # 토크나이즈
        inputs = self.tokenizer(
            text,
            truncation=True,
            max_length=256,
            padding="max_length",
            return_tensors="pt",
        )

        # 추론
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=-1)[0]
            predicted_label = torch.argmax(probabilities).item()
            confidence = probabilities[predicted_label].item()

        return {
            "label": predicted_label,
            "label_name": "rule_based" if predicted_label == 0 else "policy",
            "confidence": round(confidence, 4),
        }
