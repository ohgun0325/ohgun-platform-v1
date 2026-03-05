"""CMRT 6.5 파일 구조 분석 스크립트 (UTF-8)"""
import pandas as pd
import sys
import io

# UTF-8 출력 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def analyze_critical_sheets(file_path: str):
    """핵심 시트만 상세 분석"""
    
    print("=" * 80)
    print("RMI CMRT 6.5 핵심 시트 구조 분석")
    print("=" * 80)
    
    xl = pd.ExcelFile(file_path)
    
    # 핵심 시트 분석
    critical_sheets = {
        'Declaration': '선언 시트 (질문 1-7)',
        'Smelter List': '제련소 목록 입력 시트',
        'Smelter Look-up': '표준 제련소 참조 데이터',
        'Checker': '검증 로직 시트',
        'Product List': '제품 목록'
    }
    
    for sheet_name, description in critical_sheets.items():
        print(f"\n{'=' * 80}")
        print(f"시트: {sheet_name} ({description})")
        print("=" * 80)
        
        try:
            # 헤더 없이 처음 50행 읽기
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=50)
            
            print(f"\n시트 크기: {df.shape[0]} 행 x {df.shape[1]} 열")
            
            # 각 행의 첫 5개 열만 출력
            print("\n[처음 50행의 주요 내용 (첫 5개 열)]")
            for idx, row in df.iterrows():
                # 빈 행이 아닌 경우만 출력
                if row.notna().any():
                    row_preview = []
                    for i in range(min(5, len(row))):
                        val = row[i]
                        if pd.notna(val):
                            val_str = str(val)[:60]  # 60자까지만
                            row_preview.append(f"[{i}]: {val_str}")
                    
                    if row_preview:
                        print(f"\n행 {idx}: {' | '.join(row_preview)}")
            
            # 전체 데이터 통계
            df_full = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            print(f"\n\n전체 시트 크기: {df_full.shape[0]} 행 x {df_full.shape[1]} 열")
            
            # 데이터가 있는 영역 찾기
            non_empty_rows = df_full.notna().any(axis=1).sum()
            non_empty_cols = df_full.notna().any(axis=0).sum()
            print(f"데이터가 있는 행: {non_empty_rows}개")
            print(f"데이터가 있는 열: {non_empty_cols}개")
            
        except Exception as e:
            print(f"ERROR: {sheet_name} 시트 읽기 실패 - {e}")
    
    # Smelter Look-up 특별 분석
    print(f"\n\n{'=' * 80}")
    print("Smelter Look-up 시트 특별 분석 (표준 제련소 데이터)")
    print("=" * 80)
    
    try:
        # 다양한 헤더 행에서 시도
        for header_row in [0, 1, 2, 3, 4, 5]:
            try:
                df_smelter = pd.read_excel(file_path, sheet_name='Smelter Look-up', header=header_row)
                if len(df_smelter.columns) > 5:  # 의미있는 데이터가 있는 경우
                    print(f"\n헤더 행 {header_row}에서 읽기 성공")
                    print(f"컬럼명: {list(df_smelter.columns)[:10]}")
                    print(f"데이터 개수: {len(df_smelter)}행")
                    print(f"\n처음 5행 샘플:")
                    print(df_smelter.head().to_string())
                    break
            except:
                continue
                
    except Exception as e:
        print(f"ERROR: Smelter Look-up 특별 분석 실패 - {e}")
    
    print("\n" + "=" * 80)
    print("분석 완료")
    print("=" * 80)

if __name__ == "__main__":
    file_path = "data/rmi/RMI_CMRT_6.5.xlsx"
    analyze_critical_sheets(file_path)
