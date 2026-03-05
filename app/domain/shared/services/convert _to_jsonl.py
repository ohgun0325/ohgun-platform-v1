"""CSV 파일을 JSONL 형식으로 변환하는 스크립트.

data 폴더 아래의 CSV 파일을 읽어서 Instruction 형식의 JSONL로 변환합니다.
"""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any


def load_csv_data(csv_path: str) -> List[Dict[str, Any]]:
    """CSV 파일을 로드합니다.
    
    Args:
        csv_path: CSV 파일 경로
        
    Returns:
        CSV 데이터를 딕셔너리 리스트로 반환
    """
    data = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(dict(row))
    return data


def convert_to_instruction_format(row: Dict[str, Any]) -> Dict[str, str]:
    """CSV 행을 Instruction 형식으로 변환합니다.
    
    Args:
        row: CSV 행 데이터
        
    Returns:
        Instruction 형식의 딕셔너리
    """
    # CSV 컬럼명: 수신일자, 수신시간, 메일 종류, 제목, 첨부
    date = row.get('수신일자', '')
    time = row.get('수신시간', '')
    mail_type = row.get('메일 종류', '')
    subject = row.get('제목', '')
    attachment = row.get('첨부', '')
    
    # 입력 텍스트 구성
    input_text = f"수신일자: {date}\n수신시간: {time}\n제목: {subject}"
    if attachment:
        input_text += f"\n첨부: {attachment}"
    
    # Instruction 형식으로 변환
    instruction = "다음 이메일이 스팸인지 판단하고 이유를 설명하세요."
    
    # 출력 텍스트 구성
    if mail_type == "스팸":
        # 스팸 타입 분석
        spam_reason = analyze_spam_type(subject, attachment)
        output = f"이 이메일은 스팸입니다. {spam_reason}"
    else:
        output = "이 이메일은 정상 메일입니다."
    
    return {
        "instruction": instruction,
        "input": input_text,
        "output": output
    }


def analyze_spam_type(subject: str, attachment: str = "") -> str:
    """스팸 타입을 분석하여 이유를 반환합니다.
    
    Args:
        subject: 이메일 제목
        attachment: 첨부 파일 정보
        
    Returns:
        스팸 이유 설명
    """
    subject_lower = subject.lower()
    attachment_lower = attachment.lower() if attachment else ""
    
    # 광고 스팸
    if "(광고)" in subject or "광고" in subject:
        return "광고성 스팸입니다. 상품이나 서비스를 홍보하는 내용이 포함되어 있습니다."
    
    # 피싱 스팸 (첨부 파일)
    if attachment and any(ext in attachment_lower for ext in [".docx", ".doc", ".pdf", ".exe"]):
        if "offer" in subject_lower or "promotion" in subject_lower:
            return "피싱 스팸입니다. 의심스러운 첨부 파일이 포함되어 있습니다."
    
    # 반송 메일
    if "반송" in subject or "returned mail" in subject_lower or "delivery failure" in subject_lower:
        return "반송 메일입니다. 배달 실패로 인한 자동 반송 메일입니다."
    
    # 해외 스팸
    if any(keyword in subject_lower for keyword in ["offer", "promotion", "urgent", "winner"]):
        return "해외 스팸입니다. 영어로 된 의심스러운 제목이 포함되어 있습니다."
    
    # 일반 스팸
    return "스팸 메일입니다. 의심스러운 내용이 포함되어 있습니다."


def convert_csv_to_jsonl(csv_path: str, jsonl_path: str) -> None:
    """CSV 파일을 JSONL 형식으로 변환합니다.
    
    Args:
        csv_path: 입력 CSV 파일 경로
        jsonl_path: 출력 JSONL 파일 경로
    """
    print(f"CSV 파일 로드 중: {csv_path}")
    csv_data = load_csv_data(csv_path)
    print(f"총 {len(csv_data)}개 레코드 로드 완료")
    
    print("JSONL 형식으로 변환 중...")
    jsonl_data = []
    for i, row in enumerate(csv_data):
        if i % 10000 == 0:
            print(f"진행 중: {i}/{len(csv_data)} ({i/len(csv_data)*100:.1f}%)")
        
        instruction_data = convert_to_instruction_format(row)
        jsonl_data.append(instruction_data)
    
    print(f"JSONL 파일 저장 중: {jsonl_path}")
    with open(jsonl_path, 'w', encoding='utf-8') as f:
        for item in jsonl_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"변환 완료! 총 {len(jsonl_data)}개 레코드 저장됨")


def find_csv_files(data_dir: Path) -> List[Path]:
    """data 폴더에서 CSV 파일을 찾습니다.
    
    Args:
        data_dir: data 폴더 경로
        
    Returns:
        찾은 CSV 파일 경로 리스트
    """
    csv_files = list(data_dir.glob("*.csv"))
    return csv_files


def main():
    """메인 함수: data 폴더의 모든 CSV 파일을 JSONL로 변환합니다."""
    # 프로젝트 루트 경로 (이 파일이 app/service/에 있으므로 2단계 위로)
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data"
    
    # data 폴더가 없으면 생성
    data_dir.mkdir(exist_ok=True)
    print(f"데이터 폴더: {data_dir}")
    
    # CSV 파일 찾기
    csv_files = find_csv_files(data_dir)
    
    if not csv_files:
        print(f"경고: {data_dir} 폴더에 CSV 파일이 없습니다.")
        print("프로젝트 루트의 koreapost_spem_list.csv를 data 폴더로 복사하거나,")
        print("CSV 파일을 data 폴더에 넣어주세요.")
        return
    
    # 각 CSV 파일을 JSONL로 변환
    for csv_file in csv_files:
        print(f"\n{'='*60}")
        print(f"처리 중: {csv_file.name}")
        print(f"{'='*60}")
        
        # 출력 파일 경로 (확장자만 .jsonl로 변경)
        jsonl_file = csv_file.with_suffix('.jsonl')
        
        try:
            convert_csv_to_jsonl(str(csv_file), str(jsonl_file))
            print(f"성공: {jsonl_file.name}")
        except Exception as e:
            print(f"오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
