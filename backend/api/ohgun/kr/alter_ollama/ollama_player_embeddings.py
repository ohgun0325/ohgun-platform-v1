from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from pathlib import Path

model_path = "artifacts/base-models/exaone-2.4b"
output_file = "app/domain/v10/soccer/models/bases/player_embeddings.py"

# players.py 파일 읽기
players_file = Path("app/domain/v10/soccer/models/bases/players.py")
players_content = players_file.read_text(encoding="utf-8")

# 프롬프트 작성
prompt = f"""다음 SQLAlchemy Player 모델을 참고하여 PlayerEmbedding ORM 클래스를 작성하세요.

=== Player 모델 코드 ===
{players_content}

=== Alembic 마이그레이션 테이블 스키마 ===
테이블명: players_embeddings
컬럼:
- id: BigInteger, PK, autoincrement=True, nullable=False, comment='임베딩 레코드 고유 식별자'
- player_id: BigInteger, FK -> players.id, nullable=False, ondelete='CASCADE', comment='선수 ID'
- content: Text, nullable=False, comment='임베딩 생성에 사용된 원본 텍스트'
- embedding: Vector(768), nullable=False, comment='768차원 임베딩 벡터 (KoElectra)'
- created_at: TIMESTAMP(timezone=True), server_default=now(), nullable=False, comment='레코드 생성 시간'

=== 요구사항 ===
1. Base 클래스: from app.domain.shared.bases import Base 사용
2. pgvector: from pgvector.sqlalchemy import Vector 사용
3. SQLAlchemy imports: Column, BigInteger, Text, ForeignKey, TIMESTAMP, relationship
4. 타임스탬프: from sqlalchemy.sql import func 사용하여 server_default=func.now() 설정
5. relationship: player (back_populates="embeddings") 설정
6. players.py의 코딩 스타일과 일관성 유지 (주석 형식, Column 정의 방식 등)
7. 모든 Column에 comment 추가
8. __tablename__ = "players_embeddings" 사용
9. Python 코드만 출력 (주석이나 설명 없이 순수 코드만)
10. docstring은 Player 모델과 유사한 형식으로 작성

=== 출력 형식 ===
파일 전체 코드를 출력하세요. import 문부터 시작하여 완전한 Python 파일 형태로 작성하세요."""

# 모델 로드
print("[ExaOne] 모델 로딩 중...")
tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True
)

print("[ExaOne] 코드 생성 중...")
# ExaOne 모델의 chat template 사용 (권장 방식)
messages = [
    {
        "role": "system",
        "content": "You are EXAONE model from LG AI Research, a helpful assistant specialized in generating Python SQLAlchemy ORM code."
    },
    {
        "role": "user",
        "content": prompt
    }
]

input_ids = tokenizer.apply_chat_template(
    messages,
    tokenize=True,
    add_generation_prompt=True,
    return_tensors="pt"
).to(model.device)

outputs = model.generate(
    input_ids,
    max_new_tokens=1200,
    do_sample=True,
    temperature=0.7,
    top_p=0.9,
    eos_token_id=tokenizer.eos_token_id,
    pad_token_id=tokenizer.pad_token_id
)

# 생성된 코드 추출
generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

# 응답에서 사용자 프롬프트 부분 제거 (chat template 사용 시)
if "assistant" in generated_text.lower() or "답변" in generated_text:
    # chat template 응답에서 실제 코드 부분만 추출
    if "```python" in generated_text:
        code_start = generated_text.find("```python") + 9
        code_end = generated_text.find("```", code_start)
        if code_end != -1:
            generated_code = generated_text[code_start:code_end].strip()
        else:
            generated_code = generated_text[code_start:].strip()
    elif "```" in generated_text:
        code_start = generated_text.find("```") + 3
        code_end = generated_text.find("```", code_start)
        if code_end != -1:
            generated_code = generated_text[code_start:code_end].strip()
        else:
            generated_code = generated_text[code_start:].strip()
    else:
        # assistant 응답 부분만 추출
        if "assistant" in generated_text.lower():
            parts = generated_text.split("assistant", 1)
            if len(parts) > 1:
                generated_code = parts[-1].strip()
            else:
                generated_code = generated_text
        else:
            generated_code = generated_text
else:
    generated_code = generated_text

print("\n=== 생성된 코드 ===")
print(generated_code)
print("\n=== 코드 생성 완료 ===\n")

# 파일에 저장
output_path = Path(output_file)
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(generated_code, encoding="utf-8")

print(f"[완료] 코드가 {output_file}에 저장되었습니다.")
