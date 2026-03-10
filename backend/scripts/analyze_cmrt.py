"""CMRT 6.5 파일 구조 분석 스크립트"""
import pandas as pd
import sys

def analyze_cmrt_structure(file_path: str):
    """CMRT 엑셀 파일의 구조를 상세하게 분석"""
    
    print("=" * 80)
    print("RMI CMRT 6.5 파일 구조 분석")
    print("=" * 80)
    
    xl = pd.ExcelFile(file_path)
    
    critical_sheets = ['Declaration', 'Smelter List', 'Smelter Look-up', 'Checker']
    
    for sheet_name in xl.sheet_names:
        print(f"\n{'=' * 80}")
        print(f"시트명: {sheet_name}")
        print("=" * 80)
        
        try:
            # 전체 시트를 읽되, 헤더 없이 읽어서 실제 구조 파악
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, nrows=20)
            
            print(f"\n시트 크기: {df.shape[0]} 행 x {df.shape[1]} 열 (상위 20행만 출력)")
            print("\n[상위 데이터 미리보기]")
            print(df.to_string())
            
            # 핵심 시트는 더 자세히 분석
            if sheet_name in critical_sheets:
                print(f"\n\n*** {sheet_name} 시트 상세 분석 ***")
                
                # 실제 데이터가 시작되는 행 찾기
                df_full = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
                print(f"전체 행 수: {len(df_full)}")
                
                # 빈 셀이 아닌 데이터 분포 확인
                non_empty_cols = df_full.notna().sum()
                print(f"\n각 열별 데이터가 있는 셀 개수:")
                for idx, count in enumerate(non_empty_cols[:30]):  # 처음 30개 열만
                    if count > 0:
                        print(f"  열 {idx}: {count}개")
                        
        except Exception as e:
            print(f"ERROR: {sheet_name} 시트 읽기 실패 - {e}")
    
    print("\n" + "=" * 80)
    print("분석 완료")
    print("=" * 80)

if __name__ == "__main__":
    file_path = "data/rmi/RMI_CMRT_6.5.xlsx"
    analyze_cmrt_structure(file_path)
