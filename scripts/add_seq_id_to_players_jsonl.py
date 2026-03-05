"""players.jsonl 각 행에 1000부터 1씩 증가하는 id(BigInt)를 맨 앞에 추가. 기존 id는 player_id로 유지."""
import json
import sys
from pathlib import Path

def main():
    path = Path(__file__).parent.parent / "data" / "soccer" / "players.jsonl"
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    start_id = 1000
    lines_out = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            old_id = obj.pop("id", None)
            new_obj = {"id": start_id + i}
            if old_id is not None:
                new_obj["player_id"] = old_id
            new_obj.update(obj)
            lines_out.append(json.dumps(new_obj, ensure_ascii=False))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out) + "\n")
    print(f"Applied sequential id ({start_id}..{start_id + len(lines_out) - 1}) to {len(lines_out)} rows.")


if __name__ == "__main__":
    main()
