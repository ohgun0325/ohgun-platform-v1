from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from pathlib import Path


# 프로젝트 루트 기준 EXAONE 로컬 모델 디렉터리
# (루트/models/exaone-2.4b 에 있다고 알려줬으므로 그 경로를 사용)
ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "models" / "exaone-2.4b"
model_path = str(MODEL_DIR)

# Exaone이 생성한 임베딩 ORM 코드가 저장될 파일
output_file = "app/domain/koica/models/oda_term_embeddings.py"

# KOICA ODA 용어 베이스 테이블 ORM 파일
base_model_file = Path("app/domain/koica/models/oda_term.py")
base_model_content = base_model_file.read_text(encoding="utf-8")


prompt = f"""너는 이 KOICA 프로젝트에서 SQLAlchemy ORM "베이스 테이블" 클래스에 대해
대응되는 "임베딩 벡터 테이블" ORM 클래스를 생성하는 코드 어시스턴트이다.

=== 베이스 모델 코드 ===
{base_model_content}

=== 요구사항 ===
1. Base 클래스:
   from app.domain.koica.bases import Base
   를 사용한다.

2. 임베딩 테이블 클래스 이름:
   - <베이스클래스명>Embedding 으로 한다.
   - 예: OdaTerm -> OdaTermEmbedding

3. 테이블 이름(__tablename__):
   - <베이스테이블명>_embeddings 로 한다.
   - 예: oda_terms -> oda_terms_embeddings

4. 컬럼 설계:
   - id: BigInteger, primary_key=True, autoincrement=True,
     comment='임베딩 레코드 고유 식별자'
   - 베이스 테이블 PK(id)에 대한 FK:
     oda_term_id = Column(BigInteger, ForeignKey("oda_terms.id"),
                          nullable=False,
                          comment="OdaTerm ID")
   - content: Text, nullable=False,
     comment='임베딩 생성에 사용된 원본 텍스트'
   - embedding: Vector(1536), nullable=False,
     comment='1536차원 임베딩 벡터 (Exaone)'
   - created_at: DateTime(timezone=True),
     server_default=func.now(), nullable=False,
     comment='레코드 생성 시간'

5. 사용 라이브러리 및 import 규칙:
   - from sqlalchemy import Column, BigInteger, Text, DateTime, ForeignKey
   - from sqlalchemy.orm import relationship
   - from sqlalchemy.sql import func
   - from pgvector.sqlalchemy import Vector
   - from app.domain.koica.bases import Base

6. 관계 설정:
   - 임베딩 테이블 쪽:
     oda_term = relationship("OdaTerm", back_populates="embeddings")
   - (주석으로) 베이스 테이블 쪽에 추가해야 할 속성도 제안하라:
     embeddings = relationship("OdaTermEmbedding",
                               back_populates="oda_term",
                               cascade="all, delete-orphan")

7. 코딩 스타일:
   - 베이스 모델 파일의 코딩 스타일(주석 형식, Column 정의 방식 등)을 최대한 따라라.
   - 모든 Column에 comment 를 채운다.
   - __tablename__ 문자열은 소문자+스네이크케이스 복수형으로 맞춘다.

8. 출력 형식:
   - import 문부터 시작하는 완전한 Python 파일 1개를 생성한다.
   - Python 코드만 출력하고, 불필요한 설명 문장은 넣지 않는다.
"""


print("[ExaOne] 모델 로딩 중...")
tokenizer = AutoTokenizer.from_pretrained(
    model_path,
    trust_remote_code=True,
    local_files_only=True,  # 로컬 디렉터리만 사용 (HF Hub로 나가지 않도록)
)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    dtype=torch.float16,
    device_map="auto",
    trust_remote_code=True,
    local_files_only=True,
)

print("[ExaOne] 코드 생성 중...")
messages = [
    {
        "role": "system",
        "content": "You are EXAONE model from LG AI Research, a helpful assistant specialized in generating Python SQLAlchemy ORM code.",
    },
    {
        "role": "user",
        "content": prompt,
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
    max_new_tokens=1200,
    do_sample=True,
    temperature=0.7,
    top_p=0.9,
    eos_token_id=tokenizer.eos_token_id,
    pad_token_id=tokenizer.pad_token_id,
)

generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

# 생성된 코드만 추출
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
    generated_code = generated_text.strip()

print("\n=== 생성된 코드 ===")
print(generated_code)
print("\n=== 코드 생성 완료 ===\n")

output_path = Path(output_file)
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(generated_code, encoding="utf-8")

print(f"[완료] 코드가 {output_file}에 저장되었습니다.")

