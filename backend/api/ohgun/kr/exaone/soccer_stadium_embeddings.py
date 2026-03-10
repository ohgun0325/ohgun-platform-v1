"""Soccer 도메인: Exaone이 경기장(stadium) 엠베딩 생성용 Python 스크립트 코드를 생성한다.

Cursor 터미널에서 (반드시 프로젝트 루트에서 실행):
  1) python app/exaone/soccer_stadium_embeddings.py  → Exaone이 코드 생성, scripts/stadium_embedding_run.py 저장
  2) python scripts/stadium_embedding_run.py         → 생성된 스크립트로 실제 엠베딩 실행
"""

from __future__ import annotations

import os
from pathlib import Path

# 프로젝트 루트 (app/exaone/soccer_stadium_embeddings.py 기준 2단계 상위)
ROOT = Path(__file__).resolve().parents[2]

_default_model = ROOT / "models" / "exaone-2.4b"
MODEL_DIR = Path(os.environ.get("EXAONE_MODEL_DIR", str(_default_model)))
if not MODEL_DIR.is_absolute():
    MODEL_DIR = ROOT / MODEL_DIR

DATA_SOCCER = ROOT / "data" / "soccer"

OUTPUT_SCRIPT = ROOT / "scripts" / "stadium_embedding_run.py"


def build_prompt() -> str:
    """경기장 JSONL을 기반으로 Exaone이 전체 경기장 임베딩 스크립트를 생성하도록 유도."""
    data_root = str(DATA_SOCCER).replace("\\", "/")

    return f"""Write one complete, runnable Python script. Do NOT use pass or leave any function empty.

Script must:
1. Define ROOT = Path(__file__).resolve().parents[1], DATA_DIR = ROOT / "data" / "soccer", OUTPUT_DIR = DATA_DIR / "embeddings"
2. Read JSONL from {data_root}/stadium.jsonl (open file, for each non-empty line: json.loads(line) to a list of dicts)
3. For each stadium record dict, build one string like "id: <id> | stadium_name: <stadium_name> | address: <address> | seat_count: <seat_count> | ..." for embedding
4. Use SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"), call model.encode(texts) once for the full list of texts
5. Create OUTPUT_DIR if needed, write {data_root}/embeddings/stadiums_embeddings.jsonl: each line is json.dumps({{"id": stadium_id, "stadium_name": stadium_name, "embedding": list_of_floats}})
6. Script runs when executed: if __name__ == "__main__": main()

Required:
- Implement every function fully. No pass. No placeholder.
- Output only Python code, starting with "import" or "from"."""


def main() -> None:
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
    except ImportError:
        print("transformers, torch 가 필요합니다: pip install transformers torch")
        return

    model_path = str(MODEL_DIR)
    print(f"[경로] 프로젝트 루트: {{ROOT}}")
    print(f"[경로] Exaone 모델: {{model_path}} (기본: models/exaone-2.4b)")
    print(f"[경로] 생성 스크립트 저장: {{OUTPUT_SCRIPT}}")

    if not MODEL_DIR.exists():
        print(f"\\n[오류] Exaone 모델 경로가 없습니다: {{model_path}}")
        print("       프로젝트 루트에 models/exaone-2.4b 를 두거나,")
        print("       환경변수 EXAONE_MODEL_DIR 로 경로를 지정하세요.")
        return

    prompt = build_prompt()

    print("\\n[ExaOne] 모델 로딩 중...")
    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        trust_remote_code=True,
        local_files_only=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
        local_files_only=True,
    )

    print("[ExaOne] Stadium 엠베딩 스크립트 코드 생성 중...")
    messages = [
        {
            "role": "system",
            "content": "You are EXAONE from LG AI Research. You are an expert Python programmer. Generate complete, runnable Python code with imports, functions, and main block. Output ONLY the code without explanations.",
        },
        {
            "role": "user",
            "content": prompt
            + "\\n\\nIMPORTANT: Start your response with 'import' or 'from' immediately. Do not write any explanation text before the code.",
        },
    ]

    input_ids = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
    ).to(model.device)

    outputs = model.generate(
        input_ids,
        max_new_tokens=2048,
        do_sample=False,
        temperature=1.0,
        top_p=1.0,
        eos_token_id=tokenizer.eos_token_id,
        pad_token_id=tokenizer.pad_token_id,
    )

    generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

    if "```python" in generated_text:
        code_start = generated_text.find("```python") + 9
        code_end = generated_text.find("```", code_start)
        generated_code = (
            generated_text[code_start:code_end].strip()
            if code_end != -1
            else generated_text[code_start:].strip()
        )
    elif "```" in generated_text:
        code_start = generated_text.find("```") + 3
        code_end = generated_text.find("```", code_start)
        generated_code = (
            generated_text[code_start:code_end].strip()
            if code_end != -1
            else generated_text[code_start:].strip()
        )
    else:
        generated_code = generated_text.strip()

    print("\\n=== 생성된 코드 (앞 500자) ===")
    print(generated_code[:500] + ("..." if len(generated_code) > 500 else ""))
    print("\\n=== 코드 생성 완료 ===\\n")

    OUTPUT_SCRIPT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_SCRIPT.write_text(generated_code, encoding="utf-8")
    print(f"[완료] 코드가 저장되었습니다: {{OUTPUT_SCRIPT}}")
    print("       다음 단계: 반드시 프로젝트 루트에서 실행하세요.")
    print(f"         cd {{ROOT}}")
    print("         python scripts/stadium_embedding_run.py")


if __name__ == "__main__":
    main()

