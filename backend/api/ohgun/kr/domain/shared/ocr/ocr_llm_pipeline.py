"""
OCR + LLM 파이프라인: EasyOCR 결과를 Exaone으로 보정·구조화

흐름: 이미지 → EasyOCR → (후처리) → Exaone 보정/필드 추출 → 구조화된 결과
"""

import io
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.domain.shared.bases.semantic_matcher import get_default_semantic_matcher

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# BaseLLMModel은 app.state.chat_model로 주입되므로 런타임에만 필요
try:
    from artifacts.models.interfaces.base import BaseLLMModel
except ImportError:
    BaseLLMModel = None  # type: ignore

# 시스템 프롬프트: OCR 오류 보정 + 필드 매핑 (추론 금지)
SYSTEM_PROMPT_OCR_CORRECTION = """당신은 한국어 양식 문서의 OCR 결과에서 **명백한 OCR 인식 오류만 수정**하고 필드를 매핑하는 전문가입니다.

**엄격한 규칙**
1. OCR 텍스트에 존재하지 않는 정보는 절대 생성하지 마세요.
2. 의미 기반 추론/창작은 금지됩니다 (예: "4415년" → "2025년" 같은 변환 금지).
3. 허용되는 보정:
   - 명백한 OCR 오류: "6o45" → "6045", "춤청" → "충청", "행우" → "행위"
   - 띄어쓰기 정리
   - 형식 통일 (이미 전처리되어 있음)

**필드 매핑 규칙**
- 주어진 OCR 텍스트 조각 중 어느 것이 어느 필드에 해당하는지 분류
- OCR 원문을 evidence_text로 반드시 포함
- 불확실하면 빈 값 + confidence 낮게

**응답 형식 (반드시 JSON만 출력)**
```json
{
  "fields": {
    "담당자이름": {"value": "", "evidence_text": "", "confidence": 0.0},
    "회사명": {"value": "", "evidence_text": "", "confidence": 0.0},
    "사업자번호": {"value": "", "evidence_text": "", "confidence": 0.0},
    "회사연락처": {"value": "", "evidence_text": "", "confidence": 0.0},
    "회사주소": {"value": "", "evidence_text": "", "confidence": 0.0},
    "주요내용": {"value": "", "evidence_text": "", "confidence": 0.0},
    "작성날짜": {"value": "", "evidence_text": "", "confidence": 0.0}
  },
  "corrections": [
    {"original": "OCR 원문", "corrected": "보정 문자", "reason": "OCR 오류"}
  ]
}
```

- value: 보정된 값 (OCR 범위 내에서만)
- evidence_text: 실제 OCR 원문 조각
- confidence: 0.0~1.0 (확실하면 1.0, 불확실하면 낮게)
- corrections: 실제로 보정한 OCR 오류만 나열 (없으면 빈 배열)"""


def _run_ocr_sync(reader: Any, image_bytes: bytes) -> Tuple[str, List[Dict[str, Any]]]:
    """동기 OCR 실행. full_text와 items(텍스트, 신뢰도, bbox 등) 반환."""
    import numpy as np
    from PIL import Image

    logger.info("[OCR] EasyOCR 실행 시작 (이미지 크기: %d bytes)", len(image_bytes))
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img_array = np.array(img)
    results = reader.reader.readtext(img_array)

    items: List[Dict[str, Any]] = []
    texts: List[str] = []
    for bbox, text, conf in results:
        items.append({
            "text": text,
            "confidence": float(conf),
            "bbox": bbox,
        })
        texts.append(text)
    full_text = " ".join(texts)
    logger.info(
        "[OCR] EasyOCR 완료: 인식 항목 %d개, 전체 길이 %d자, 앞 200자: %s",
        len(items),
        len(full_text),
        (full_text[:200] + "..." if len(full_text) > 200 else full_text),
    )
    return full_text, items


def _shrink_field_contexts_with_embeddings(
    field_contexts: Dict[str, str],
    max_chars: int = 220,
) -> Dict[str, str]:
    """임베딩 기반으로 필드 컨텍스트를 축약해 LLM 토큰 수를 줄입니다.

    - 각 필드 컨텍스트가 max_chars를 초과할 때만 동작
    - 컨텍스트를 간단히 문장/라인 단위로 분리한 뒤
    - field_name을 쿼리로 하여 SemanticFieldMatcher.rank_candidates로 상위 N개만 선택
    """
    if not field_contexts:
        return field_contexts

    try:
        matcher = get_default_semantic_matcher()
    except Exception as e:
        logger.warning(
            "[OCR+LLM] 임베딩 기반 컨텍스트 축약 비활성화 (매처 초기화 실패): %s",
            e,
        )
        return field_contexts

    new_contexts: Dict[str, str] = {}

    for field_name, context in field_contexts.items():
        if not context or len(context) <= max_chars:
            new_contexts[field_name] = context
            continue

        # 간단한 문장/라인 단위 분할
        segments = re.split(r"[.\n]", context)
        segments = [s.strip() for s in segments if s and s.strip()]

        # 분할이 안 되면 단순 자르기
        if not segments:
            shortened = context[:max_chars]
            logger.info(
                "[OCR+LLM] 컨텍스트 축약(분할 실패): field=%s, 원래 길이=%d, 축약 후 길이=%d",
                field_name,
                len(context),
                len(shortened),
            )
            new_contexts[field_name] = shortened
            continue

        # 임베딩으로 field_name과 가장 잘 맞는 세그먼트 상위 3개 선택
        labeled_segments = [seg for seg in segments]
        ranked = matcher.rank_candidates(field_name, labeled_segments, top_k=3)
        selected = [seg for seg, _ in ranked] or segments[:3]
        shortened = " ".join(selected)

        logger.info(
            "[OCR+LLM] 임베딩 기반 컨텍스트 축약: field=%s, 원래 길이=%d, 축약 후 길이=%d, 세그먼트=%d→%d",
            field_name,
            len(context),
            len(shortened),
            len(segments),
            len(selected),
        )
        new_contexts[field_name] = shortened

    return new_contexts


def _build_user_prompt(
    full_text: str,
    items: List[Dict[str, Any]],
    field_contexts: Dict[str, str],
    patterns: Dict[str, List[str]],
) -> str:
    """LLM에 넘길 사용자 프롬프트 구성 (입력 최소화)"""
    # 1차 문자열 기반 field_contexts를 임베딩으로 한번 더 축약해 토큰 수를 줄인다.
    field_contexts = _shrink_field_contexts_with_embeddings(field_contexts)

    lines = ["아래는 OCR이 추출한 텍스트입니다. 명백한 OCR 오류만 수정하고 필드를 매핑해주세요.\n"]
    
    # 라벨 주변 텍스트만 전달 (전체 텍스트 대신)
    if field_contexts:
        lines.append("**필드 주변 텍스트**")
        for field_name, context in field_contexts.items():
            lines.append(f"- {field_name}: \"{context}\"")
        lines.append("")
    
    # 추출된 패턴 힌트 제공
    if patterns.get('phone_numbers'):
        lines.append(f"**전화번호 후보**: {', '.join(patterns['phone_numbers'][:3])}")
    if patterns.get('business_numbers'):
        lines.append(f"**사업자번호 후보**: {', '.join(patterns['business_numbers'][:3])}")
    if patterns.get('dates'):
        lines.append(f"**날짜 후보**: {', '.join(patterns['dates'][:3])}")
    
    # 신뢰도 낮은 항목 (OCR 오류 가능성 높음)
    low = [x for x in items if x.get("confidence", 1.0) < 0.7 and x.get("text")]
    if low:
        lines.append("\n**신뢰도 낮은 구간 (OCR 오류 가능)**")
        for x in low[:3]:  # 최대 3개만 전달해 토큰 수 절감
            lines.append(f"  - \"{x['text']}\" (신뢰도: {x.get('confidence', 0):.2f})")
    
    return "\n".join(lines)


def _parse_llm_json_response(response_text: str) -> Dict[str, Any]:
    """LLM 응답 문자열에서 JSON 블록을 추출해 파싱."""
    text = response_text.strip()
    # ```json ... ``` 또는 ```\n...\n``` 블록 찾기
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    # 그냥 JSON 객체로 시작하는 경우
    start = text.find("{")
    if start != -1:
        depth = 0
        end = -1
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end != -1:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "fields": {},
            "corrections": [],
        }


def run_ocr_only(reader: Any, image_bytes: bytes) -> Tuple[str, List[Dict[str, Any]]]:
    """EasyOCR만 실행하여 full_text와 items 반환."""
    return _run_ocr_sync(reader, image_bytes)


def run_llm_correction(
    full_text: str,
    items: List[Dict[str, Any]],
    llm_model: Any,
    preprocessed_text: str,
    patterns: Dict[str, List[str]],
    field_contexts: Dict[str, str],
) -> Dict[str, Any]:
    """
    OCR 결과를 LLM(Gemini/Exaone)에 넘겨 OCR 오류만 보정하고 필드 매핑.

    Args:
        full_text: OCR 원본 텍스트
        items: OCR 항목 리스트
        llm_model: Gemini 또는 Exaone 모델
        preprocessed_text: 전처리된 텍스트
        patterns: 추출된 패턴들 (전화번호, 사업자번호, 날짜)
        field_contexts: 필드별 라벨 주변 텍스트

    Returns:
        {
            "fields": dict,  # 필드명 → {value, evidence_text, confidence}
            "corrections": list,
            "raw_response": str
        }
    """
    user_content = _build_user_prompt(preprocessed_text, items, field_contexts, patterns)
    
    # 모델 타입 확인 (Gemini vs Exaone)
    is_gemini = False
    if hasattr(llm_model, '__class__'):
        class_name = llm_model.__class__.__name__
        is_gemini = 'Gemini' in class_name or 'Google' in class_name
    
    logger.info(
        "[OCR+LLM] %s 보정 요청 시작 (전처리 완료, 입력 최소화)",
        "Gemini API" if is_gemini else "Exaone"
    )
    
    try:
        if is_gemini:
            # Gemini는 LangChain 메시지 형식 사용
            from langchain_core.messages import SystemMessage, HumanMessage
            messages_langchain = [
                SystemMessage(content=SYSTEM_PROMPT_OCR_CORRECTION),
                HumanMessage(content=user_content),
            ]
            response = llm_model.invoke(messages_langchain)
            response_text = response.content if hasattr(response, 'content') else str(response)
        else:
            # Exaone는 dict 리스트 형식 사용
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT_OCR_CORRECTION},
                {"role": "user", "content": user_content},
            ]
            # 가능한 경우 토큰 수와 temperature를 강하게 제한
            try:
                response_text = llm_model.invoke(
                    messages,
                    max_new_tokens=512,
                    temperature=0.0,
                )
            except TypeError:
                # invoke가 추가 인자를 받지 못하는 구현일 수 있으므로 안전하게 폴백
                response_text = llm_model.invoke(messages)

        logger.info(
            "[OCR+LLM] %s 응답 수신 (길이: %d자)",
            "Gemini" if is_gemini else "Exaone",
            len(response_text)
        )
    except Exception as e:
        logger.warning("[OCR+LLM] LLM 호출 실패: %s → OCR 원문 그대로 반환", e)
        return {
            "fields": {},
            "corrections": [],
            "error": str(e),
            "raw_response": "",
        }
    
    parsed = _parse_llm_json_response(response_text)
    fields = parsed.get("fields", {})
    corrections = parsed.get("corrections", [])
    
    logger.info(
        "[OCR+LLM] %s 보정 완료: used_llm=True, corrections=%d건, fields=%d개",
        "Gemini" if is_gemini else "Exaone",
        len(corrections),
        len([f for f in fields.values() if f.get("value")]),
    )
    if corrections:
        for i, c in enumerate(corrections[:5]):
            logger.info(
                "[OCR+LLM] 보정 #%d: %r → %r (%s)",
                i + 1,
                c.get("original", "")[:80],
                c.get("corrected", "")[:80],
                c.get("reason", ""),
            )
        if len(corrections) > 5:
            logger.info("[OCR+LLM] ... 외 %d건 더 있음", len(corrections) - 5)
    
    return {
        "fields": fields,
        "corrections": corrections,
        "raw_response": response_text,
    }


def run_pipeline(
    reader: Any,
    image_bytes: bytes,
    llm_model: Optional[Any] = None,
    min_confidence: float = 0.3,
) -> Dict[str, Any]:
    """
    OCR → 전처리 → LLM 보정 파이프라인 전체 실행.

    Args:
        reader: EasyOCRReader 인스턴스
        image_bytes: 이미지 바이트
        llm_model: Exaone 등 BaseLLMModel 호환 객체. None이면 OCR만 수행
        min_confidence: OCR 항목 최소 신뢰도

    Returns:
        {
            "raw_full_text": str,
            "raw_items": list,
            "preprocessed_text": str,  # 전처리된 텍스트
            "corrected_text": str | None,
            "fields": dict,  # 필드명 → {value, evidence_text, confidence}
            "corrections": list,
            "used_llm": bool,
            "error": str | None,
        }
    """
    # 1. OCR 실행
    full_text, items = run_ocr_only(reader, image_bytes)
    filtered = [x for x in items if x.get("confidence", 0) >= min_confidence]
    if not filtered:
        filtered = items

    # 2. 전처리 (정규식 기반 정규화 + 패턴 추출)
    from .ocr_preprocessing import (
        preprocess_ocr_text,
        extract_all_field_contexts,
    )
    
    preprocessed_text, patterns = preprocess_ocr_text(full_text)
    logger.info(
        "[OCR 파이프라인] 전처리 완료: 전화번호 %d개, 사업자번호 %d개, 날짜 %d개 추출",
        len(patterns.get("phone_numbers", [])),
        len(patterns.get("business_numbers", [])),
        len(patterns.get("dates", [])),
    )
    
    # 3. 라벨 주변 텍스트 추출 (LLM 입력 최소화)
    field_labels = {
        "담당자이름": ["성명", "담당자명", "담당자"],
        "회사명": ["회사명", "발행회사명"],
        "사업자번호": ["사업자번호", "사업자 번호"],
        "회사연락처": ["연락처", "연락 처", "전화번호"],
        "회사주소": ["주소", "주 소", "소재지"],
        "주요내용": ["위임내용", "위임 내용", "위임사항"],
        "작성날짜": ["작성일", "위임일", "날짜"],
    }
    # window_size를 작게 유지해 LLM 입력 토큰 수 최소화
    field_contexts = extract_all_field_contexts(preprocessed_text, field_labels, window_size=100)
    
    out: Dict[str, Any] = {
        "raw_full_text": full_text,
        "raw_items": items,
        "preprocessed_text": preprocessed_text,
        "corrected_text": preprocessed_text,  # 기본값은 전처리 결과
        "fields": {},
        "corrections": [],
        "used_llm": False,
        "error": None,
    }

    # 4. LLM 보정 (선택적)
    if llm_model is not None and getattr(llm_model, "invoke", None):
        is_gemini = False
        if hasattr(llm_model, '__class__'):
            class_name = llm_model.__class__.__name__
            is_gemini = 'Gemini' in class_name or 'Google' in class_name
        
        logger.info(
            "[OCR 파이프라인] LLM(%s) 사용 가능 → 보정 단계 실행",
            "Gemini API" if is_gemini else "기타 LLM"
        )
        try:
            llm_result = run_llm_correction(
                full_text, items, llm_model, preprocessed_text, patterns, field_contexts
            )
            out["fields"] = llm_result.get("fields") or {}
            out["corrections"] = llm_result.get("corrections") or []
            out["used_llm"] = True
            
            # corrected_text: corrections 적용한 텍스트 생성
            corrected = preprocessed_text
            for corr in out["corrections"]:
                orig = corr.get("original", "")
                fixed = corr.get("corrected", "")
                if orig and fixed:
                    corrected = corrected.replace(orig, fixed)
            out["corrected_text"] = corrected
            
            if llm_result.get("error"):
                out["error"] = llm_result["error"]
            
            logger.info(
                "[OCR 파이프라인] 완료: used_llm=True, corrections=%d, fields=%d",
                len(out["corrections"]),
                len([f for f in out["fields"].values() if isinstance(f, dict) and f.get("value")]),
            )
        except Exception as e:
            logger.exception("[OCR 파이프라인] LLM 보정 중 예외 → 전처리 결과만 반환: %s", e)
            out["error"] = str(e)
    else:
        logger.info(
            "[OCR 파이프라인] LLM 미사용(모델 없음 또는 미로드) → 전처리 결과만 반환, used_llm=False"
        )

    return out
