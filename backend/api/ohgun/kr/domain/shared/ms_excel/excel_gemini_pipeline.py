"""Excel 추출 + Gemini 보정 파이프라인.

흐름: Excel 업로드 → pandas/필드 추출 → Gemini 보정 → 보정된 필드 + 보정 내역 반환
터미널 로그로 각 단계가 출력되도록 설계.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Gemini 보정용 시스템 프롬프트
SYSTEM_PROMPT_EXCEL_CORRECTION = """당신은 Excel에서 추출된 회사정보 필드의 **형식 오류만** 수정하는 전문가입니다.

**엄격한 규칙**
1. 추출된 값에 존재하지 않는 정보를 만들지 마세요.
2. 다음 유형의 오류만 보정하세요:
   - 잘못된 필드에 들어간 값 (예: "담당자 연락처"에 "YYYY-MM-DD" 같은 날짜 형식이 들어간 경우 → "확인 필요" 또는 해당 필드가 비어있으면 빈 값)
   - 날짜/시간이 붙어있는 형식 (예: "2026-01-0100:00:00" → "2026-01-01", "2026-12-3100:00:00" → "2026-12-31")
   - 전화번호 필드에 날짜가 들어간 경우 제거 또는 "확인 필요"
3. 명확히 올바른 값은 그대로 두세요.
4. 보정한 경우에만 corrections 배열에 항목을 추가하세요.

**응답 형식 (반드시 JSON만 출력)**
```json
{
  "fields": {
    "회사명": {"value": "보정된값 또는 원래값"},
    "담당자명": {"value": "..."},
    "사업자번호": {"value": "..."},
    "담당자연락처": {"value": "..."},
    "회사주소": {"value": "..."},
    "담당자이메일": {"value": "..."},
    "통화단위": {"value": "..."},
    "데이터기준기간시작일": {"value": "YYYY-MM-DD 형식"},
    "데이터기준기간종료일": {"value": "YYYY-MM-DD 형식"}
  },
  "corrections": [
    {"field": "필드명", "original": "원래값", "corrected": "보정값", "reason": "보정 사유"}
  ]
}
```
- fields: 입력으로 받은 모든 필드에 대해 value만 포함. 없는 필드는 빈 문자열.
- corrections: 실제로 값을 바꾼 경우만 나열."""


def _parse_llm_json_response(response_text: str) -> Dict[str, Any]:
    """LLM 응답 문자열에서 JSON 블록 추출 후 파싱."""
    text = response_text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
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
        return {"fields": {}, "corrections": []}


def _build_user_prompt(extracted_fields: Dict[str, Any]) -> str:
    """추출된 필드 딕셔너리를 Gemini용 사용자 프롬프트로 변환."""
    lines = ["다음은 Excel에서 추출한 회사정보 필드입니다. 형식 오류가 있으면 보정한 뒤 JSON으로만 답하세요.\n"]
    for name, data in extracted_fields.items():
        if isinstance(data, dict):
            val = data.get("value", data.get("value", ""))
        else:
            val = str(data)
        lines.append(f"- {name}: {val}")
    return "\n".join(lines)


def run_gemini_correction(
    extracted_fields: Dict[str, Any],
    gemini_model: Any,
) -> Dict[str, Any]:
    """추출된 필드를 Gemini로 보정합니다.

    Args:
        extracted_fields: extract_fields_from_excel 결과의 fields (필드명 → {value, ...})
        gemini_model: ChatGoogleGenerativeAI 등 invoke(messages) 지원 모델

    Returns:
        {
            "fields": 필드명 → {"value": 보정된값},
            "corrections": [{"field", "original", "corrected", "reason"}],
            "error": str | None
        }
    """
    # 추출값만 평탄화 (value만 나열)
    flat: Dict[str, str] = {}
    for name, data in extracted_fields.items():
        if isinstance(data, dict):
            flat[name] = str(data.get("value", ""))
        else:
            flat[name] = str(data)

    user_content = _build_user_prompt(flat)

    logger.info(
        "[Excel+Gemini] 보정 요청 시작: 필드 %d개",
        len(flat),
    )
    print("[Excel+Gemini] 보정 요청 시작: 필드 %d개" % len(flat))

    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = [
            SystemMessage(content=SYSTEM_PROMPT_EXCEL_CORRECTION),
            HumanMessage(content=user_content),
        ]
        response = gemini_model.invoke(messages)
        response_text = (
            response.content if hasattr(response, "content") else str(response)
        )

        logger.info(
            "[Excel+Gemini] Gemini 응답 수신 (길이: %d자)",
            len(response_text),
        )
        print("[Excel+Gemini] Gemini 응답 수신 (길이: %d자)" % len(response_text))
    except Exception as e:
        logger.warning("[Excel+Gemini] Gemini 호출 실패: %s → 원본 값 유지", e)
        return {
            "fields": {k: {"value": v} for k, v in flat.items()},
            "corrections": [],
            "error": str(e),
        }

    parsed = _parse_llm_json_response(response_text)
    fields_out = parsed.get("fields") or {}
    corrections = parsed.get("corrections") or []

    # fields_out이 필드명 → {"value": "..."} 형태가 아니면 보정
    result_fields: Dict[str, Dict[str, str]] = {}
    for name, val in flat.items():
        result_fields[name] = {"value": val}
    for name, data in fields_out.items():
        if isinstance(data, dict) and "value" in data:
            result_fields[name] = {"value": str(data["value"])}
        elif isinstance(data, str):
            result_fields[name] = {"value": data}

    logger.info(
        "[Excel+Gemini] 보정 완료: corrections=%d건",
        len(corrections),
    )
    print("[Excel+Gemini] 보정 완료: corrections=%d건" % len(corrections))
    for i, c in enumerate(corrections[:10]):
        logger.info(
            "[Excel+Gemini] 보정 #%d: [%s] %r → %r (%s)",
            i + 1,
            c.get("field", ""),
            str(c.get("original", ""))[:60],
            str(c.get("corrected", ""))[:60],
            c.get("reason", ""),
        )
    if len(corrections) > 10:
        logger.info("[Excel+Gemini] ... 외 %d건 더 있음", len(corrections) - 10)

    return {
        "fields": result_fields,
        "corrections": corrections,
        "error": None,
    }


def run_excel_extract_and_correct(
    excel_path: str,
    field_definitions: Optional[Dict[str, Dict[str, Any]]] = None,
    sheet_name: Optional[str] = None,
    use_semantic_matching: bool = True,
    gemini_model: Optional[Any] = None,
) -> Dict[str, Any]:
    """Excel 추출 후 Gemini 보정까지 한 번에 실행.

    Args:
        excel_path: Excel 파일 경로
        field_definitions: 필드 정의 (None이면 표준 정의 사용)
        sheet_name: 시트 이름
        use_semantic_matching: 임베딩 매칭 사용 여부
        gemini_model: Gemini 채팅 모델 (None이면 보정 생략)

    Returns:
        {
            "raw_fields": 추출 직후 필드,
            "fields": 보정된 필드 (Gemini 미사용 시 raw_fields와 동일),
            "corrections": 보정 내역,
            "metadata": 시트 메타데이터,
            "used_gemini": bool,
            "error": str | None
        }
    """
    from domain.shared.ms_excel.field_extractor import (
        extract_fields_from_excel,
        get_standard_excel_field_definitions,
    )

    if field_definitions is None:
        field_definitions = get_standard_excel_field_definitions()

    logger.info("[Excel 파이프라인] 1단계: pandas 필드 추출 시작 file=%s", excel_path)
    print("[Excel 파이프라인] 1단계: pandas 필드 추출 시작", excel_path)

    result = extract_fields_from_excel(
        excel_path,
        field_definitions,
        sheet_name=sheet_name,
        use_semantic_matching=use_semantic_matching,
    )

    if result.get("error"):
        logger.error("[Excel 파이프라인] 추출 실패: %s", result["error"])
        return {
            "raw_fields": {},
            "fields": {},
            "corrections": [],
            "metadata": result.get("metadata", {}),
            "used_gemini": False,
            "error": result["error"],
        }

    raw_fields = result.get("fields") or {}
    # API 응답 형식에 맞게 value만 있는 딕셔너리로 평탄화
    flat_raw = {}
    for name, data in raw_fields.items():
        if isinstance(data, dict):
            flat_raw[name] = {"value": data.get("value", ""), **data}
        else:
            flat_raw[name] = {"value": str(data)}

    logger.info(
        "[Excel 파이프라인] 1단계 완료: 추출 필드 %d개, sheet=%s",
        len(raw_fields),
        result.get("metadata", {}).get("sheet_name", ""),
    )
    print("[Excel 파이프라인] 1단계 완료: 추출 필드 %d개" % len(raw_fields))

    if gemini_model is None or not getattr(gemini_model, "invoke", None):
        logger.info(
            "[Excel 파이프라인] 2단계: Gemini 미사용 → 보정 생략, 추출 결과 그대로 반환"
        )
        print("[Excel 파이프라인] 2단계: Gemini 미사용 → 보정 생략")
        corrected_flat = {k: {"value": v.get("value", "")} for k, v in flat_raw.items()}
        return {
            "raw_fields": raw_fields,
            "fields": corrected_flat,
            "corrections": [],
            "metadata": result.get("metadata", {}),
            "used_gemini": False,
            "error": None,
        }

    logger.info("[Excel 파이프라인] 2단계: Gemini 보정 시작")
    print("[Excel 파이프라인] 2단계: Gemini 보정 시작")

    gemini_result = run_gemini_correction(flat_raw, gemini_model)

    corrected_fields = gemini_result.get("fields") or {}
    corrections = gemini_result.get("corrections") or []

    logger.info(
        "[Excel 파이프라인] 완료: used_gemini=True, 보정 %d건, 필드 %d개",
        len(corrections),
        len(corrected_fields),
    )
    print("[Excel 파이프라인] 완료: used_gemini=True, 보정 %d건" % len(corrections))

    return {
        "raw_fields": raw_fields,
        "fields": corrected_fields,
        "corrections": corrections,
        "metadata": result.get("metadata", {}),
        "used_gemini": True,
        "error": gemini_result.get("error"),
    }
