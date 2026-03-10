# -*- coding: utf-8 -*-
"""JSONL 파일을 SFT(Supervised Fine-Tuning) 형식으로 변환하는 모듈.

기존 convert_to_jsonl.py에서 생성한 JSONL 파일을 읽어서
더 구조화된 SFT 형식으로 변환합니다.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    """JSONL을 한 줄씩 읽습니다. 깨진 라인은 건너뜁니다.

    Args:
        path: 읽을 JSONL 파일 경로

    Yields:
        각 행의 JSON 객체 딕셔너리
    """
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # 운영에서는 별도 로그 파일로 남기는 것이 좋습니다.
                print(f"경고: {path.name}의 {lineno}번째 줄을 파싱할 수 없습니다. 건너뜁니다.")
                continue


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    """JSONL 파일로 저장합니다.

    Args:
        path: 저장할 파일 경로
        rows: 저장할 딕셔너리들의 반복 가능 객체
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_attachments(raw: str) -> List[str]:
    """첨부파일 문자열에서 파일명 목록을 추출합니다.

    "Offer.docx (16.4 K), Offer - contextual advertising.docx (15.8 K)"
    -> ["Offer.docx", "Offer - contextual advertising.docx"]

    Args:
        raw: 첨부파일 원본 문자열

    Returns:
        파일명 목록
    """
    if not raw:
        return []
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    names: List[str] = []
    for p in parts:
        # 뒤의 "(16.4 K)" 같은 용량 표기를 제거
        p = re.sub(r"\s*\([^)]*\)\s*$", "", p).strip()
        if p:
            names.append(p)
    return names


def parse_input_text(input_text: str) -> Dict[str, Any]:
    """기존 JSONL의 input 텍스트를 파싱하여 구조화된 딕셔너리로 변환합니다.

    Args:
        input_text: "수신일자: ...\n수신시간: ...\n제목: ...\n첨부: ..." 형식의 문자열

    Returns:
        구조화된 딕셔너리
    """
    result = {
        "received_date": "",
        "received_time": "",
        "subject": "",
        "attachments": [],
        "attachments_raw": "",
    }
    
    lines = input_text.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("수신일자:"):
            result["received_date"] = line.replace("수신일자:", "").strip()
        elif line.startswith("수신시간:"):
            result["received_time"] = line.replace("수신시간:", "").strip()
        elif line.startswith("제목:"):
            result["subject"] = line.replace("제목:", "").strip()
        elif line.startswith("첨부:"):
            attach_raw = line.replace("첨부:", "").strip()
            result["attachments_raw"] = attach_raw
            result["attachments"] = parse_attachments(attach_raw)
    
    # received_at 생성
    if result["received_date"] and result["received_time"]:
        result["received_at"] = f"{result['received_date']} {result['received_time']}".strip()
    else:
        result["received_at"] = result.get("received_date", "") or result.get("received_time", "")
    
    return result


def normalize_from_jsonl(row: Dict[str, Any]) -> Dict[str, Any]:
    """기존 JSONL 형식의 row를 정규화한 clean 레코드로 변환합니다.

    Args:
        row: 기존 JSONL 행 데이터 (instruction, input, output 포함)

    Returns:
        정규화된 딕셔너리
    """
    input_text = row.get("input", "")
    output_text = row.get("output", "")
    
    # input 텍스트 파싱
    parsed = parse_input_text(input_text)
    
    # output에서 메일 타입 추출 (스팸/정상)
    mail_type = "스팸"  # 기본값
    if "정상" in output_text or "정상 메일" in output_text:
        mail_type = "정상"
    elif "스팸" in output_text:
        mail_type = "스팸"
    
    return {
        "received_date": parsed.get("received_date", ""),
        "received_time": parsed.get("received_time", ""),
        "received_at": parsed.get("received_at", ""),
        "subject": parsed.get("subject", ""),
        "attachments": parsed.get("attachments", []),
        "attachments_raw": parsed.get("attachments_raw", ""),
        "mail_type": mail_type,
        "original_output": output_text,  # 원본 보존
    }


def dedup_key(clean: Dict[str, Any], mode: str = "subject+attachments") -> Tuple:
    """중복 제거 기준을 선택합니다.

    Args:
        clean: 정규화된 데이터 딕셔너리
        mode: 중복 제거 모드
            - "subject+attachments": 제목과 첨부가 같으면 중복
            - "datetime+subject+attachments": 시간까지 포함(더 엄격)

    Returns:
        중복 체크용 튜플 키
    """
    if mode == "datetime+subject+attachments":
        return (
            clean.get("received_at", ""),
            clean.get("subject", ""),
            tuple(clean.get("attachments", [])),
        )
    return (
        clean.get("subject", ""),
        tuple(clean.get("attachments", [])),
    )


def rule_label(clean: Dict[str, Any]) -> Tuple[str, str, float]:
    """rule-based labeling을 수행합니다.

    Args:
        clean: 정규화된 데이터 딕셔너리

    Returns:
        (action, reason, confidence) 튜플
        - action: BLOCK/ALLOW
        - reason: 짧은 근거
        - confidence: 0~1 사이의 신뢰도
    """
    subject = (clean.get("subject") or "").lower()
    attachments = clean.get("attachments") or []
    mail_type = (clean.get("mail_type") or "").strip()
    
    # 1) 원천 데이터에 '스팸' 라벨이 있으면 기본적으로 BLOCK
    if mail_type == "스팸":
        base_action = "BLOCK"
    elif mail_type == "정상":
        base_action = "ALLOW"
    else:
        # 라벨이 없으면 rule로 추정(초기엔 보수적으로)
        base_action = "BLOCK"
    
    # 2) reason / confidence 규칙
    reasons = []
    score = 0.0
    
    if "(광고)" in (clean.get("subject") or ""):
        reasons.append("제목에 (광고) 표기가 포함됨")
        score += 0.5
    
    # 흔한 스팸 키워드 예시(필요시 확장)
    spam_keywords = [
        "offer", "보험", "임플란트", "치아보험", "이벤트", "할인",
        "진단금", "간병", "promotion", "urgent", "winner", "prize"
    ]
    if any(k.lower() in subject for k in [kw.lower() for kw in spam_keywords]):
        reasons.append("스팸/광고성 키워드 패턴이 포함됨")
        score += 0.35
    
    if attachments:
        # 의심스러운 첨부 파일 확장자
        suspicious_exts = [".exe", ".bat", ".scr", ".com", ".pif"]
        if any(any(ext in att.lower() for ext in suspicious_exts) for att in attachments):
            reasons.append("의심스러운 첨부파일이 포함됨")
            score += 0.4
        else:
            reasons.append("첨부파일이 포함됨")
            score += 0.2
    
    if not reasons:
        reasons.append("메타데이터만으로는 뚜렷한 단서가 적음")
        score += 0.1
    
    # confidence는 0.85~0.99 사이로 클램프(초기 모델 학습 안정 목적)
    confidence = min(0.99, max(0.85, 0.80 + score))
    
    # action은 base_action을 따르되, 이유가 약하면 confidence만 낮게
    action = base_action
    reason = " / ".join(reasons)
    
    return action, reason, float(f"{confidence:.2f}")


def to_sft(clean: Dict[str, Any]) -> Dict[str, Any]:
    """정규화된 데이터를 SFT 형식으로 변환합니다.

    Args:
        clean: 정규화된 데이터 딕셔너리

    Returns:
        SFT 형식의 딕셔너리
    """
    action, reason, confidence = rule_label(clean)
    
    # 입력 텍스트 구성 (더 구조화된 형식)
    input_parts = []
    if clean.get("subject"):
        input_parts.append(f"제목: {clean['subject']}")
    if clean.get("attachments"):
        input_parts.append(f"첨부파일: {', '.join(clean['attachments'])}")
    if clean.get("received_at"):
        input_parts.append(f"수신일시: {clean['received_at']}")
    
    input_text = "\n".join(input_parts) if input_parts else "메타데이터 없음"
    
    # 출력 JSON 형식
    output_json = {
        "action": action,
        "reason": reason,
        "confidence": confidence,
    }
    
    return {
        "instruction": "다음 이메일 메타데이터를 분석하여 스팸 여부를 판정하고 JSON 형식으로만 답하세요.",
        "input": input_text,
        "output": json.dumps(output_json, ensure_ascii=False),
    }


def convert_jsonl_to_sft(
    input_jsonl_path: Path,
    output_sft_path: Path,
    output_dedup_path: Optional[Path] = None,
    output_clean_path: Optional[Path] = None,
    dedup_mode: str = "subject+attachments",
) -> Tuple[int, int, int]:
    """JSONL 파일을 SFT 형식으로 변환합니다.

    Args:
        input_jsonl_path: 입력 JSONL 파일 경로
        output_sft_path: 출력 SFT JSONL 파일 경로
        output_dedup_path: (선택) 중복 제거된 JSONL 파일 경로
        output_clean_path: (선택) 정규화된 JSONL 파일 경로
        dedup_mode: 중복 제거 모드

    Returns:
        (sft_count, dedup_count, clean_count) 튜플
    """
    seen = set()
    dedup_rows = []
    clean_rows = []
    sft_rows = []
    
    total_count = 0
    for row in iter_jsonl(input_jsonl_path):
        total_count += 1
        if total_count % 10000 == 0:
            print(f"처리 중: {total_count}개 레코드...")
        
        clean = normalize_from_jsonl(row)
        key = dedup_key(clean, mode=dedup_mode)
        
        if key in seen:
            continue
        seen.add(key)
        
        # dedup 단계 산출물(원본 형태 유지가 필요하면 row를, 정규화 형태면 clean을 저장)
        if output_dedup_path is not None:
            dedup_rows.append(row)
        
        # clean 단계 산출물
        if output_clean_path is not None:
            clean_rows.append(clean)
        
        # sft 산출물
        sft_rows.append(to_sft(clean))
    
    # 저장
    print(f"SFT 파일 저장 중: {output_sft_path}")
    write_jsonl(output_sft_path, sft_rows)
    
    if output_dedup_path is not None:
        print(f"중복 제거 파일 저장 중: {output_dedup_path}")
        write_jsonl(output_dedup_path, dedup_rows)
    
    if output_clean_path is not None:
        print(f"정규화 파일 저장 중: {output_clean_path}")
        write_jsonl(output_clean_path, clean_rows)
    
    return len(sft_rows), len(dedup_rows), len(clean_rows)


if __name__ == "__main__":
    # 프로젝트 루트 경로 (이 파일이 app/service/에 있으므로 2단계 위로)
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data"
    
    if not data_dir.exists():
        print(f"오류: data 디렉토리를 찾을 수 없습니다: {data_dir}")
        sys.exit(1)
    
    # JSONL 파일 찾기 (기존 convert_to_jsonl.py에서 생성한 파일)
    jsonl_files = list(data_dir.glob("*.jsonl"))
    # .sft.jsonl 파일은 제외
    jsonl_files = [f for f in jsonl_files if not f.name.endswith(".sft.jsonl")]
    
    if not jsonl_files:
        print(f"오류: '{data_dir}' 디렉토리에서 JSONL 파일을 찾을 수 없습니다.")
        sys.exit(1)
    
    # 모든 JSONL 파일 변환
    print(f"총 {len(jsonl_files)}개의 JSONL 파일을 찾았습니다.\n")
    
    for jsonl_file in jsonl_files:
        # 출력 파일명 생성 (확장자만 변경)
        sft_file = jsonl_file.with_suffix(".sft.jsonl")
        print(f"{'='*60}")
        print(f"변환 중: {jsonl_file.name} -> {sft_file.name}")
        print(f"{'='*60}")
        
        try:
            sft_count, dedup_count, clean_count = convert_jsonl_to_sft(
                input_jsonl_path=jsonl_file,
                output_sft_path=sft_file,
                dedup_mode="subject+attachments",
            )
            print(f"\n[성공] SFT 변환 완료:")
            print(f"  - SFT 레코드: {sft_count:,}개")
            print(f"  - 중복 제거: {len(jsonl_file.read_text(encoding='utf-8').splitlines()) - sft_count:,}개")
            print(f"  - 출력 파일: {sft_file.name}\n")
        except Exception as e:
            print(f"[오류] {jsonl_file.name} 변환 실패: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    print("\n모든 변환 작업이 완료되었습니다.")
