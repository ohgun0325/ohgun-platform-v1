"""SQL INSERT INTO player 문을 파싱하여 players.jsonl 형식으로 출력."""
import re
import json
import sys

MONTH = {
    "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05", "JUN": "06",
    "JUL": "07", "AUG": "08", "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12",
}


def parse_date(s: str) -> str | None:
    if not s or not s.strip():
        return None
    s = s.strip().upper()
    m = re.match(r"(\d{1,2})-([A-Z]{3})-(\d{4})", s)
    if m:
        dd, mon, yyyy = m.group(1), m.group(2), m.group(3)
        mm = MONTH.get(mon, "01")
        return f"{yyyy}-{mm}-{dd.zfill(2)}"
    return None


def to_null(s: str) -> str | None:
    if s is None or (isinstance(s, str) and not s.strip()):
        return None
    return s.strip() or None


# VALUES  ('id','name','team_id','e_name','nick','join','pos','back','nation',TO_DATE('DD-MON-YYYY',...),'solar','height','weight');
PAT = re.compile(
    r"VALUES\s*\(\s*"
    r"'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*'([^']*)',\s*"
    r"TO_DATE\s*\(\s*'([^']*)'[^)]*\)\s*,\s*'([^']*)',\s*'([^']*)',\s*'([^']*)'\s*\)",
    re.IGNORECASE,
)


def parse_line(line: str) -> dict | None:
    line = line.strip()
    if "INSERT" not in line or "player" not in line:
        return None
    m = PAT.search(line)
    if not m:
        return None
    (pid, player_name, team_id, e_player_name, nickname, join_yyyy, position, back_no, nation,
     birth_s, solar, height, weight) = m.groups()
    return {
        "id": pid,
        "player_name": player_name,
        "team_id": team_id,
        "e_player_name": to_null(e_player_name),
        "nickname": to_null(nickname),
        "join_yyyy": to_null(join_yyyy),
        "position": position or None,
        "back_no": to_null(back_no),
        "nation": to_null(nation),
        "birth_date": parse_date(birth_s),
        "solar": to_null(solar),
        "height": to_null(height),
        "weight": to_null(weight),
    }


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            raw = f.read()
    else:
        raw = sys.stdin.read()
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    records = []
    for line in lines:
        d = parse_line(line)
        if d:
            records.append(json.dumps(d, ensure_ascii=False))
    # --append <jsonl_path>: 기존 파일 끝에 추가
    if len(sys.argv) >= 4 and sys.argv[2] == "--append":
        out_path = sys.argv[3]
        with open(out_path, "r", encoding="utf-8") as f:
            existing = f.read().rstrip("\n")
        with open(out_path, "w", encoding="utf-8") as f:
            if existing:
                f.write(existing + "\n")
            f.write("\n".join(records) + "\n")
        return
    for r in records:
        print(r)


if __name__ == "__main__":
    main()
