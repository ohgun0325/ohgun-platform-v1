"""Exaone 모델 훈련 서비스

로컬 Exaone-2.4b 모델을 사용하여 SFT(Supervised Fine-Tuning)를 수행합니다.
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    DataCollatorForLanguageModeling,
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    TaskType,
)
from datasets import Dataset, DatasetDict

# OpenMP 라이브러리 중복 문제 해결
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

try:
    from trl import SFTTrainer
    TRL_AVAILABLE = True
except ImportError:
    try:
        from trl.trainer import SFTTrainer
        TRL_AVAILABLE = True
    except ImportError:
        try:
            from trl.trainer.sft_trainer import SFTTrainer
            TRL_AVAILABLE = True
        except ImportError:
            TRL_AVAILABLE = False
            SFTTrainer = None

from transformers import Trainer


def force_float16_recursive(module: torch.nn.Module) -> None:
    """모듈의 모든 파라미터와 버퍼를 재귀적으로 Float16으로 변환합니다.

    Args:
        module: 변환할 모듈
    """
    for name, param in module.named_parameters(recurse=False):
        if param.dtype == torch.bfloat16:
            param.data = param.data.to(torch.float16)

    for name, buffer in module.named_buffers(recurse=False):
        if buffer.dtype == torch.bfloat16:
            buffer.data = buffer.data.to(torch.float16)

    # 재귀적으로 모든 서브모듈 처리
    for child in module.children():
        force_float16_recursive(child)


class ExaoneTrainer:
    """Exaone 모델 훈련 클래스

    로컬 Exaone-2.4b 모델을 QLoRA 방식으로 Fine-tuning합니다.
    """

    def __init__(
        self,
        model_path: str,
        output_dir: str = "models/exaone-spam-classifier",
        use_4bit: bool = True,
        device_map: str = "auto",
        torch_dtype: str = "float16",
        use_fp16_training: bool = False,  # FP16 Mixed Precision 사용 여부 (BFloat16 에러 방지를 위해 기본값 False)
    ):
        """Exaone 훈련 서비스 초기화

        Args:
            model_path: Exaone 모델 경로 (models/exaone-2.4b)
            output_dir: 훈련된 모델 저장 경로
            use_4bit: 4-bit 양자화 사용 여부
            device_map: 디바이스 매핑 전략
            torch_dtype: 모델 데이터 타입
            use_fp16_training: FP16 Mixed Precision 사용 여부 (False면 float32로 학습, 메모리는 더 사용하지만 안정적)
        """
        self.model_path = Path(model_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_4bit = use_4bit
        self.device_map = device_map
        self.torch_dtype_str = torch_dtype

        # torch_dtype 변환 (BFloat16은 현재 환경에서 지원되지 않으므로 Float16으로 강제)
        if torch_dtype == "float16":
            self.torch_dtype = torch.float16
        elif torch_dtype == "float32":
            self.torch_dtype = torch.float32
        elif torch_dtype == "bfloat16":
            print("[WARNING] BFloat16은 현재 CUDA 환경에서 지원되지 않습니다. Float16으로 변경합니다.")
            self.torch_dtype = torch.float16  # BFloat16 요청 시 Float16으로 강제 변환
        else:
            self.torch_dtype = torch.float16

        # BitsAndBytes 설정
        self.bnb_config = None
        if use_4bit and torch.cuda.is_available():
            self.bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
            )

        self.model = None
        self.tokenizer = None
        self.peft_model = None
        self.is_loaded = False
        self.use_fp16_training = use_fp16_training  # FP16 Mixed Precision 사용 여부

    def load_model(self) -> None:
        """모델과 토크나이저를 로드하고 QLoRA를 준비합니다."""
        if self.is_loaded:
            print("[WARNING] 모델이 이미 로드되어 있습니다.")
            return

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"모델을 찾을 수 없습니다: {self.model_path}\n"
                f"models/exaone-2.4b 폴더에 모델 파일이 있는지 확인하세요."
            )

        print("=" * 60)
        print("[ExaoneTrainer] 모델 로드 중...")
        print("=" * 60)
        print(f"경로: {self.model_path}")

        # GPU 감지 정보 출력
        import torch
        cuda_available = torch.cuda.is_available()
        print(f"CUDA 사용 가능: {cuda_available}")
        if cuda_available:
            print(f"CUDA 버전: {torch.version.cuda}")
            print(f"GPU 개수: {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
                print(f"    메모리: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
        else:
            print("⚠️  CUDA를 사용할 수 없습니다. CPU로 실행됩니다.")
            print("   GPU를 사용하려면:")
            print("   1. NVIDIA 드라이버 설치 확인")
            print("   2. Docker에서 GPU 지원 확인 (nvidia-docker)")
            print("   3. docker-compose.yml의 GPU 설정 확인")

        # device_map 결정
        if self.device_map == "auto" and cuda_available:
            final_device = "cuda (auto)"
        elif self.device_map != "cpu" and cuda_available:
            final_device = f"cuda ({self.device_map})"
        else:
            final_device = "cpu"

        print(f"디바이스: {final_device}")
        print(f"4-bit 양자화: {self.use_4bit and cuda_available}")
        print()

        # 토크나이저 로드
        print("토크나이저 로드 중...")
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(self.model_path),
            trust_remote_code=True,
        )

        # pad_token 설정
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

        print("토크나이저 로드 완료")

        # 모델 로드
        print("모델 로드 중...")
        model_kwargs = {
            "trust_remote_code": True,
        }

        # GPU 사용 강제 (device_map이 "cpu"가 아닌 경우)
        cuda_available = torch.cuda.is_available()
        force_cpu = self.device_map == "cpu"

        if self.bnb_config and cuda_available and not force_cpu:
            model_kwargs["quantization_config"] = self.bnb_config
            model_kwargs["device_map"] = "auto"
            print("[OK] GPU 사용: 4-bit 양자화 + device_map='auto'")
        else:
            # device_map이 "cpu"가 아니고 CUDA가 사용 가능하면 GPU 사용
            if cuda_available and not force_cpu:
                device = "cuda"
                print(f"[OK] GPU 사용: device_map='{self.device_map}'")
            else:
                device = "cpu"
                if force_cpu:
                    print("⚠️  CPU 사용: device_map이 'cpu'로 설정됨")
                else:
                    print("⚠️  CPU 사용: CUDA를 사용할 수 없음")
            # BFloat16 완전 차단 및 Float16 강제 (CUDA Mixed Precision 호환성)
            if device == "cuda":
                # BFloat16은 완전히 차단하고 Float16으로 강제
                if self.torch_dtype == torch.bfloat16:
                    print("[WARNING] BFloat16 감지됨. Float16으로 강제 변환합니다.")
                    model_kwargs["torch_dtype"] = torch.float16
                else:
                    model_kwargs["torch_dtype"] = self.torch_dtype
                # 추가 안전장치: 명시적으로 Float16으로 설정
                if model_kwargs.get("torch_dtype") != torch.float16 and model_kwargs.get("torch_dtype") != torch.float32:
                    print(f"[WARNING] torch_dtype이 {model_kwargs.get('torch_dtype')}입니다. Float16으로 변경합니다.")
                    model_kwargs["torch_dtype"] = torch.float16
            else:
                model_kwargs["torch_dtype"] = torch.float32
            if device == "cuda" and self.device_map == "auto":
                model_kwargs["device_map"] = "auto"
            elif device == "cuda":
                model_kwargs["device_map"] = self.device_map

        # 모델 로드 전에 torch_dtype을 명시적으로 float16으로 강제 (BFloat16 완전 차단)
        if torch.cuda.is_available():
            if "torch_dtype" in model_kwargs:
                if model_kwargs["torch_dtype"] == torch.bfloat16:
                    print("[WARNING] torch_dtype이 BFloat16입니다. Float16으로 강제 변경합니다.")
                    model_kwargs["torch_dtype"] = torch.float16
                # 추가 안전장치: CUDA 사용 시 항상 float16으로 강제 (float32 제외)
                elif model_kwargs["torch_dtype"] != torch.float32:
                    model_kwargs["torch_dtype"] = torch.float16
            else:
                # torch_dtype이 없으면 명시적으로 float16 추가
                model_kwargs["torch_dtype"] = torch.float16

        self.model = AutoModelForCausalLM.from_pretrained(
            str(self.model_path),
            **model_kwargs
        )

        # 모델 dtype 확인 및 변환 (BFloat16 -> Float16)
        # 주의: bitsandbytes 양자화 모델은 로드 후 dtype 변경 불가능
        if torch.cuda.is_available():
            # bitsandbytes 모델인지 확인 (4-bit 양자화 사용 시)
            is_bitsandbytes_model = self.use_4bit and self.bnb_config is not None

            if is_bitsandbytes_model:
                # bitsandbytes 모델은 로드 후 dtype 변경 불가능
                # 로드 시점에 이미 올바른 dtype으로 설정되어 있어야 함
                print("[INFO] bitsandbytes 양자화 모델 감지: dtype 변환 건너뜀 (로드 시점 dtype 유지)")

                # BFloat16 파라미터가 있는지 확인만 수행 (변환은 불가능)
                bfloat16_count = sum(1 for p in self.model.parameters() if p.dtype == torch.bfloat16)
                if bfloat16_count > 0:
                    print(f"[WARNING] bitsandbytes 모델에 {bfloat16_count}개의 BFloat16 파라미터가 있습니다.")
                    print("[WARNING] bitsandbytes 모델은 로드 후 dtype 변경이 불가능합니다.")
                    print("[WARNING] 모델 로드 시 torch_dtype을 올바르게 설정했는지 확인하세요.")
                else:
                    first_param_dtype = next(self.model.parameters()).dtype
                    print(f"[OK] 모델 dtype: {first_param_dtype} (BFloat16 없음)")
            else:
                # 일반 모델은 Float16으로 변환 가능
                print("[INFO] 모델을 Float16으로 변환 중...")
                self.model = self.model.to(torch.float16)

                # 재귀적으로 모든 서브모듈의 파라미터와 버퍼를 Float16으로 강제 변환
                print("[INFO] 모든 서브모듈의 BFloat16 파라미터/버퍼를 Float16으로 변환 중...")
                force_float16_recursive(self.model)

                # 최종 확인 및 재시도
                bfloat16_count = sum(1 for p in self.model.parameters() if p.dtype == torch.bfloat16)
                if bfloat16_count > 0:
                    print(f"[WARNING] 여전히 {bfloat16_count}개의 BFloat16 파라미터가 남아있습니다. 재시도합니다.")
                    self.model = self.model.to(torch.float16)
                    force_float16_recursive(self.model)

                first_param_dtype = next(self.model.parameters()).dtype
                print(f"[OK] 최종 모델 dtype: {first_param_dtype} (BFloat16 완전 차단)")

        # QLoRA 준비
        if self.bnb_config:
            print("QLoRA 준비 중...")
            self.model = prepare_model_for_kbit_training(self.model)

        # LoRA 설정
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=16,  # LoRA rank
            lora_alpha=32,  # LoRA alpha
            lora_dropout=0.1,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],  # Exaone attention 모듈
            bias="none",
        )

        # PEFT 모델 적용
        print("LoRA 어댑터 적용 중...")
        self.peft_model = get_peft_model(self.model, lora_config)

        # PEFT 모델도 Float16으로 변환 확인 (BFloat16 완전 차단)
        # 주의: bitsandbytes 양자화 모델은 로드 후 dtype 변경 불가능
        if torch.cuda.is_available():
            try:
                # bitsandbytes 모델인지 확인
                is_bitsandbytes_model = self.use_4bit and self.bnb_config is not None

                if is_bitsandbytes_model:
                    # bitsandbytes 모델은 로드 후 dtype 변경 불가능
                    print("[INFO] bitsandbytes 양자화 모델: PEFT 모델 dtype 변환 건너뜀")

                    # BFloat16 파라미터 확인만 수행
                    bfloat16_count = sum(1 for p in self.peft_model.parameters() if p.dtype == torch.bfloat16)
                    if bfloat16_count > 0:
                        print(f"[WARNING] PEFT 모델에 {bfloat16_count}개의 BFloat16 파라미터가 있습니다.")
                    else:
                        first_param_dtype = next(self.peft_model.parameters()).dtype
                        print(f"[OK] PEFT 모델 dtype: {first_param_dtype} (BFloat16 없음)")
                else:
                    # 일반 모델은 Float16으로 변환 가능
                    print("[INFO] PEFT 모델을 Float16으로 강제 변환 중...")
                    self.peft_model = self.peft_model.to(torch.float16)

                    # 재귀적으로 모든 서브모듈의 파라미터와 버퍼를 Float16으로 강제 변환
                    print("[INFO] PEFT 모델의 모든 서브모듈을 Float16으로 변환 중...")
                    force_float16_recursive(self.peft_model)

                    # 최종 확인 및 재시도
                    bfloat16_count = sum(1 for p in self.peft_model.parameters() if p.dtype == torch.bfloat16)
                    if bfloat16_count > 0:
                        print(f"[WARNING] PEFT 모델에 여전히 {bfloat16_count}개의 BFloat16 파라미터가 남아있습니다. 재시도합니다.")
                        self.peft_model = self.peft_model.to(torch.float16)
                        force_float16_recursive(self.peft_model)

                    first_param_dtype = next(self.peft_model.parameters()).dtype
                    print(f"[OK] 최종 PEFT 모델 dtype: {first_param_dtype} (BFloat16 완전 차단)")
            except Exception as e:
                print(f"[INFO] PEFT 모델 dtype 확인 중 오류 (무시): {e}")

        # 학습 가능 파라미터 출력
        self.peft_model.print_trainable_parameters()

        self.is_loaded = True
        print("[OK] 모델 로드 완료!")
        print("=" * 60)

    def load_jsonl_data(self, jsonl_path: str) -> List[Dict[str, Any]]:
        """JSONL 파일을 로드합니다.

        Args:
            jsonl_path: JSONL 파일 경로

        Returns:
            데이터 리스트
        """
        jsonl_path = Path(jsonl_path)
        if not jsonl_path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {jsonl_path}")

        print(f"JSONL 파일 로드 중: {jsonl_path.name}")
        data = []

        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"경고: {jsonl_path.name}의 {lineno}번째 줄을 파싱할 수 없습니다: {e}")
                    continue

        print(f"총 {len(data):,}개 레코드 로드 완료")
        return data

    def format_prompt(self, example: Dict[str, str]) -> Dict[str, str]:
        """데이터를 프롬프트 형식으로 변환합니다.

        Args:
            example: {"instruction": "...", "input": "...", "output": "..."}

        Returns:
            {"text": "포맷된 프롬프트"}
        """
        instruction = example.get("instruction", "")
        input_text = example.get("input", "")
        output = example.get("output", "")

        # Exaone 프롬프트 형식
        if input_text:
            prompt = f"### Instruction:\n{instruction}\n\n### Input:\n{input_text}\n\n### Response:\n{output}"
        else:
            prompt = f"### Instruction:\n{instruction}\n\n### Response:\n{output}"

        return {"text": prompt}

    def train(
        self,
        training_data: List[Dict[str, str]],
        num_epochs: int = 3,
        batch_size: int = 4,
        learning_rate: float = 2e-4,
        max_seq_length: int = 512,
        save_steps: int = 500,
        logging_steps: int = 10,
        eval_data: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """모델을 훈련합니다.

        Args:
            training_data: 훈련 데이터 [{"instruction": "...", "input": "...", "output": "..."}]
            num_epochs: 학습 에포크 수
            batch_size: 배치 크기
            learning_rate: 학습률
            max_seq_length: 최대 시퀀스 길이
            save_steps: 저장 간격
            logging_steps: 로깅 간격
            eval_data: 평가 데이터 (선택)

        Returns:
            학습된 모델 저장 경로
        """
        if not self.is_loaded:
            raise RuntimeError("모델이 로드되지 않았습니다. load_model()을 먼저 호출하세요.")

        print("=" * 60)
        print("[ExaoneTrainer] 훈련 시작")
        print("=" * 60)
        print(f"훈련 샘플 수: {len(training_data):,}")
        if eval_data:
            print(f"평가 샘플 수: {len(eval_data):,}")
        print()

        # 데이터 포맷팅
        print("데이터 포맷팅 중...")
        train_dataset = Dataset.from_list(training_data)
        train_dataset = train_dataset.map(self.format_prompt)

        eval_dataset = None
        if eval_data:
            eval_dataset = Dataset.from_list(eval_data)
            eval_dataset = eval_dataset.map(self.format_prompt)

        # 학습 인자 설정
        training_args = TrainingArguments(
            output_dir=str(self.output_dir),
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size if eval_dataset else None,
            gradient_accumulation_steps=4,
            learning_rate=learning_rate,
            # BFloat16 완전 차단: fp16 사용 여부 설정
            fp16=self.use_fp16_training and torch.cuda.is_available(),  # FP16 Mixed Precision (BFloat16 에러 방지를 위해 기본값 False)
            bf16=False,  # BFloat16 명시적으로 비활성화
            dataloader_pin_memory=False,  # 메모리 고정 비활성화 (호환성 개선)
            logging_steps=logging_steps,
            save_steps=save_steps,
            save_total_limit=3,
            optim="paged_adamw_8bit" if self.bnb_config else "adamw_torch",
            warmup_steps=100,
            lr_scheduler_type="cosine",
            weight_decay=0.01,
            max_grad_norm=1.0,
            eval_strategy="steps" if eval_dataset else "no",
            eval_steps=save_steps if eval_dataset else None,
            load_best_model_at_end=True if eval_dataset else False,
            metric_for_best_model="eval_loss" if eval_dataset else None,
            greater_is_better=False if eval_dataset else None,
            report_to="tensorboard",  # TensorBoard 로깅 활성화
            logging_dir=str(self.output_dir / "logs"),
        )

        # 데이터 콜레이터
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False,  # Causal LM
        )

        # Trainer 생성
        if TRL_AVAILABLE and SFTTrainer is not None:
            print("SFTTrainer 사용")
            try:
                import inspect
                sig = inspect.signature(SFTTrainer.__init__)
                params = sig.parameters

                # SFTTrainer 파라미터에 따라 다르게 호출
                trainer_kwargs = {
                    "model": self.peft_model,
                    "args": training_args,
                    "train_dataset": train_dataset,
                }

                # eval_dataset 파라미터가 있으면 추가
                if "eval_dataset" in params and eval_dataset:
                    trainer_kwargs["eval_dataset"] = eval_dataset

                # processing_class 파라미터가 있으면 tokenizer를 processing_class로 전달
                if "processing_class" in params:
                    trainer_kwargs["processing_class"] = self.tokenizer
                # tokenizer 파라미터가 있으면 추가 (구버전 호환)
                elif "tokenizer" in params:
                    trainer_kwargs["tokenizer"] = self.tokenizer

                # max_seq_length 파라미터가 있으면 추가 (일부 버전에서는 제거됨)
                if "max_seq_length" in params:
                    trainer_kwargs["max_seq_length"] = max_seq_length
                # max_seq_length가 없으면 데이터셋에서 처리하거나 기본값 사용

                # data_collator 파라미터가 있으면 추가
                if "data_collator" in params:
                    trainer_kwargs["data_collator"] = data_collator

                trainer = SFTTrainer(**trainer_kwargs)
            except Exception as e:
                print(f"[WARNING] SFTTrainer 초기화 실패: {e}, 기본 Trainer 사용")
                trainer = Trainer(
                    model=self.peft_model,
                    args=training_args,
                    train_dataset=train_dataset,
                    eval_dataset=eval_dataset,
                    data_collator=data_collator,
                )
        else:
            print("기본 Trainer 사용 (SFTTrainer를 사용할 수 없습니다)")
            trainer = Trainer(
                model=self.peft_model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                data_collator=data_collator,
            )

        # 학습 전 최종 BFloat16 차단 확인 및 강제 변환
        if torch.cuda.is_available():
            print("\n[최종 확인] 모델 및 PEFT 모델 dtype 검증 및 변환 중...")
            bfloat16_count = 0
            # PEFT 모델의 모든 파라미터 재확인 및 변환
            for name, param in self.peft_model.named_parameters():
                if param.dtype == torch.bfloat16:
                    bfloat16_count += 1
                    if bfloat16_count <= 5:  # 처음 5개만 로그 출력
                        print(f"[WARNING] 학습 전 {name} 파라미터가 BFloat16입니다. Float16으로 변환합니다.")
                    param.data = param.data.to(torch.float16)
            # PEFT 모델의 모든 버퍼 재확인 및 변환
            for name, buffer in self.peft_model.named_buffers():
                if buffer.dtype == torch.bfloat16:
                    print(f"[WARNING] 학습 전 {name} 버퍼가 BFloat16입니다. Float16으로 변환합니다.")
                    buffer.data = buffer.data.to(torch.float16)

            if bfloat16_count > 0:
                print(f"[OK] 총 {bfloat16_count}개의 BFloat16 파라미터를 Float16으로 변환 완료")
            else:
                print("[OK] BFloat16 파라미터가 없습니다. 모든 파라미터가 Float16입니다.")

            # 최종 확인: 모든 파라미터가 Float16인지 검증
            all_float16 = True
            for param in self.peft_model.parameters():
                if param.dtype == torch.bfloat16:
                    all_float16 = False
                    break

            if not all_float16:
                print("[ERROR] 일부 파라미터가 여전히 BFloat16입니다. 재귀적 강제 변환을 시도합니다.")
                self.peft_model = self.peft_model.to(torch.float16)
                force_float16_recursive(self.peft_model)

            print("[OK] 최종 검증 완료\n")

        # 학습 실행
        print()
        print("=" * 60)
        print("[ExaoneTrainer] 학습 시작")
        print("=" * 60)
        trainer.train()

        # 모델 저장
        print()
        print("=" * 60)
        print("[ExaoneTrainer] 모델 저장 중...")
        print("=" * 60)
        trainer.save_model()
        self.tokenizer.save_pretrained(str(self.output_dir))

        print(f"[OK] 학습 완료! 모델 저장 위치: {self.output_dir}")
        print("=" * 60)

        return str(self.output_dir)

    def unload(self) -> None:
        """모델을 언로드하고 메모리를 해제합니다."""
        if not self.is_loaded:
            return

        del self.model
        del self.tokenizer
        del self.peft_model

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        self.model = None
        self.tokenizer = None
        self.peft_model = None
        self.is_loaded = False

        print("[OK] 모델 언로드 완료")
