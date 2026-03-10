"""KOICA 보고서 JSONL을 Exaone SFT(instruction/input/output) 형식으로 변환합니다.

입력: data/koica_reports/*.jsonl (source, page, text)
출력: data/koica_reports/koica_reports.sft.jsonl (id, instruction, input, output)

- instruction: 보고서 요약 지시
- input: 보고서명 + 페이지 + 본문 텍스트
- output: 추출적 요약(첫 문단/문장). 나중에 LLM으로 대체 가능

실행 (프로젝트 루트에서):
  python scripts/koica_reports_to_sft.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "data" / "koica_reports"
OUT_SFT = ROOT / "data" / "koica_reports" / "koica_reports.sft.jsonl"

# 요약용: 본문이 너무 길면 output은 앞부분 추출(최대 글자 수)
MAX_OUTPUT_CHARS = 800


def ensure_sentence_boundary(text: str) -> str:
    """문장이 중간에 잘리지 않도록 마지막 마침표 기준으로 잘라냅니다.

    - 가능한 한 '~합니다.', '~입니다.' 등 완결형 문장 끝에서 자르도록 시도
    - 그래도 없으면 일반적인 '다.'를 기준으로 자르되, 최소 한 문장 이상은 남김
    """
    text = (text or "").strip()
    if not text:
        return ""

    # 우선순위 높은 종결 표현들
    endings = ["입니다.", "합니다.", "됩니다.", "되었으며.", "되었습니다.", "되었습니다.", "되었습니다"]
    last_idx = -1
    for end in endings:
        idx = text.rfind(end)
        if idx != -1:
            last_idx = max(last_idx, idx + len(end))
    if last_idx != -1:
        return text[:last_idx].strip()

    # 일반적인 '다.' 기준으로 자르기
    idx = text.rfind("다.")
    if idx != -1 and idx > 10:  # 너무 앞이면 무시
        return text[: idx + len("다.")].strip()

    # 적절한 종결을 찾지 못하면 원문 그대로 반환
    return text.strip()


def extractive_summary(text: str, max_chars: int = MAX_OUTPUT_CHARS) -> str:
    """본문 앞부분을 추출적 요약으로 사용. (나중에 LLM 요약으로 교체 가능)"""
    text = (text or "").strip()
    if not text:
        return ""
    # [표] 이전까지 또는 첫 문단 위주
    if "[표]" in text:
        head = text.split("[표]")[0].strip()
        if len(head) <= max_chars:
            return head
    # 줄바꿈 기준 첫 2~3문단 또는 max_chars
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return text[:max_chars].strip()
    buf = []
    n = 0
    for line in lines:
        if n + len(line) + 1 > max_chars:
            break
        buf.append(line)
        n += len(line) + 1
    summary = "\n".join(buf) if buf else text[:max_chars].strip()
    return ensure_sentence_boundary(summary)


def doc_name_from_source(source: str) -> str:
    """파일명에서 확장자 제거한 보고서명."""
    return Path(source).stem if source else "보고서"


def main() -> int:
    if not REPORTS_DIR.exists():
        print(f"[오류] 폴더 없음: {REPORTS_DIR}")
        return 1

    jsonl_files = sorted(REPORTS_DIR.glob("*.jsonl"))
    # koica_reports.sft.jsonl 은 출력이므로 제외
    jsonl_files = [f for f in jsonl_files if f.name != "koica_reports.sft.jsonl"]
    if not jsonl_files:
        print(f"[오류] JSONL 파일 없음: {REPORTS_DIR}")
        return 1

    print(f"[1/2] 입력 파일: {[f.name for f in jsonl_files]}")

    sft_records = []
    rec_id = 1
    for jf in jsonl_files:
        with open(jf, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    continue
                source = raw.get("source", "")
                page = raw.get("page", 0)
                text = raw.get("text", "")
                if not text.strip():
                    continue
                doc_name = doc_name_from_source(source)
                instruction = (
                    "제공된 KOICA 평가보고서 본문을 분석하여, "
                    "사업의 성과, 한계점 및 향후 과제를 포함한 종합 요약본을 작성하세요. "
                    "OECD-DAC 6대 기준(적절성, 일관성, 효과성, 효율성, 지속가능성, 범분야 이슈)을 반드시 포함하고, "
                    "문장은 모두 '~합니다', '~입니다.'와 같이 완결형으로 끝내세요. "
                    "소제목과 주요 항목명은 **굵게** 표시하는 형식을 따르세요."
                )
                input_text = f"[{doc_name}] {page}페이지:\n\n{text}"
                output_text = extractive_summary(text)

                sft_records.append({
                    "id": rec_id,
                    "instruction": instruction,
                    "input": input_text,
                    "output": output_text,
                })
                rec_id += 1

    if not sft_records:
        print("[오류] 변환된 레코드가 없습니다.")
        return 1

    # 사용자가 직접 작성한 '깨끗한' Few-shot 예시(케냐 + 몽골)를 SFT에 포함
    fewshot_records = [
        {
            "id": 1,
            "instruction": (
                "제공된 KOICA 평가보고서의 주요 내용을 분석하여, "
                "사업의 성과, 한계점 및 향후 과제를 포함한 종합 요약본을 A4 한 페이지 분량으로 작성해줘. "
                "문장은 모두 '~합니다', '~입니다.'로 끝내고, 아래 예시와 같은 형식을 따르는 것이 중요해."
            ),
            "input": (
                "사업명: 케냐 청년취업 증진을 위한 직업기술교육훈련(GIZ) 지원 사업 (2021-2024). "
                "예산: 750만 불. 주요 활동: 산업수요 기반 TVET 커리큘럼 개편, 교원 역량 강화, "
                "8개 훈련기관 기자재 지원, 민관협력(PPP) 고용연계 모델 구축. "
                "평가 기준: OECD-DAC 6대 기준(적절성, 일관성, 효과성, 효율성, 지속가능성, 범분야 이슈)."
            ),
            "output": (
                "케냐 청년취업 증진을 위한 TVET 지원 사업 종료평가\n\n"
                "1. 행정 및 기본 정보\n"
                "사업명: 케냐 청년취업 증진을 위한 직업기술교육훈련(GIZ) 지원 사업 (2021-2024)입니다.\n"
                "작성 주관: KOICA 케냐 사무소 및 이우성 책임평가자(RISTI)입니다.\n"
                "평가 기간: 2025년 12월에 평가를 완료했습니다.\n\n"
                "2. 주요 평가 결과 (OECD-DAC 기준)\n"
                "적절성 (Relevance): 케냐 국가 개발 정책인 'Vision 2030' 및 청년 고용 전략과 매우 높은 정합성을 보였습니다.\n"
                "이해관계자의 수요를 적절히 반영하여 설계되었으나, 외부 환경 변화에 따른 유연한 대응 체계는 보완이 필요합니다.\n\n"
                "일관성 (Coherence): 독일 GIZ 등 타 공여기관의 사업과 조화를 이루어 중복 투자를 방지하고 원조 효과성을 극대화하였습니다.\n"
                "한국의 강점인 ICT 기술 교육을 체계적으로 융합하여 정책적 일관성을 유지하였습니다.\n\n"
                "효과성 (Effectiveness): 교육 이수생들의 취업률이 목표치 이상으로 향상되었으며, "
                "산업 맞춤형 커리큘럼 도입을 통해 실무 역량이 크게 개선되었습니다.\n"
                "다만, 일부 직종에서의 고용 질적 측면에 대한 추가 검증이 필요합니다.\n\n"
                "효율성 (Efficiency): 예산 집행과 기자재 조달이 계획된 일정 내에 신속하게 이루어졌습니다.\n"
                "전반적인 자금 운용의 효율은 높았으나, 향후 투입 대비 산출을 극대화하기 위한 정밀한 예산 가이드라인이 요구됩니다.\n\n"
                "지속가능성 (Sustainability): 케냐 정부의 높은 주인의식과 교육 기관의 운영 능력이 확인되었습니다.\n"
                "사업 종료 후에도 자체 예산을 통한 기자재 유지보수 및 교육 과정 지속 운영 가능성이 매우 높게 평가됩니다.\n\n"
                "3. 범분야 이슈 및 권고사항\n"
                "범분야 이슈 (Cross-cutting Issues): 여성 및 소외계층의 교육 참여율이 향상되었으나, "
                "특정 기술 분야에서의 젠더 불균형 해소를 위한 전략적 접근이 지속적으로 필요합니다.\n\n"
                "제언 사항: 졸업생들의 장기적인 커리어 트래킹을 위한 사후 관리 시스템(ALUMNI) 구축을 권고하며, "
                "정기적인 성과 모니터링 데이터의 표준화가 시급합니다."
            ),
        },
        {
            "id": 2,
            "instruction": (
                "제공된 KOICA 평가보고서의 주요 내용을 분석하여, "
                "사업의 성과, 한계점 및 향후 과제를 포함한 종합 요약본을 A4 한 페이지 분량으로 작성해줘. "
                "문장은 모두 '~합니다', '~입니다.'로 끝내고, 아래 예시와 같은 형식을 따르는 것이 중요해."
            ),
            "input": (
                "사업명: 몽골 직업기술교육훈련(TVET) 시스템 개선사업 (2019-2022). "
                "예산: 450만 불. 핵심 내용: TVET 법·제도 정비, 평가·인증 시스템 구축, 교원 역량 강화, "
                "산업계 연계 강화. 평가 기준: OECD-DAC 6대 기준(적절성, 일관성, 효과성, 효율성, "
                "지속가능성, 범분야 이슈)."
            ),
            "output": (
                "### [요약본] 몽골 직업기술교육훈련(TVET) 시스템 개선사업 종료평가\n\n"
                "1. 행정 및 기본 정보\n"
                "사업명: 몽골 직업기술교육훈련(TVET) 시스템 개선사업 (2019-2022)입니다.\n"
                "예산: 총 450만 불입니다.\n"
                "책임 평가자: 이우성 책임평가자(RISTI)입니다.\n"
                "평가 완료일: 2025년 11월 12일입니다.\n\n"
                "2. 주요 평가 결과 (OECD-DAC 기준)\n"
                "적절성 (Relevance): 몽골 정부의 'Vision 2050' 및 교육 섹터 중기 발전계획과 일치하여 매우 높은 타당성을 보였습니다.\n"
                "특히 국가 차원의 TVET 법적 프레임워크 구축 지원은 시의적절한 투입으로 평가됩니다.\n\n"
                "일관성 (Coherence): 타 공여기관과의 중복을 피하고 몽골 교육과학부와의 긴밀한 협력을 통해 정책적 일관성을 확보하였습니다.\n\n"
                "효과성 (Effectiveness): TVET 평가 인증 시스템 구축 및 교원 역량 강화를 통해 교육의 질적 수준을 상향 평준화하는 성과를 거두었습니다.\n"
                "다만, 산업계와의 실질적인 고용 연계 부분에서는 고도화가 필요합니다.\n\n"
                "효율성 (Efficiency): 코로나19 팬데믹 상황에도 불구하고 비대면 교육 시스템 전환 등을 통해 사업 기간 내 예산과 인력이 효율적으로 투입되었습니다.\n\n"
                "지속가능성 (Sustainability): 2023년 개정된 TVET 법안에 본 사업의 성과가 반영됨에 따라, 제도적 차원의 지속 가능성이 매우 견고하게 확보되었습니다.\n\n"
                "범분야 이슈 (Cross-cutting Issues): 교육 수혜자의 성별 분리 데이터를 관리하고 여성 교원의 역량 강화 기회를 확대하여 젠더 주류화 가치를 실현하였습니다.\n\n"
                "3. 주요 성과 및 제언\n"
                "주요 성과: 몽골 국가 직업자격체계(NQF)와 연계된 평가 시스템을 구축하여 교육 표준화의 기반을 마련했습니다.\n"
                "제언 사항: 구축된 시스템이 현장에서 지속적으로 작동하기 위해 운영 인력에 대한 심화 교육이 필요하며, "
                "산업 수요를 실시간으로 반영하는 피드백 루프를 강화할 것을 권고합니다."
            ),
        },
    ]

    # 기존 페이지 단위 SFT 레코드의 id를 Few-shot 예시 뒤에 이어지도록 조정
    for i, rec in enumerate(sft_records, start=len(fewshot_records) + 1):
        rec["id"] = i

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    all_records = fewshot_records + sft_records

    with open(OUT_SFT, "w", encoding="utf-8") as f:
        for rec in all_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[2/2] SFT 저장 완료: {OUT_SFT} ({len(all_records)}건, Few-shot {len(fewshot_records)}건 포함)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
