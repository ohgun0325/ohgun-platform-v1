"""SQL INSERT 문을 players.jsonl 형식으로 변환하는 스크립트 (간단한 버전)."""

import re
import json
from pathlib import Path

def parse_sql_insert(sql_line: str) -> dict:
    """SQL INSERT 문을 파싱하여 딕셔너리로 변환."""
    # VALUES 이후의 괄호 안 내용 추출
    match = re.search(r"VALUES\s*\((.+)\);?$", sql_line, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    
    values_str = match.group(1)
    
    # 쉼표로 분리하되, 따옴표 안의 쉼표는 무시
    values = []
    current = ""
    in_quotes = False
    quote_char = None
    paren_depth = 0
    
    i = 0
    while i < len(values_str):
        char = values_str[i]
        
        # 따옴표 처리
        if char in ("'", '"') and (i == 0 or values_str[i-1] != '\\'):
            if not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char:
                in_quotes = False
                quote_char = None
            current += char
        # 괄호 처리 (TO_DATE 내부)
        elif not in_quotes:
            if char == '(':
                paren_depth += 1
                current += char
            elif char == ')':
                paren_depth -= 1
                current += char
            elif char == ',' and paren_depth == 0:
                values.append(current.strip())
                current = ""
            else:
                current += char
        else:
            current += char
        
        i += 1
    
    # 마지막 값 추가
    if current.strip():
        values.append(current.strip())
    
    if len(values) != 13:
        return None
    
    # 값 정리 함수
    def clean_value(val: str) -> str:
        val = val.strip()
        if val.startswith("'") and val.endswith("'"):
            val = val[1:-1]
        elif val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        return val.strip()
    
    # 날짜 파싱 함수
    def parse_date(date_str: str) -> str:
        if not date_str or not date_str.upper().startswith('TO_DATE'):
            return clean_value(date_str) if date_str else None
        
        date_match = re.search(r"TO_DATE\s*\(\s*'([^']+)'", date_str, re.IGNORECASE)
        if not date_match:
            return None
        
        date_part = date_match.group(1)
        month_map = {
            'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
            'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
            'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'
        }
        
        parts = date_part.split('-')
        if len(parts) == 3:
            day = parts[0].zfill(2)
            month = month_map.get(parts[1].upper(), '01')
            year = parts[2]
            return f"{year}-{month}-{day}"
        
        return None
    
    # 값 추출
    player_id = clean_value(values[0])
    player_name = clean_value(values[1])
    team_id = clean_value(values[2])
    e_player_name = clean_value(values[3]) or None
    nickname = clean_value(values[4]) or None
    join_yyyy = clean_value(values[5]) or None
    position = clean_value(values[6])
    back_no = clean_value(values[7]) or None
    nation = clean_value(values[8]) or None
    birth_date = parse_date(values[9])
    solar = clean_value(values[10]) or None
    height = clean_value(values[11]) or None
    weight = clean_value(values[12]) or None
    
    return {
        "id": player_id,
        "player_name": player_name,
        "team_id": team_id,
        "e_player_name": e_player_name,
        "nickname": nickname,
        "join_yyyy": join_yyyy,
        "position": position,
        "back_no": back_no,
        "nation": nation,
        "birth_date": birth_date,
        "solar": solar,
        "height": height,
        "weight": weight
    }


def convert_sql_to_jsonl(sql_content: str, output_path: Path):
    """SQL INSERT 문들을 JSONL 파일로 변환."""
    lines = sql_content.strip().split('\n')
    players = []
    errors = []
    
    for idx, line in enumerate(lines, 1):
        line = line.strip()
        if not line or not line.upper().startswith('INSERT'):
            continue
        
        try:
            player = parse_sql_insert(line)
            if player:
                players.append(player)
            else:
                errors.append(f"Line {idx}: Parsing failed")
        except Exception as e:
            errors.append(f"Line {idx}: Error - {str(e)}")
    
    # JSONL 파일로 저장
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for player in players:
            f.write(json.dumps(player, ensure_ascii=False) + '\n')
    
    print(f"[SUCCESS] Conversion completed!")
    print(f"   Total lines: {len(lines)}")
    print(f"   Success: {len(players)} records")
    print(f"   Errors: {len(errors)} records")
    
    if errors:
        print(f"\n[WARNING] Error list (first 10):")
        for error in errors[:10]:
            print(f"   {error}")
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more")
    
    return players


if __name__ == "__main__":
    # SQL INSERT 문들 (사용자가 제공한 내용)
    sql_content = """INSERT INTO player VALUES  ('2009175','우르모브','K06','','','2009','DF','4','유고',TO_DATE('30-AUG-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','180','70');
INSERT INTO player VALUES  ('2007188','윤희준','K06','','','2005','DF','15','',TO_DATE('01-NOV-1982','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','180','74');
INSERT INTO player VALUES  ('2012073','김규호','K06','','','2011','DF','23','',TO_DATE('13-JUL-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','177','72');
INSERT INTO player VALUES  ('2007178','김민성','K06','','','','DF','20','',TO_DATE('23-JUN-1983','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','182','73');
INSERT INTO player VALUES  ('2007191','김장관','K06','','배추도사,작은삼손','2007','DF','18','',TO_DATE('05-JUN-1984','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'2','170','61');
INSERT INTO player VALUES  ('2008384','김정효','K06','','깜둥이,통키통','2008','DF','19','',TO_DATE('23-JUL-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'2','174','68');
INSERT INTO player VALUES  ('2008395','장대일','K06','','달구','2010','DF','7','',TO_DATE('09-MAR-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','184','79');
INSERT INTO player VALUES  ('2011050','박상수','K06','','꼬마홍길동','2011','DF','36','',TO_DATE('14-JUN-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE  = AMERICAN'),'1','173','65');
INSERT INTO player VALUES  ('2007189','정재영','K06','','제리','2006','MF','6','',TO_DATE('02-SEP-1983','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','187','75');
INSERT INTO player VALUES  ('2011049','정태민','K06','','킹카','2011','MF','38','',TO_DATE('25-MAY-1992','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','180','71');
INSERT INTO player VALUES  ('2010107','정현우','K06','','','2010','MF','37','',TO_DATE('04-JUN-1991','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','70');
INSERT INTO player VALUES  ('2011043','송종국','K06','','썰렁왕자','2011','MF','24','',TO_DATE('20-FEB-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE  = AMERICAN'),'1','177','73');
INSERT INTO player VALUES  ('2011044','오정석','K06','','서경석','2011','MF','13','',TO_DATE('08-SEP-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','74');
INSERT INTO player VALUES  ('2012137','이고르','K06','이골 실바 데  페리이따스','이골','2012','MF','21','브라질',TO_DATE('25-OCT-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','181','76');
INSERT INTO player VALUES  ('2007200','김용하','K06','','용식이','2007','MF','26','',TO_DATE('15-DEC-1983','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','173','66');
INSERT INTO player VALUES  ('2012072','전상배','K06','','','2012','MF','14','',TO_DATE('22-MAR-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','176','67');
INSERT INTO player VALUES  ('2009038','전우근','K06','','에너자이져','2009','MF','11','',TO_DATE('25-FEB-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE  = AMERICAN'),'2','175','68');
INSERT INTO player VALUES  ('2008365','이태성','K06','','','2011','MF','30','',TO_DATE('16-JUN-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','177','64');
INSERT INTO player VALUES  ('2011047','황철민','K06','','사다리맨','2011','MF','35','',TO_DATE('20-NOV-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE  = AMERICAN'),'1','175','68');
INSERT INTO player VALUES  ('2008235','정관규','K06','','','','FW','39','',TO_DATE('10-OCT-1986','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','71');
INSERT INTO player VALUES  ('2011048','정기종','K06','','','2011','FW','25','',TO_DATE('22-MAY-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','182','78');
INSERT INTO player VALUES  ('2012074','정창오','K06','','임땡','2012','FW','27','',TO_DATE('10-JAN-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','186','82');
INSERT INTO player VALUES  ('2012127','디디','K06','Sebastiao  Pereira do  Nascimento','','2012','FW','8','브라질',TO_DATE('24-FEB-1986','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','179','78');
INSERT INTO player VALUES  ('2007182','마니치','K06','','바람의  아들','2006','FW','9','',TO_DATE('16-JAN-1982','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'2','184','80');
INSERT INTO player VALUES  ('2007195','우성용','K06','','따따','2006','FW','22','',TO_DATE('18-AUG-1983','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','191','76');
INSERT INTO player VALUES  ('2010103','장기봉','K06','','짝팔','2010','FW','12','',TO_DATE('08-JUL-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','180','71');
INSERT INTO player VALUES  ('2012075','이광수','K06','','','2012','FW','29','',TO_DATE('25-SEP-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','177','73');
INSERT INTO player VALUES  ('2010087','하리','K06','','','2010','FW','10','콜롬비아',TO_DATE('14-MAY-1984','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','168','65');
INSERT INTO player VALUES  ('2000017','박상남','K06','','','2008','FW','32','',TO_DATE('07-SEP-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','188','80');
INSERT INTO player VALUES  ('2000018','빅토르','K06','','빅토르','2011','FW','28','나이지리아',TO_DATE('05-JAN-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'1','183','79');
INSERT INTO player VALUES  ('2000021','이윤겸','K04','LEE,  YOONGYUM','','2002','DF','','',TO_DATE('','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'','178','80');
INSERT INTO player VALUES  ('2000022','하재훈','K04','HA,  JAEHON','','2002','DF','','',TO_DATE('','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'','174','67');
INSERT INTO player VALUES  ('2000023','김충호','K04','KIM,  CHUNGHO','','2009','DF','','',TO_DATE('','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'','185','83');
INSERT INTO player VALUES  ('2000024','임기한','K04','LIM,  GIHAN','','2004','DF','','',TO_DATE('','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'','177','85');
INSERT INTO player VALUES  ('2000025','김경태','K04','KIM,  KYOUNGTAE','','','DF','','',TO_DATE('','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'','','');
INSERT INTO player VALUES  ('2012054','남현우','K04','','','','GK','31','',TO_DATE('20-APR-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','180','72');
INSERT INTO player VALUES  ('2008499','김충호','K04','','','','GK','60','',TO_DATE('04-JUL-1978','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','185','83');
INSERT INTO player VALUES  ('2011021','이현','K04','','','','GK','1','',TO_DATE('07-NOV-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','192','85');
INSERT INTO player VALUES  ('2012052','한동진','K04','','','','GK','21','',TO_DATE('25-AUG-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','183','78');
INSERT INTO player VALUES  ('2012126','다오','K04','','','','DF','61','',TO_DATE('25-SEP-1992','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','190','80');
INSERT INTO player VALUES  ('2008182','최철','K04','','','','DF','15','',TO_DATE('20-AUG-1983','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','176','77');
INSERT INTO player VALUES  ('2010112','송창남','K04','','','','DF','23','',TO_DATE('31-DEC-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','175','67');
INSERT INTO player VALUES  ('2008424','조승호','K04','','','','DF','2','',TO_DATE('13-MAY-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','179','70');
INSERT INTO player VALUES  ('2008450','윤중희','K04','','','','DF','5','',TO_DATE('08-DEC-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','177','75');
INSERT INTO player VALUES  ('2011022','김범직','K04','','','','DF','25','',TO_DATE('11-FEB-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','182','75');
INSERT INTO player VALUES  ('2012053','김상홍','K04','','','','DF','30','',TO_DATE('04-FEB-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','68');
INSERT INTO player VALUES  ('2000001','김태호','K10','','','','DF','','',TO_DATE('29-JAN-1971','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','','');
INSERT INTO player VALUES  ('2000002','정상수','K10','JEONG,  SAMSOO','','','DF','','',TO_DATE('08-FEB-1973','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'1','','');
INSERT INTO player VALUES  ('2000003','유동우','K10','YOU,  DONGWOO','','','DF','40','',TO_DATE('07-MAR-1978','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'1','177','70');
INSERT INTO player VALUES  ('2000004','전기현','K10','JEON,  GIHYUN','','','DF','','',TO_DATE('06-JUN-1975','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'1','','');
INSERT INTO player VALUES  ('2012047','강성일','K10','KANG,  SUNGIL','','2012','GK','30','',TO_DATE('04-JUN-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','182','80');
INSERT INTO player VALUES  ('2010057','김승준','K10','KIM,  SEUNGJUN','개구멍','2010','GK','1','',TO_DATE('01-SEP-1982','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','183','77');
INSERT INTO player VALUES  ('2007298','이은성','K10','LEE,  EUNSUNG','수호천황','2007','GK','21','',TO_DATE('05-APR-1981','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','184','82');
INSERT INTO player VALUES  ('2007312','정대수','K10','JEONG,  DAESOO','','2007','DF','15','',TO_DATE('20-MAR-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','184','74');
INSERT INTO player VALUES  ('2012051','정민기','K10','','','','DF','3','',TO_DATE('25-APR-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','171','65');
INSERT INTO player VALUES  ('2010110','정성근','K10','JEONG,  SUNGKEUN','','2010','DF','33','',TO_DATE('20-JUN-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','180','73');
INSERT INTO player VALUES  ('2011098','정영근','K10','JEONG,  YOUNGKWEN','','2011','DF','5','',TO_DATE('12-OCT-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','180','70');
INSERT INTO player VALUES  ('2007301','정정수','K10','JEONG,  JUNGSOO','','2002','DF','36','',TO_DATE('17-JAN-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','180','74');
INSERT INTO player VALUES  ('2007309','김창엽','K10','KIM,  CHANGYUP','','2007','DF','6','',TO_DATE('19-NOV-1984','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','174','64');
INSERT INTO player VALUES  ('2007299','장철우','K10','JANG,  CHULWOO','폭주기관차','2010','DF','7','',TO_DATE('01-APR-1981','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','172','65');
INSERT INTO player VALUES  ('2011116','콜리','K10','OMAR PAPA  COLY','검은낙타(Black  Camel)','2011','DF','29','세네갈',TO_DATE('20-MAY-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','182','75');
INSERT INTO player VALUES  ('2007313','홍광철','K10','HONG,  KWANGCHUL','','2007','DF','4','',TO_DATE('09-OCT-1984','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','172','65');
INSERT INTO player VALUES  ('2008461','강정훈','K10','KANG,  JUNGHOON','','2008','MF','38','',TO_DATE('20-FEB-1986','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','175','65');
INSERT INTO player VALUES  ('2007306','공오균','K10','KONG,  OHKYUN','CROW','2007','MF','22','',TO_DATE('10-AUG-1984','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','177','72');
INSERT INTO player VALUES  ('2012049','정국진','K10','JEONG,  KOOKJIN','','2012','MF','16','',TO_DATE('09-FEB-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','172','62');
INSERT INTO player VALUES  ('2011099','정동선','K10','JEONG,  DONGSUN','','2011','MF','9','',TO_DATE('15-MAR-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','170','65');
INSERT INTO player VALUES  ('2010109','최경규','K10','CHOI,  KUNGGUY','','2010','MF','10','',TO_DATE('10-MAR-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','177','72');
INSERT INTO player VALUES  ('2010111','최내철','K10','CHOI,  RAECHEOL','','2010','MF','24','',TO_DATE('20-AUG-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','177','71');
INSERT INTO player VALUES  ('2012048','배성재','K10','BAE,  SUNGJAE','','2012','MF','28','',TO_DATE('01-JUL-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','74');
INSERT INTO player VALUES  ('2012121','샴','K10','','','','MF','25','',TO_DATE('30-APR-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','174','69');
INSERT INTO player VALUES  ('2012136','오비나','K10','','','','MF','26','',TO_DATE('03-JUN-1990','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','169','70');
INSERT INTO player VALUES  ('2010056','김관우','K10','KIM,  KWANWOO','SIRIUS','2010','MF','8','',TO_DATE('25-FEB-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','175','69');
INSERT INTO player VALUES  ('2012050','김광진','K10','KIM,  KWANGJIN','','2012','MF','13','',TO_DATE('27-MAY-1982','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','175','75');
INSERT INTO player VALUES  ('2010113','김상규','K10','KIM,  SANGKYU','','2010','MF','27','',TO_DATE('05-SEP-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','175','65');
INSERT INTO player VALUES  ('2009151','임영주','K10','LIM,  YOUNGJOO','','2009','MF','23','',TO_DATE('08-MAR-1986','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','176','68');
INSERT INTO player VALUES  ('2011101','박영훈','K10','PARK,  YOUNGHOON','','2011','MF','12','',TO_DATE('01-MAY-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','174','73');
INSERT INTO player VALUES  ('2008178','한정국','K10','HAN,  JUNGKOOK','','2011','MF','19','',TO_DATE('19-JUL-1981','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','179','71');
INSERT INTO player VALUES  ('2012046','정광선','K10','JEONG,  KWANGSUN','','2012','FW','32','',TO_DATE('17-JUN-1993','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','175','68');
INSERT INTO player VALUES  ('2007315','정은중','K10','JEONG,  EUNJUNG','샤프(SHARP)','2007','FW','18','',TO_DATE('08-APR-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','184','72');
INSERT INTO player VALUES  ('2009152','정찬중','K10','JEONG.  CHANJOONG','','2009','FW','17','',TO_DATE('14-JUN-1986','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','182','72');
INSERT INTO player VALUES  ('2011032','김석','K10','KIM,  SEOK','','2012','FW','20','',TO_DATE('01-FEB-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'1','194','85');
INSERT INTO player VALUES  ('2011100','탁준석','K10','TAK,  JUNSUK','','2011','FW','11','',TO_DATE('24-MAR-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','69');
INSERT INTO player VALUES  ('2000011','정호곤','K06','','','2010','DF','','',TO_DATE('26-MAR-1971','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','172','77');
INSERT INTO player VALUES  ('2000012','최경훈','K06','','','','DF','','',TO_DATE('19-JAN-1971','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','','');
INSERT INTO player VALUES  ('2000013','정동훈','K06','','','2010','DF','','',TO_DATE('11-JUN-1975','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','180','88');
INSERT INTO player VALUES  ('2000014','정남표','K06','','','2005','DF','','',TO_DATE('27-JAN-1974','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','180','77');
INSERT INTO player VALUES  ('2000015','정광재','K06','','','2005','DF','','',TO_DATE('30-MAY-1978','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','180','75');
INSERT INTO player VALUES  ('2000016','권혁준','K06','','','2006','DF','','',TO_DATE('22-MAY-1980','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','173','82');
INSERT INTO player VALUES  ('2011052','정경진','K06','','임꺽정','2011','GK','41','',TO_DATE('07-FEB-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','186','78');
INSERT INTO player VALUES  ('2012076','정용대','K06','','','2012','GK','40','',TO_DATE('11-OCT-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','189','83');
INSERT INTO player VALUES  ('2010108','정지혁','K06','','','2010','GK','31','',TO_DATE('22-NOV-1991','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','187','77');
INSERT INTO player VALUES  ('2010059','박유석','K06','','터프가이','2010','GK','1','',TO_DATE('10-JUN-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','186','78');
INSERT INTO player VALUES  ('2011053','정진우','K06','','터프가이','2011','DF','33','',TO_DATE('28-FEB-1993','DD_MON_YYYY','NLS_DATE_LANGUAGE  = AMERICAN'),'1','180','76');
INSERT INTO player VALUES  ('2007185','정학철','K06','','','2005','DF','3','',TO_DATE('07-NOV-1982','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','176','73');
INSERT INTO player VALUES  ('2007193','류병훈','K06','','','2005','DF','17','',TO_DATE('03-JUL-1986','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','184','68');
INSERT INTO player VALUES  ('2011055','최준홍','K06','','말머리','2011','DF','2','',TO_DATE('13-APR-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','70');
INSERT INTO player VALUES  ('2011046','서용혁','K06','','터프가이','2011','DF','34','',TO_DATE('02-JUL-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE  = AMERICAN'),'1','183','79');
INSERT INTO player VALUES  ('2010058','심재원','K06','','도날드  덕','2010','DF','5','',TO_DATE('11-MAR-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'1','184','77');
INSERT INTO player VALUES  ('2007123','김임생','K04','','','','DF','20','',TO_DATE('17-NOV-1981','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','183','80');
INSERT INTO player VALUES  ('2007022','장형석','K04','','','','DF','36','',TO_DATE('07-JUL-1982','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','181','72');
INSERT INTO player VALUES  ('2012058','박진성','K04','','','','DF','35','',TO_DATE('10-AUG-1993','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','184','76');
INSERT INTO player VALUES  ('2009125','이거룩','K04','','','','DF','4','',TO_DATE('26-JUN-1986','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','183','77');
INSERT INTO player VALUES  ('2010001','이정민','K04','','','','DF','3','',TO_DATE('07-OCT-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','183','78');
INSERT INTO player VALUES  ('2012134','페르난도','K04','','','','DF','44','',TO_DATE('24-FEB-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','74');
INSERT INTO player VALUES  ('2000094','김무건','K03','KIM,  MUGYUN','','','DF','','',TO_DATE('18-MAR-1971','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'1','','');
INSERT INTO player VALUES  ('2007001','정병지','K03','JEONG,  BYUNGJI','','2011','GK','1','',TO_DATE('08-APR-1980','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','184','77');
INSERT INTO player VALUES  ('2011069','최주호','K03','CHOI,  JUHO','','2011','GK','51','',TO_DATE('16-JUL-1992','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'1','185','75');
INSERT INTO player VALUES  ('2007130','김대희','K03','KIM,  DAEHEE','','2010','GK','31','',TO_DATE('26-APR-1984','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','192','88');
INSERT INTO player VALUES  ('2009133','김준호','K03','KIM,  JUNHO','','2009','GK','21','',TO_DATE('28-APR-1983','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'1','185','77');
INSERT INTO player VALUES  ('2011065','허인무','K03','HEO,  INMOO','','2011','GK','41','',TO_DATE('14-APR-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'1','187','81');
INSERT INTO player VALUES  ('2011056','강용','K03','KANG,  YONG','','2011','DF','2','',TO_DATE('14-JAN-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'1','179','72');
INSERT INTO player VALUES  ('2007080','고병운','K03','GO,  BYUNGWOON','','2006','DF','16','',TO_DATE('28-SEP-1983','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','180','73');
INSERT INTO player VALUES  ('2012069','정광석','K03','JEONG,  KWANGSUK','','2012','DF','39','',TO_DATE('12-FEB-1993','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','183','72');
INSERT INTO player VALUES  ('2007002','정상훈','K03','JEONG,  SANGHUN','','2006','DF','13','',TO_DATE('08-JUN-1983','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','183','76');
INSERT INTO player VALUES  ('2012062','정석우','K03','JEONG,  SEOKWOO','','2012','DF','32','',TO_DATE('06-MAY-1993','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','181','72');
INSERT INTO player VALUES  ('2009139','정은석','K03','JEONG,  EUNSEOK','','2009','DF','5','',TO_DATE('14-MAR-1982','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','185','80');
INSERT INTO player VALUES  ('2009030','최민서','K03','CHOI,  MINSEO','','2009','DF','3','',TO_DATE('24-AUG-1986','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'2','180','78');
INSERT INTO player VALUES  ('2012064','성종현','K03','SUNG,  JONGHUN','','2012','DF','34','',TO_DATE('02-APR-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','74');
INSERT INTO player VALUES  ('2008468','싸빅','K03','Jasenko  Sabitovic','','2007','DF','4','',TO_DATE('29-MAR-1983','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','185','78');
INSERT INTO player VALUES  ('2007277','오명관','K03','OH,  MYUNGKWAN','','2008','DF','15','',TO_DATE('29-APR-1984','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','185','76');
INSERT INTO player VALUES  ('2012063','김동식','K03','KIM,  DONGSIK','','2012','MF','33','',TO_DATE('15-MAR-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','183','77');
INSERT INTO player VALUES  ('2012067','김수길','K03','KIM,  SOOKIL','','2012','DF','37','',TO_DATE('09-APR-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','179','69');
INSERT INTO player VALUES  ('2008444','김승엽','K03','KIM,  SEUNGYUB','','2008','DF','12','',TO_DATE('12-OCT-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','180','74');
INSERT INTO player VALUES  ('2007101','김종화','K03','','','','DF','25','',TO_DATE('04-APR-1984','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','182','76');
INSERT INTO player VALUES  ('2007190','하석주','K03','HA,  SEOKJU','','2011','DF','17','',TO_DATE('20-FEB-1978','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','174','71');
INSERT INTO player VALUES  ('2010065','허제정','K03','HEO,  JAEJUNG','','2010','DF','29','',TO_DATE('02-JUN-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','175','70');
INSERT INTO player VALUES  ('2007096','홍명보','K03','HONG,  MYUNGBO','','2012','DF','20','',TO_DATE('12-FEB-1979','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','181','72');
INSERT INTO player VALUES  ('2008472','정기남','K03','JEONG,  KINAM','','2010','MF','6','',TO_DATE('18-JAN-1981','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'1','174','72');
INSERT INTO player VALUES  ('2011059','정상록','K03','JEONG,  SANGROK','','2011','MF','14','',TO_DATE('25-FEB-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','173','63');
INSERT INTO player VALUES  ('2011068','나희근','K03','NA,  HEEKEUN','','2011','FW','22','',TO_DATE('05-MAY-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','72');
INSERT INTO player VALUES  ('2012133','레오','K03','','','','MF','45','',TO_DATE('22-OCT-1984','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','179','74');
INSERT INTO player VALUES  ('2012124','메도','K03','Medvid  Ivan','','2012','MF','44','',TO_DATE('13-OCT-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'1','180','78');
INSERT INTO player VALUES  ('2012068','최길영','K03','CHOI,  KILYOUNG','','2012','MF','38','',TO_DATE('04-FEB-1990','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','172','64');
INSERT INTO player VALUES  ('2008203','최상인','K03','CHOI,  SANGIN','','2005','DF','27','',TO_DATE('10-MAR-1986','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','174','63');
INSERT INTO player VALUES  ('2011131','옐라','K03','Josko  Jelicic','','2012','MF','8','',TO_DATE('05-JAN-1981','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','184','79');
INSERT INTO player VALUES  ('2011061','유현구','K03','YOU,  HYUNGOO','','2011','MF','26','',TO_DATE('25-JAN-1993','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','170','68');
INSERT INTO player VALUES  ('2009033','김기부','K03','KIM,  KIBU','','2009','MF','18','',TO_DATE('16-MAR-1986','DD_MON_YYYY','NLS_DATE_LANGUAGE = AMERICAN'),'2','183','76');
INSERT INTO player VALUES  ('2012070','김상인','K03','KIM,  SANGIN','','2012','DF','40','',TO_DATE('11-JUL-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','70');
INSERT INTO player VALUES  ('2011062','김정운','K03','KIM,  JUNGWOON','','2011','MF','19','',TO_DATE('19-APR-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','70');
INSERT INTO player VALUES  ('2012071','김중규','K03','KIM,  JUNGJYU','','2012','MF','42','',TO_DATE('06-JUN-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','170','64');
INSERT INTO player VALUES  ('2012066','김창호','K03','KIM,  CHANGHO','','2012','MF','36','',TO_DATE('15-MAR-1991','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','175','75');
INSERT INTO player VALUES  ('2011063','이종범','K03','LEE,  JONGBUM','','2011','MF','24','',TO_DATE('27-MAR-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','68');
INSERT INTO player VALUES  ('2012061','남익경','K03','NAM,  IKKYUNG','','2012','MF','30','',TO_DATE('26-JAN-1993','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','177','70');
INSERT INTO player VALUES  ('2011064','윤보영','K03','YOON,  BOYOUNG','','2011','FW','23','',TO_DATE('29-APR-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','177','63');
INSERT INTO player VALUES  ('2008443','김동국','K03','KIM,  DONGGOOK','','2008','FW','10','',TO_DATE('29-APR-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','185','80');
INSERT INTO player VALUES  ('2012060','박종완','K03','PARK,  JONGWAN','','2012','DF','28','',TO_DATE('05-AUG-1993','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','188','82');
INSERT INTO player VALUES  ('2012059','김징요','K03','Jorge  Claudio','','2011','FW','7','브라질',TO_DATE('01-OCT-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','174','70');
INSERT INTO player VALUES  ('2010044','이철우','K03','LEE,  CHULWOO','','2010','FW','9','',TO_DATE('30-NOV-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','185','78');
INSERT INTO player VALUES  ('2011057','코난','K03','Goram  Petreski','','2010','FW','11','',TO_DATE('23-MAY-1982','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','180','76');
INSERT INTO player VALUES  ('2000095','정민규','K03','JEONG,  MINJYU','','2012','MF','35','',TO_DATE('29-SEP-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','71');
INSERT INTO player VALUES  ('2000062','제형진','K01','JAE,  HYUNGJIN','','2012','DF','38','',TO_DATE('25-JUN-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','179','75');
INSERT INTO player VALUES  ('2000063','곽기훈','K01','KWAK,  KIHOON','','2012','FW','33','',TO_DATE('05-NOV-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','177','72');
INSERT INTO player VALUES  ('2000064','최민영','K01','CHOI,  MINYOUNG','','2010','FW','37','',TO_DATE('07-MAR-1991','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','174','67');
INSERT INTO player VALUES  ('2000071','김회택','K07','','','','DF','','',TO_DATE('11-OCT-1976','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','','');
INSERT INTO player VALUES  ('2000072','서현옥','K07','','','','DF','','',TO_DATE('27-OCT-1979','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','','');
INSERT INTO player VALUES  ('2000073','정상호','K07','','','','DF','','',TO_DATE('05-OCT-1974','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','','');
INSERT INTO player VALUES  ('2000074','최철우','K07','','','','DF','','',TO_DATE('29-SEP-1975','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','','');
INSERT INTO player VALUES  ('2012081','정영광','K07','','','','GK','41','',TO_DATE('28-JUN-1993','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','185','80');
INSERT INTO player VALUES  ('2007227','최종문','K07','','','','GK','1','',TO_DATE('02-OCT-1980','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','185','76');
INSERT INTO player VALUES  ('2012088','염동균','K07','','','','GK','31','',TO_DATE('06-SEP-1993','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','189','83');
INSERT INTO player VALUES  ('2012089','김정래','K07','','','','GK','33','',TO_DATE('12-NOV-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','185','81');
INSERT INTO player VALUES  ('2008212','강철','K07','','','','DF','3','',TO_DATE('02-NOV-1981','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','72');
INSERT INTO player VALUES  ('2012077','정강선','K07','','','','DF','37','',TO_DATE('23-MAY-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','180','73');
INSERT INTO player VALUES  ('2012083','정인호','K07','','','','DF','39','',TO_DATE('09-JUN-1993','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','184','79');
INSERT INTO player VALUES  ('2007213','정태영','K07','','','','DF','7','',TO_DATE('08-NOV-1980','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','180','74');
INSERT INTO player VALUES  ('2007209','정현수','K07','','','','DF','21','',TO_DATE('14-FEB-1983','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','176','74');
INSERT INTO player VALUES  ('2012084','정형주','K07','','','','DF','42','',TO_DATE('23-JUN-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','','');
INSERT INTO player VALUES  ('2012085','정홍철','K07','','','','DF','36','',TO_DATE('02-JUN-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','181','69');
INSERT INTO player VALUES  ('2008359','마시엘','K07','','','','DF','24','',TO_DATE('15-MAR-1982','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','177','70');
INSERT INTO player VALUES  ('2011034','김창원','K07','','','','DF','5','',TO_DATE('10-JUL-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','183','75');
INSERT INTO player VALUES  ('2012090','장경진','K07','','','','DF','34','',TO_DATE('31-AUG-1993','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','184','82');
INSERT INTO player VALUES  ('2008425','주영호','K07','','','','DF','6','',TO_DATE('24-OCT-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','185','80');
INSERT INTO player VALUES  ('2012092','홍성요','K07','','','','DF','28','',TO_DATE('26-MAY-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','184','78');
INSERT INTO player VALUES  ('2009115','정경일','K07','','','','MF','49','',TO_DATE('30-AUG-1990','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','170','65');
INSERT INTO player VALUES  ('2011035','정길식','K07','','','','MF','12','',TO_DATE('24-AUG-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','72');
INSERT INTO player VALUES  ('2010030','정남일','K07','','','','MF','4','',TO_DATE('14-MAR-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','182','76');
INSERT INTO player VALUES  ('2010032','정대욱','K07','','','','MF','18','',TO_DATE('02-APR-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','182','73');
INSERT INTO player VALUES  ('2007210','정도근','K07','','','','MF','10','',TO_DATE('02-MAR-1982','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','181','69');
INSERT INTO player VALUES  ('2012078','정동희','K07','','','','MF','38','',TO_DATE('06-MAY-1993','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','174','64');
INSERT INTO player VALUES  ('2007102','정명곤','K07','','','','MF','2','',TO_DATE('15-APR-1984','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','177','73');
INSERT INTO player VALUES  ('2012079','정성진','K07','','','','MF','44','',TO_DATE('20-JAN-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','178','68');
INSERT INTO player VALUES  ('2012080','정승현','K07','','','','MF','26','',TO_DATE('17-AUG-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','181','71');
INSERT INTO player VALUES  ('2012082','정요환','K07','','','','MF','25','',TO_DATE('23-MAY-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','170','62');
INSERT INTO player VALUES  ('2009100','정정겸','K07','','','','MF','13','',TO_DATE('09-JUN-1986','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','172','65');
INSERT INTO player VALUES  ('2008428','정종현','K07','','','','MF','11','',TO_DATE('10-JUL-1983','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','173','68');
INSERT INTO player VALUES  ('2012086','노병준','K07','','','','MF','22','',TO_DATE('29-SEP-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','177','67');
INSERT INTO player VALUES  ('2012087','최종우','K07','','','','MF','43','',TO_DATE('11-APR-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','176','69');
INSERT INTO player VALUES  ('2007305','조진원','K07','','','','MF','9','',TO_DATE('27-SEP-1984','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','176','75');
INSERT INTO player VALUES  ('2012132','실바','K07','','','','MF','45','',TO_DATE('20-JUN-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','173','67');
INSERT INTO player VALUES  ('2010031','윤용구','K07','','','','MF','15','',TO_DATE('08-AUG-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','168','60');
INSERT INTO player VALUES  ('2011127','김반','K07','','','','MF','14','',TO_DATE('27-OCT-1984','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','174','69');
INSERT INTO player VALUES  ('2011038','김영수','K07','','','','MF','30','',TO_DATE('30-JUL-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','175','65');
INSERT INTO player VALUES  ('2008423','임관식','K07','','','','MF','29','',TO_DATE('28-JUL-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','172','68');
INSERT INTO player VALUES  ('2011036','이정호','K07','','','','MF','23','',TO_DATE('06-APR-1988','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','176','71');
INSERT INTO player VALUES  ('2011039','하기윤','K07','','','','MF','32','',TO_DATE('10-MAR-1992','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','180','65');
INSERT INTO player VALUES  ('2010003','정대철','K07','','','','FW','20','',TO_DATE('26-AUG-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','183','78');
INSERT INTO player VALUES  ('2010154','꼬레아','K07','','','','FW','16','',TO_DATE('23-AUG-1984','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','172','70');
INSERT INTO player VALUES  ('2007214','노상래','K07','','','','FW','8','',TO_DATE('15-DEC-1980','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','175','74');
INSERT INTO player VALUES  ('2009149','성한수','K07','','','','FW','40','',TO_DATE('10-MAR-1986','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'2','177','69');
INSERT INTO player VALUES  ('2009161','세자르','K07','','','','FW','17','',TO_DATE('09-DEC-1983','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','180','78');
INSERT INTO player VALUES  ('2012032','조병호','K07','','','','FW','27','',TO_DATE('26-APR-1987','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','177','75');
INSERT INTO player VALUES  ('2011120','찌코','K07','','','','FW','27','',TO_DATE('26-JAN-1985','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','180','67');
INSERT INTO player VALUES  ('2010037','하성룡','K07','','','','FW','35','',TO_DATE('03-FEB-1992','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','179','68');
INSERT INTO player VALUES  ('2012091','홍복표','K07','','','','FW','19','',TO_DATE('28-OCT-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','182','73');
INSERT INTO player VALUES  ('2000081','김윤환','K05','','','','DF','','',TO_DATE('24-MAY-1971','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','','');
INSERT INTO player VALUES  ('2000082','정은철','K05','','','','DF','','',TO_DATE('26-MAY-1978','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','','');
INSERT INTO player VALUES  ('2000083','김경춘','K05','','','','DF','','',TO_DATE('14-APR-1979','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','','');
INSERT INTO player VALUES  ('2000084','최동우','K05','','','','DF','','',TO_DATE('03-NOV-1980','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','','');
INSERT INTO player VALUES  ('2000085','전명구','K05','','','','DF','','',TO_DATE('16-MAR-1979','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','','');
INSERT INTO player VALUES  ('2000086','박경치','K05','','','','DF','','',TO_DATE('06-JAN-1979','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','','');
INSERT INTO player VALUES  ('2007106','정이섭','K05','JEONG,  ISUB','쾌남','2012','GK','45','',TO_DATE('06-APR-1984','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','185','78');
INSERT INTO player VALUES  ('2012007','최관민','K05','CHOI,  KWANMIN','','2012','GK','31','',TO_DATE('26-MAY-1989','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','188','85');
INSERT INTO player VALUES  ('2008179','최동우','K05','','','','GK','60','',TO_DATE('03-NOV-1980','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','187','78');
INSERT INTO player VALUES  ('2008138','김용발','K05','KIM,  YONGBAL','','2004','GK','18','',TO_DATE('15-MAR-1983','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','183','77');
INSERT INTO player VALUES  ('2012006','김창민','K05','KIM,  CHANGMIN','고릴라','2012','GK','1','',TO_DATE('25-JAN-1990','DD_MON_YYYY','NLS_DATE_LANGUAGE =  AMERICAN'),'1','191','87');"""
    
    # 출력 경로
    output_path = Path(__file__).parent.parent / "data" / "soccer" / "players.jsonl"
    
    # 변환 실행
    players = convert_sql_to_jsonl(sql_content, output_path)
    
    # 첫 5개 샘플 출력
    print(f"\n[INFO] First 5 samples:")
    for i, player in enumerate(players[:5], 1):
        print(f"\n[Sample {i}]")
        print(json.dumps(player, ensure_ascii=False, indent=2))
