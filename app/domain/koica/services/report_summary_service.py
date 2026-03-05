"""KOICA 평가보고서 PDF 요약 서비스.

PDF 바이트를 받아 텍스트를 추출하고, 훈련된 Exaone(LoRA)으로 요약문을 생성합니다.
모델이 없으면 추출적 요약으로 대체합니다.
"""

from __future__ import annotations

import io
import threading
from pathlib import Path
from typing import Any, Tuple

# 요약 본문 최대 글자 수 (추출적 요약 폴백용)
MAX_SUMMARY_CHARS = 2000

# 훈련 시 사용한 instruction (SFT와 동일)
KOICA_REPORT_INSTRUCTION = (
    "제공된 KOICA 평가보고서의 주요 내용을 분석하여, "
    "사업의 성과, 한계점 및 향후 과제를 포함한 종합 요약본을 A4 한 페이지 분량으로 작성해줘. "
    "아래 예시와 같은 형식을 따르고, 문장은 모두 '~합니다', '~입니다.'와 같이 완결형으로 끝내줘."
)

# 프롬프트 Input 최대 토큰 수 (instruction + Response 헤더 공간 확보)
MAX_INPUT_TOKENS = 700
MAX_NEW_TOKENS = 1024

# Lazy-loaded 모델 (첫 요청 시 로드)
_model_lock = threading.Lock()
_exaone_model: Any = None
_exaone_tokenizer: Any = None
_exaone_available = False


def _get_project_root() -> Path:
    """프로젝트 루트 경로 반환 (app/domain/koica/services → 루트)."""
    return Path(__file__).resolve().parents[4]


def _ensure_sentence_boundary(text: str) -> str:
    """문장이 중간에 잘리지 않도록 마지막 완결형 문장 끝에서 자릅니다."""
    text = (text or "").strip()
    if not text:
        return ""
    for end in ["입니다.", "합니다.", "됩니다.", "되었습니다.", "다."]:
        idx = text.rfind(end)
        if idx != -1 and idx > 10:
            return text[: idx + len(end)].strip()
    return text.strip()


def _extractive_summary(text: str, max_chars: int = MAX_SUMMARY_CHARS) -> str:
    """본문 앞부분을 추출적 요약으로 사용합니다. Exaone 미사용 시 폴백."""
    text = (text or "").strip()
    if not text:
        return ""
    if "[표]" in text:
        head = text.split("[표]")[0].strip()
        if len(head) <= max_chars:
            return _ensure_sentence_boundary(head)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return _ensure_sentence_boundary(text[:max_chars])
    buf, n = [], 0
    for line in lines:
        if n + len(line) + 1 > max_chars:
            break
        buf.append(line)
        n += len(line) + 1
    summary = "\n".join(buf) if buf else text[:max_chars]
    return _ensure_sentence_boundary(summary)


def _extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """PDF 바이트에서 페이지별 텍스트를 추출해 하나의 문자열로 반환합니다."""
    import pdfplumber

    parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                parts.append(text.strip())
            tables = page.extract_tables() or []
            for t in tables:
                if not t:
                    continue
                for row in t:
                    cells = [str(c).strip() if c else "" for c in row]
                    parts.append(" | ".join(cells))
    return "\n\n".join(parts)


def _load_exaone_report_model() -> Tuple[Any, Any]:
    """훈련된 Exaone(베이스 + exaone-koica-reports LoRA)을 로드합니다.

    Returns:
        (model, tokenizer). 어댑터가 없거나 로드 실패 시 (None, None).
    """
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel, prepare_model_for_kbit_training

    root = _get_project_root()
    base_path = root / "models" / "exaone-2.4b"
    adapter_path = root / "models" / "exaone-koica-reports"

    if not base_path.exists():
        return None, None
    if not adapter_path.exists() or not (adapter_path / "adapter_config.json").exists():
        return None, None

    try:
        tokenizer = AutoTokenizer.from_pretrained(
            str(base_path),
            trust_remote_code=True,
            padding_side="right",
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
            tokenizer.pad_token_id = tokenizer.eos_token_id

        bnb_config = None
        if torch.cuda.is_available():
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )

        model = AutoModelForCausalLM.from_pretrained(
            str(base_path),
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )
        model = prepare_model_for_kbit_training(model)
        model = PeftModel.from_pretrained(model, str(adapter_path), device_map="auto")
        model.eval()

        return model, tokenizer
    except Exception:
        return None, None


def _ensure_exaone_loaded() -> bool:
    """필요 시 Exaone 모델을 한 번만 로드하고, 사용 가능 여부를 반환합니다."""
    global _exaone_model, _exaone_tokenizer, _exaone_available
    with _model_lock:
        if _exaone_model is not None and _exaone_tokenizer is not None:
            return _exaone_available
        if _exaone_model is None and _exaone_tokenizer is None:
            _exaone_model, _exaone_tokenizer = _load_exaone_report_model()
            _exaone_available = _exaone_model is not None and _exaone_tokenizer is not None
    return _exaone_available


def _generate_summary_with_exaone(report_text: str) -> str:
    """훈련된 Exaone으로 보고서 본문에서 요약문을 생성합니다.

    훈련 시 사용한 프롬프트 형식: ### Instruction: / ### Input: / ### Response:
    """
    import torch

    if not _exaone_tokenizer or not _exaone_model:
        return ""

    # Input 토큰 수 제한 (instruction + "### Response:\n" 공간 확보)
    input_ids = _exaone_tokenizer.encode(
        report_text,
        add_special_tokens=False,
        truncation=True,
        max_length=MAX_INPUT_TOKENS,
    )
    truncated_input = _exaone_tokenizer.decode(input_ids, skip_special_tokens=True)

    prompt = (
        f"### Instruction:\n{KOICA_REPORT_INSTRUCTION}\n\n"
        f"### Input:\n[보고서 본문]\n\n{truncated_input}\n\n"
        "### Response:\n"
    )

    inputs = _exaone_tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=2048,
        return_token_type_ids=False,
    )
    if "token_type_ids" in inputs:
        inputs.pop("token_type_ids")

    if torch.cuda.is_available():
        inputs = {k: v.to("cuda") for k, v in inputs.items()}

    with torch.no_grad():
        outputs = _exaone_model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=0.3,
            top_p=0.9,
            do_sample=True,
            pad_token_id=_exaone_tokenizer.pad_token_id,
            eos_token_id=_exaone_tokenizer.eos_token_id,
        )

    generated = _exaone_tokenizer.decode(outputs[0], skip_special_tokens=True)

    # "### Response:\n" 이후만 반환
    if "### Response:" in generated:
        response = generated.split("### Response:")[-1].strip()
    else:
        response = generated[len(prompt) :].strip()

    return response.strip()


def summarize_pdf_bytes(pdf_bytes: bytes) -> str:
    """PDF 바이트를 요약합니다.

    훈련된 Exaone(LoRA, models/exaone-koica-reports)이 있으면 해당 모델로 생성 요약을 반환하고,
    없으면 PDF 텍스트 추출 후 추출적 요약으로 대체합니다.

    Args:
        pdf_bytes: PDF 파일 원시 바이트.

    Returns:
        요약문 문자열.

    Raises:
        FileNotFoundError: (현재는 사용하지 않음. 추출적 폴백으로 대체)
        Exception: PDF 추출 실패 등 기타 오류.
    """
    if not pdf_bytes:
        return ""

    full_text = _extract_text_from_pdf_bytes(pdf_bytes)
    if not full_text.strip():
        return "(PDF에서 추출된 텍스트가 없습니다.)"

    if _ensure_exaone_loaded():
        try:
            return _generate_summary_with_exaone(full_text) or _extractive_summary(full_text)
        except Exception:
            return _extractive_summary(full_text)

    return _extractive_summary(full_text)
