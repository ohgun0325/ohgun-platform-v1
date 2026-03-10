"""KOICA 데이터를 JSONL 형식으로 변환하는 스크립트.

data/koica_data 폴더의 CSV 파일들을 국제개발협력 도메인에 맞는 Instruction 형식으로 변환합니다.
"""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional


def load_csv_data(csv_path: Path) -> List[Dict[str, Any]]:
    """CSV 파일을 로드합니다.
    
    Args:
        csv_path: CSV 파일 경로
        
    Returns:
        CSV 데이터를 딕셔너리 리스트로 반환
    """
    data = []
    # 여러 인코딩 시도
    encodings = ['utf-8', 'cp949', 'euc-kr']
    
    for encoding in encodings:
        try:
            with open(csv_path, 'r', encoding=encoding, newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 빈 행 제거
                    if any(row.values()):
                        data.append(dict(row))
            break
        except UnicodeDecodeError:
            continue
    
    return data


def convert_oda_glossary(row: Dict[str, Any]) -> Dict[str, str]:
    """ODA 용어사전 데이터를 Instruction 형식으로 변환.
    
    Args:
        row: CSV 행 데이터
        
    Returns:
        Instruction 형식의 딕셔너리
    """
    약어 = row.get('약어', '').strip()
    영문명 = row.get('영문명', '').strip()
    한글명 = row.get('한글명', '').strip()
    설명 = row.get('설명', '').strip()
    
    if not 한글명 and not 영문명:
        return None
    
    # 입력 구성
    input_parts = []
    if 약어:
        input_parts.append(f"약어: {약어}")
    if 영문명:
        input_parts.append(f"영문명: {영문명}")
    if 한글명:
        input_parts.append(f"한글명: {한글명}")
    
    input_text = "\n".join(input_parts) if input_parts else f"{한글명 or 영문명}"
    
    # 출력 구성
    output_parts = []
    if 한글명:
        output_parts.append(f"한글명: {한글명}")
    if 영문명:
        output_parts.append(f"영문명: {영문명}")
    if 약어:
        output_parts.append(f"약어: {약어}")
    if 설명:
        output_parts.append(f"\n설명:\n{설명}")
    
    output = "\n".join(output_parts)
    
    return {
        "instruction": "다음 ODA 용어에 대한 정보를 제공하세요.",
        "input": input_text,
        "output": output
    }


def convert_project_data(row: Dict[str, Any]) -> Dict[str, str]:
    """사업 데이터를 Instruction 형식으로 변환.
    
    Args:
        row: CSV 행 데이터
        
    Returns:
        Instruction 형식의 딕셔너리
    """
    사업명_국문 = row.get('사업명_국문', '').strip()
    사업명_영문 = row.get('사업명_영문', '').strip()
    대상국가 = row.get('대상국가', '').strip()
    사업분야 = row.get('사업분야', '').strip()
    사업형태 = row.get('사업형태', '').strip()
    사업요약 = row.get('사업요약', '').strip()
    사업목표 = row.get('사업목표', '').strip()
    사업목적 = row.get('사업목적', '').strip()
    
    if not 사업명_국문 and not 사업명_영문:
        return None
    
    # 입력 구성
    input_parts = []
    if 사업명_국문:
        input_parts.append(f"사업명: {사업명_국문}")
    if 대상국가:
        input_parts.append(f"대상국가: {대상국가}")
    if 사업분야:
        input_parts.append(f"사업분야: {사업분야}")
    if 사업형태:
        input_parts.append(f"사업형태: {사업형태}")
    
    input_text = "\n".join(input_parts) if input_parts else 사업명_국문 or 사업명_영문
    
    # 출력 구성
    output_parts = []
    if 사업명_국문:
        output_parts.append(f"사업명: {사업명_국문}")
    if 사업명_영문:
        output_parts.append(f"영문명: {사업명_영문}")
    if 대상국가:
        output_parts.append(f"대상국가: {대상국가}")
    if 사업분야:
        output_parts.append(f"사업분야: {사업분야}")
    if 사업형태:
        output_parts.append(f"사업형태: {사업형태}")
    if 사업요약:
        output_parts.append(f"\n사업요약:\n{사업요약}")
    if 사업목표:
        output_parts.append(f"\n사업목표:\n{사업목표}")
    if 사업목적:
        output_parts.append(f"\n사업목적:\n{사업목적}")
    
    output = "\n".join(output_parts)
    
    return {
        "instruction": "다음 국제개발협력 사업에 대한 정보를 제공하세요.",
        "input": input_text,
        "output": output
    }


def convert_qa_data(row: Dict[str, Any]) -> Dict[str, str]:
    """질의응답 데이터를 Instruction 형식으로 변환.
    
    Args:
        row: CSV 행 데이터
        
    Returns:
        Instruction 형식의 딕셔너리
    """
    질문 = row.get('질문', '').strip()
    답변 = row.get('답변', '').strip()
    출처 = row.get('출처', '').strip()
    
    if not 질문 or not 답변:
        return None
    
    input_text = 질문
    
    output_parts = [답변]
    if 출처:
        output_parts.append(f"\n출처: {출처}")
    
    output = "\n".join(output_parts)
    
    return {
        "instruction": "다음 질문에 대해 국제개발협력 조달계약 규정에 따라 답변하세요.",
        "input": input_text,
        "output": output
    }


def convert_ngo_guide_data(row: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """NGO 길라잡이 데이터를 Instruction 형식으로 변환.
    CSV 컬럼: 번호, 국가, 발행연도, 주요내용, 링크
    """
    국가 = row.get('국가', '').strip()
    발행연도 = row.get('발행연도', '').strip()
    주요내용 = row.get('주요내용', '').strip()
    링크 = row.get('링크', '').strip()

    if not 국가 and not 주요내용:
        return None

    input_text = f"국가: {국가}" if 국가 else "NGO 길라잡이 정보"
    if 발행연도:
        input_text += f"\n발행연도: {발행연도}"

    output_parts = []
    if 발행연도:
        output_parts.append(f"발행연도: {발행연도}")
    if 주요내용:
        output_parts.append(f"주요내용: {주요내용}")
    if 링크:
        output_parts.append(f"링크: {링크}")
    output = "\n".join(output_parts) if output_parts else "정보 없음"

    return {
        "instruction": "다음 국가의 NGO 길라잡이 정보를 제공하세요.",
        "input": input_text,
        "output": output,
    }


def _col(row: Dict[str, Any], name: str) -> str:
    """BOM 등으로 키가 깨진 경우를 대비해 컬럼값 조회."""
    for k in row:
        if k.replace("\ufeff", "").strip() == name:
            return (row.get(k) or "").strip()
    return (row.get(name) or "").strip()


def convert_press_release_data(row: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """개발협력 보도자료 데이터를 Instruction 형식으로 변환.
    CSV 컬럼: 제목, 자료형태, 배포날짜, 담당부서, 링크
    """
    제목 = _col(row, "제목")
    자료형태 = _col(row, "자료형태")
    배포날짜 = _col(row, "배포날짜")
    담당부서 = _col(row, "담당부서")
    링크 = _col(row, "링크")

    if not 제목:
        return None

    input_parts = [f"제목: {제목}"]
    if 배포날짜:
        input_parts.append(f"배포날짜: {배포날짜}")
    input_text = "\n".join(input_parts)

    output_parts = [f"제목: {제목}"]
    if 자료형태:
        output_parts.append(f"자료형태: {자료형태}")
    if 배포날짜:
        output_parts.append(f"배포날짜: {배포날짜}")
    if 담당부서:
        output_parts.append(f"담당부서: {담당부서}")
    if 링크:
        output_parts.append(f"링크: {링크}")
    output = "\n".join(output_parts)

    return {
        "instruction": "다음 개발협력 보도자료에 대한 정보를 제공하세요.",
        "input": input_text,
        "output": output,
    }


def convert_country_trend_data(row: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """국별 개발협력동향 데이터를 Instruction 형식으로 변환.
    CSV 컬럼: 국가, 구분, 분야, 제목, 본문1, 본문2, 본문3, 영문제목, 영문본문1, 영문본문2, 영문본문3, 출처, 링크, 날짜
    """
    국가 = _col(row, "국가")
    구분 = _col(row, "구분")
    분야 = _col(row, "분야")
    제목 = _col(row, "제목")
    본문1 = _col(row, "본문1")
    본문2 = _col(row, "본문2")
    본문3 = _col(row, "본문3")
    출처 = _col(row, "출처")
    링크 = _col(row, "링크")
    날짜 = _col(row, "날짜")

    # 제목·본문1·영문제목 중 하나는 있어야 함
    영문제목 = _col(row, "영문제목")
    if not 제목 and not 본문1 and not 영문제목:
        return None

    # input: 질의 형태 (국가, 구분, 분야, 제목)
    input_parts = []
    if 국가:
        input_parts.append(f"국가: {국가}")
    if 구분:
        input_parts.append(f"구분: {구분}")
    if 분야:
        input_parts.append(f"분야: {분야}")
    input_parts.append(f"제목: {제목 or 영문제목 or '(제목 없음)'}")
    input_text = "\n".join(input_parts)

    # output: 제목, 본문1~3, 출처, 링크, 날짜
    output_parts = [f"제목: {제목 or 영문제목 or '(제목 없음)'}"]
    if 본문1:
        output_parts.append(f"\n본문:\n{본문1}")
    if 본문2:
        output_parts.append(본문2)
    if 본문3:
        output_parts.append(본문3)
    if 출처:
        output_parts.append(f"\n출처: {출처}")
    if 링크:
        output_parts.append(f"링크: {링크}")
    if 날짜:
        output_parts.append(f"날짜: {날짜}")
    output = "\n".join(output_parts)

    return {
        "instruction": "다음 국별 개발협력 동향에 대한 정보를 제공하세요.",
        "input": input_text,
        "output": output,
    }


def convert_sdgs_project_data(row: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """사업별 지속가능개발목표(SDGs) 연계 현황 데이터를 Instruction 형식으로 변환.
    CSV 컬럼: 사업연도, 사업유형명, 사업명(한글), 사업명(영문), 국가명, 지역명,
              전체사업시작일자, 전체사업종료일자, 지원액(원화), 지원액(달러), SDGs 필드
    """
    사업연도 = _col(row, "사업연도")
    사업유형명 = _col(row, "사업유형명")
    사업명_한글 = _col(row, "사업명(한글)")
    사업명_영문 = _col(row, "사업명(영문)")
    국가명 = _col(row, "국가명")
    지역명 = _col(row, "지역명")
    시작일 = _col(row, "전체사업시작일자")
    종료일 = _col(row, "전체사업종료일자")
    지원액_원 = _col(row, "지원액(원화)")
    지원액_달러 = _col(row, "지원액(달러)")
    sdgs = _col(row, "SDGs 필드")

    if not 사업명_한글 and not 사업명_영문:
        return None

    # input: 사업연도, 국가명, 사업명
    input_parts = []
    if 사업연도:
        input_parts.append(f"사업연도: {사업연도}")
    if 국가명:
        input_parts.append(f"국가명: {국가명}")
    input_parts.append(f"사업명: {사업명_한글 or 사업명_영문}")
    input_text = "\n".join(input_parts)

    # output: 사업명, 국가, 지역, 유형, 기간, 지원액, SDGs
    output_parts = [f"사업명: {사업명_한글 or 사업명_영문}"]
    if 사업명_한글 and 사업명_영문:
        output_parts.append(f"영문명: {사업명_영문}")
    if 국가명:
        output_parts.append(f"국가명: {국가명}")
    if 지역명:
        output_parts.append(f"지역명: {지역명}")
    if 사업유형명:
        output_parts.append(f"사업유형: {사업유형명}")
    if 시작일 or 종료일:
        output_parts.append(f"사업기간: {시작일 or '-'} ~ {종료일 or '-'}")
    if 지원액_원:
        try:
            v = 지원액_원.replace(",", "").strip()
            if v.replace(".", "").isdigit():
                fv = float(v)
                output_parts.append(f"지원액(원화): {fv:,.0f}원" if fv >= 1 else f"지원액(원화): {지원액_원}원")
            else:
                output_parts.append(f"지원액(원화): {지원액_원}원")
        except Exception:
            output_parts.append(f"지원액(원화): {지원액_원}원")
    if 지원액_달러:
        try:
            v = 지원액_달러.replace(",", "").strip()
            if v.replace(".", "").isdigit():
                fv = float(v)
                output_parts.append(f"지원액(달러): {fv:,.0f}달러" if fv >= 1 else f"지원액(달러): {지원액_달러}달러")
            else:
                output_parts.append(f"지원액(달러): {지원액_달러}달러")
        except Exception:
            output_parts.append(f"지원액(달러): {지원액_달러}달러")
    if sdgs:
        output_parts.append(f"SDGs 연계: {sdgs}")
    output = "\n".join(output_parts)

    return {
        "instruction": "다음 사업의 지속가능개발목표(SDGs) 연계 현황에 대한 정보를 제공하세요.",
        "input": input_text,
        "output": output,
    }


def convert_recipient_country_data(row: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """사업요청 수원국 정보 데이터를 Instruction 형식으로 변환.
    CSV 컬럼: 사업번호, 사업명, 국가코드, 국가한글명, 수원국기관한글명, 수원국기관영문명, 시행기관한글명, 시행기관영문명
    """
    사업번호 = _col(row, "사업번호")
    사업명 = _col(row, "사업명")
    국가코드 = _col(row, "국가코드")
    국가한글명 = _col(row, "국가한글명")
    수원국기관한글 = _col(row, "수원국기관한글명")
    수원국기관영문 = _col(row, "수원국기관영문명")
    시행기관한글 = _col(row, "시행기관한글명")
    시행기관영문 = _col(row, "시행기관영문명")

    if not 사업명 and not 사업번호:
        return None

    # input: 사업번호, 사업명, 국가한글명
    input_parts = []
    if 사업번호:
        input_parts.append(f"사업번호: {사업번호}")
    if 사업명:
        input_parts.append(f"사업명: {사업명}")
    if 국가한글명:
        input_parts.append(f"국가: {국가한글명}")
    input_text = "\n".join(input_parts) if input_parts else (사업명 or 사업번호)

    # output: 사업번호, 사업명, 국가, 수원국기관, 시행기관
    output_parts = [f"사업번호: {사업번호 or '-'}", f"사업명: {사업명 or '-'}"]
    if 국가한글명:
        output_parts.append(f"국가: {국가한글명}")
    if 국가코드:
        output_parts.append(f"국가코드: {국가코드}")
    if 수원국기관한글 and 수원국기관영문:
        output_parts.append(f"수원국기관: {수원국기관한글} ({수원국기관영문})")
    elif 수원국기관한글:
        output_parts.append(f"수원국기관: {수원국기관한글}")
    elif 수원국기관영문:
        output_parts.append(f"수원국기관: {수원국기관영문}")
    if 시행기관한글 and 시행기관영문:
        output_parts.append(f"시행기관: {시행기관한글} ({시행기관영문})")
    elif 시행기관한글:
        output_parts.append(f"시행기관: {시행기관한글}")
    elif 시행기관영문:
        output_parts.append(f"시행기관: {시행기관영문}")
    output = "\n".join(output_parts)

    return {
        "instruction": "다음 사업요청에 대한 수원국 및 기관 정보를 제공하세요.",
        "input": input_text,
        "output": output,
    }


def convert_statistics_data(row: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """통계 데이터(연도, 사업유형, 금액)를 Instruction 형식으로 변환.
    CSV 컬럼: 연도, 사업유형, 금액(원), 금액(달러)
    """
    연도 = _col(row, "연도")
    사업유형 = _col(row, "사업유형")
    금액_원 = _col(row, "금액(원)")
    금액_달러 = _col(row, "금액(달러)")
    
    if not 연도 or not 사업유형:
        return None
    
    input_text = f"연도: {연도}\n사업유형: {사업유형}"
    
    output_parts = [f"{연도}년 {사업유형} 실적"]
    if 금액_원:
        try:
            # 숫자로 변환 시도
            금액_원_숫자 = 금액_원.replace(',', '').strip()
            if 금액_원_숫자.isdigit():
                output_parts.append(f"금액(원): {int(금액_원_숫자):,}원")
            else:
                output_parts.append(f"금액(원): {금액_원}")
        except:
            output_parts.append(f"금액(원): {금액_원}")
    if 금액_달러:
        try:
            # 숫자로 변환 시도
            금액_달러_숫자 = 금액_달러.replace(',', '').strip()
            if 금액_달러_숫자.replace('.', '').isdigit():
                output_parts.append(f"금액(달러): {float(금액_달러_숫자):,.0f}달러")
            else:
                output_parts.append(f"금액(달러): {금액_달러}")
        except:
            output_parts.append(f"금액(달러): {금액_달러}")
    
    output = "\n".join(output_parts)
    
    return {
        "instruction": "다음 ODA 실적 통계 정보를 제공하세요.",
        "input": input_text,
        "output": output
    }


def convert_eval_report_data(row: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """종료평가보고서 성과지표 요약 데이터를 Instruction 형식으로 변환.
    CSV 컬럼: 사업번호, 도메인, 사업명, 국가명, 시작년도, 종료년도, 평가완료일,
              사업금액_원, 사업금액_usd, 지표_대분류, 지표_중분류, 지표_소분류, 지표_세부분류, 기초선, 목표치, 결과선
    """
    사업번호 = _col(row, "사업번호")
    도메인 = _col(row, "도메인")
    사업명 = _col(row, "사업명")
    국가명 = _col(row, "국가명")
    시작년도 = _col(row, "시작년도")
    종료년도 = _col(row, "종료년도")
    평가완료일 = _col(row, "평가완료일")
    사업금액_원 = _col(row, "사업금액_원")
    사업금액_usd = _col(row, "사업금액_usd")
    지표_대 = _col(row, "지표_대분류")
    지표_중 = _col(row, "지표_중분류")
    지표_소 = _col(row, "지표_소분류")
    지표_세부 = _col(row, "지표_세부분류")
    기초선 = _col(row, "기초선")
    목표치 = _col(row, "목표치")
    결과선 = _col(row, "결과선")

    if not 사업명 and not 사업번호:
        return None

    # input: 사업번호, 사업명, 국가명, 지표(대분류 또는 중분류)
    input_parts = []
    if 사업번호:
        input_parts.append(f"사업번호: {사업번호}")
    if 사업명:
        input_parts.append(f"사업명: {사업명}")
    if 국가명:
        input_parts.append(f"국가: {국가명}")
    if 지표_대:
        input_parts.append(f"지표: {지표_대}")
    elif 지표_중:
        input_parts.append(f"지표: {지표_중}")
    input_text = "\n".join(input_parts) if input_parts else (사업명 or 사업번호)

    # output: 사업 정보 + 지표 계층 + 기초선/목표치/결과선
    output_parts = [f"사업번호: {사업번호 or '-'}", f"사업명: {사업명 or '-'}"]
    if 국가명:
        output_parts.append(f"국가: {국가명}")
    if 도메인:
        output_parts.append(f"도메인: {도메인}")
    if 시작년도 or 종료년도:
        output_parts.append(f"사업기간: {시작년도 or '-'} ~ {종료년도 or '-'}")
    if 평가완료일:
        output_parts.append(f"평가완료일: {평가완료일}")
    if 사업금액_원:
        try:
            v = 사업금액_원.replace(",", "").strip()
            if v.replace(".", "").isdigit():
                fv = float(v)
                output_parts.append(f"사업금액(원): {fv:,.0f}원" if fv >= 1 else f"사업금액(원): {사업금액_원}원")
            else:
                output_parts.append(f"사업금액(원): {사업금액_원}원")
        except Exception:
            output_parts.append(f"사업금액(원): {사업금액_원}원")
    if 사업금액_usd:
        try:
            v = 사업금액_usd.replace(",", "").strip()
            if v.replace(".", "").isdigit():
                fv = float(v)
                output_parts.append(f"사업금액(USD): {fv:,.0f}달러" if fv >= 1 else f"사업금액(USD): {사업금액_usd}달러")
            else:
                output_parts.append(f"사업금액(USD): {사업금액_usd}달러")
        except Exception:
            output_parts.append(f"사업금액(USD): {사업금액_usd}달러")
    # 지표 계층
    지표_parts = [x for x in [지표_대, 지표_중, 지표_소, 지표_세부] if x]
    if 지표_parts:
        output_parts.append(f"성과지표: {' > '.join(지표_parts)}")
    if 기초선:
        output_parts.append(f"기초선: {기초선}")
    if 목표치:
        output_parts.append(f"목표치: {목표치}")
    if 결과선:
        output_parts.append(f"결과선: {결과선}")
    output = "\n".join(output_parts)

    return {
        "instruction": "다음 사업의 종료평가보고서 성과지표 요약 정보를 제공하세요.",
        "input": input_text,
        "output": output,
    }


def detect_file_type(csv_path: Path) -> str:
    """CSV 파일 타입을 감지합니다.
    
    Args:
        csv_path: CSV 파일 경로
        
    Returns:
        파일 타입 ('glossary', 'project', 'qa', 'statistics', 'other')
    """
    filename = csv_path.name
    fn_lower = filename.lower()

    if '용어사전' in filename or 'glossary' in fn_lower:
        return 'glossary'
    elif '질의응답' in filename or 'qa' in fn_lower or '질문' in filename:
        return 'qa'
    elif '실적통계' in filename or '통계' in filename:
        return 'statistics'
    elif ('ngo' in fn_lower or 'NGO' in filename) and '길라잡이' in filename:
        return 'ngo_guide'
    elif '보도자료' in filename:
        return 'press_release'
    elif '국별' in filename and '동향' in filename:
        return 'country_trend'
    elif 'SDGs' in filename or '지속가능개발목표' in filename:
        return 'sdgs_project'
    elif '사업요청' in filename and '수원국' in filename:
        return 'recipient_country'
    elif '종료평가보고서' in filename and '성과지표' in filename:
        return 'eval_report'
    elif any(k in filename for k in ['사업', 'project', '협력', '보고서', '동향']):
        return 'project'
    else:
        return 'other'


def convert_csv_to_jsonl(csv_path: Path, jsonl_path: Path) -> int:
    """CSV 파일을 JSONL 형식으로 변환합니다.
    
    Args:
        csv_path: 입력 CSV 파일 경로
        jsonl_path: 출력 JSONL 파일 경로
        
    Returns:
        변환된 레코드 수
    """
    print(f"CSV 파일 로드 중: {csv_path.name}")
    csv_data = load_csv_data(csv_path)
    print(f"총 {len(csv_data)}개 레코드 로드 완료")
    
    if not csv_data:
        print(f"[WARNING] 데이터가 없습니다: {csv_path.name}")
        return 0
    
    # 파일 타입 감지
    file_type = detect_file_type(csv_path)
    print(f"파일 타입 감지: {file_type}")
    
    # 변환 함수 선택
    converter_map = {
        'glossary': convert_oda_glossary,
        'project': convert_project_data,
        'qa': convert_qa_data,
        'statistics': convert_statistics_data,
        'ngo_guide': convert_ngo_guide_data,
        'press_release': convert_press_release_data,
        'country_trend': convert_country_trend_data,
        'sdgs_project': convert_sdgs_project_data,
        'recipient_country': convert_recipient_country_data,
        'eval_report': convert_eval_report_data,
    }
    
    converter = converter_map.get(file_type, convert_project_data)
    
    print("JSONL 형식으로 변환 중...")
    jsonl_data = []
    skipped = 0
    
    for i, row in enumerate(csv_data):
        if i % 1000 == 0 and i > 0:
            print(f"진행 중: {i}/{len(csv_data)} ({i/len(csv_data)*100:.1f}%)")
        
        try:
            instruction_data = converter(row)
            if instruction_data:
                jsonl_data.append(instruction_data)
            else:
                skipped += 1
        except Exception as e:
            print(f"[WARNING] {i+1}번째 행 변환 실패: {e}")
            skipped += 1
            continue
    
    if skipped > 0:
        print(f"[WARNING] {skipped}개 레코드 건너뜀")
    
    print(f"JSONL 파일 저장 중: {jsonl_path.name}")
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with open(jsonl_path, 'w', encoding='utf-8') as f:
        for item in jsonl_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"[OK] 변환 완료! 총 {len(jsonl_data)}개 레코드 저장됨")
    return len(jsonl_data)


def main():
    """메인 함수: koica_data 폴더의 모든 CSV 파일을 JSONL로 변환합니다."""
    project_root = Path(__file__).parent.parent.parent
    koica_data_dir = project_root / "data" / "koica_data"
    
    if not koica_data_dir.exists():
        print(f"[ERROR] 디렉토리를 찾을 수 없습니다: {koica_data_dir}")
        return
    
    print("=" * 60)
    print("KOICA 데이터 JSONL 변환")
    print("=" * 60)
    print(f"데이터 폴더: {koica_data_dir}\n")
    
    # CSV 파일 찾기
    csv_files = sorted(koica_data_dir.glob("*.csv"))
    
    if not csv_files:
        print(f"[WARNING] {koica_data_dir} 폴더에 CSV 파일이 없습니다.")
        return
    
    print(f"총 {len(csv_files)}개의 CSV 파일을 찾았습니다.\n")
    
    total_converted = 0
    for csv_file in csv_files:
        print(f"{'='*60}")
        print(f"처리 중: {csv_file.name}")
        print(f"{'='*60}")
        
        # 출력 파일 경로 (확장자만 .jsonl로 변경)
        jsonl_file = csv_file.with_suffix('.jsonl')
        
        try:
            count = convert_csv_to_jsonl(csv_file, jsonl_file)
            total_converted += count
            print(f"[OK] 성공: {jsonl_file.name} ({count}개 레코드)\n")
        except Exception as e:
            print(f"[ERROR] 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            print()
    
    print("=" * 60)
    print(f"전체 변환 완료! 총 {total_converted}개 레코드 변환됨")
    print("=" * 60)


if __name__ == "__main__":
    main()
