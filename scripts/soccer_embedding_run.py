import os
from pathlib import Path
import json
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "soccer"
OUTPUT_DIR = DATA_DIR / "embeddings"

def read_jsonl(file_path):
    records = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            records.append(json.loads(line))
    return records

def build_embedding_string(record):
    """검색용 텍스트: player_id(선수코드)와 주요 필드로 구성."""
    pid = record.get("player_id") or record.get("id")
    pid = pid if isinstance(pid, str) else str(pid)
    parts = [f"선수 {record.get('player_name', '')}", f"코드 {pid}"]
    if record.get("e_player_name"):
        parts.append(str(record["e_player_name"]))
    if record.get("position"):
        parts.append(f"포지션 {record['position']}")
    if record.get("team_id"):
        parts.append(f"소속팀 {record['team_id']}")
    if record.get("nation"):
        parts.append(str(record["nation"]))
    if record.get("back_no"):
        parts.append(f"등번호 {record['back_no']}")
    if record.get("nickname"):
        parts.append(f"별명 {record['nickname']}")
    return " ".join(parts)

def generate_embeddings(records):
    model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    embeddings = []
    for record in records:
        embedding_string = build_embedding_string(record)
        embedding = model.encode([embedding_string]).tolist()[0]
        embeddings.append({**record, "embedding": embedding})
    return embeddings

def write_embeddings_to_jsonl(embeddings, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as file:
        for embedding in embeddings:
            file.write(json.dumps(embedding) + '\n')

def main():
    file_path = DATA_DIR / "players.jsonl"
    records = read_jsonl(file_path)
    embeddings = generate_embeddings(records)
    output_path = OUTPUT_DIR / "players_embeddings.jsonl"
    write_embeddings_to_jsonl(embeddings, output_path)

if __name__ == "__main__":
    main()
