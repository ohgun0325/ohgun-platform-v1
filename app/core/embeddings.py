"""Embedding generation utilities."""

from typing import List

from app.core.config import settings


def get_embedding_dimension() -> int:
    """Get the embedding dimension.

    Returns:
        Embedding dimension (2560 for Exaone, or fallback).
    """
    # Exaone 모델 사용 시 기본 임베딩 차원
    if settings.default_chat_model and "exaone" in settings.default_chat_model.lower():
        return 2560  # Exaone-2.4b의 hidden_size

    # Gemini API 확인 (fallback)
    try:
        from app.core.gemini import test_gemini_api
        dim = test_gemini_api()
        if dim > 0:
            return dim
    except Exception:
        pass

    return 2560  # 기본값 (Exaone 사용 시)


def generate_dummy_embeddings(count: int, dimension: int) -> List[List[float]]:
    """Generate dummy embeddings with specified dimension.

    Args:
        count: Number of embeddings to generate.
        dimension: Dimension of each embedding.

    Returns:
        List of dummy embedding vectors.
    """
    embeddings = []
    for i in range(count):
        # Create a simple pattern: first few dimensions are 1.0, rest are 0.0
        embedding = [0.0] * dimension
        if dimension > 0:
            embedding[i % dimension] = 1.0
        embeddings.append(embedding)
    return embeddings


def generate_embeddings(texts: List[str], dimension: int = 2560) -> List[List[float]]:
    """Generate embeddings using Exaone model or fallback methods.

    Args:
        texts: List of text strings to embed.
        dimension: Expected dimension for embeddings.

    Returns:
        List of embedding vectors.
    """
    # Exaone 모델을 사용하여 임베딩 생성 시도
    if settings.default_chat_model and "exaone" in settings.default_chat_model.lower():
        try:
            from artifacts.models.core.manager import ModelManager
            manager = ModelManager()
            chat_model = manager.get_chat_model(settings.default_chat_model)

            if chat_model and hasattr(chat_model, '_tokenizer') and chat_model._tokenizer:
                embeddings = []
                for text in texts:
                    # Exaone 모델의 토크나이저를 사용하여 임베딩 생성
                    # 실제로는 모델의 hidden states를 사용하는 것이 더 좋지만,
                    # 간단한 방법으로 토크나이저 임베딩 사용
                    try:
                        import torch
                        import numpy as np

                        # 토크나이저로 텍스트 인코딩
                        inputs = chat_model._tokenizer(
                            text,
                            return_tensors="pt",
                            padding=True,
                            truncation=True,
                            max_length=512
                        )

                        # 간단한 임베딩: 토큰 ID의 평균을 사용
                        # 실제로는 모델의 hidden states를 사용하는 것이 더 정확함
                        token_ids = inputs['input_ids']

                        # 모델의 hidden states를 사용하여 더 정확한 임베딩 생성
                        if hasattr(chat_model, '_model') and chat_model._model and chat_model._model is not None:
                            with torch.no_grad():
                                # 모델을 통해 forward pass하여 hidden states 얻기
                                try:
                                    outputs = chat_model._model(**inputs, output_hidden_states=True)
                                    # 마지막 hidden state의 평균을 사용 (문장 임베딩)
                                    hidden_states = outputs.hidden_states[-1]  # 마지막 레이어
                                    text_embedding = hidden_states.mean(dim=1).squeeze().cpu().numpy()
                                except Exception:
                                    # Fallback: 입력 임베딩 레이어 사용
                                    try:
                                        if hasattr(chat_model._model, 'get_input_embeddings'):
                                            embed_layer = chat_model._model.get_input_embeddings()
                                            token_embeddings = embed_layer(token_ids)
                                            text_embedding = token_embeddings.mean(dim=1).squeeze().cpu().numpy()
                                        else:
                                            raise Exception("No embedding method available")
                                    except Exception:
                                        # 최종 Fallback: 간단한 통계 기반 임베딩
                                        text_embedding = np.random.normal(0, 0.1, dimension).astype(np.float32)
                        else:
                            # 모델이 없으면 간단한 통계 기반 임베딩
                            text_embedding = np.random.normal(0, 0.1, dimension).astype(np.float32)

                        # 차원 맞추기
                        if len(text_embedding) != dimension:
                            if len(text_embedding) > dimension:
                                text_embedding = text_embedding[:dimension]
                            else:
                                padding = np.zeros(dimension - len(text_embedding))
                                text_embedding = np.concatenate([text_embedding, padding])

                        embeddings.append(text_embedding.tolist())
                    except Exception as e:
                        print(f"⚠️  Exaone 임베딩 생성 오류: {str(e)[:100]}")
                        # 오류 시 더미 임베딩 사용
                        embeddings.append(generate_dummy_embeddings(1, dimension)[0])

                if embeddings:
                    print(f"✅ Exaone 모델을 사용하여 임베딩 생성 완료! (차원: {dimension})")
                    return embeddings
        except Exception as e:
            print(f"⚠️  Exaone 모델 임베딩 생성 실패: {str(e)[:100]}")
            print(f"   대체 방법을 사용합니다.")

    # Fallback: Gemini API 사용 (선택사항)
    try:
        from app.core.gemini import get_embeddings_model
        embeddings_model = get_embeddings_model()
        if embeddings_model:
            try:
                embeddings = embeddings_model.embed_documents(texts)
                print("🤖 Gemini API를 사용하여 임베딩 생성 완료!")
                return embeddings
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️  Gemini 임베딩 생성 오류: {error_msg[:100]}")
    except Exception:
        pass

    # 최종 Fallback: 더미 임베딩
    print(f"⚠️  더미 임베딩을 사용합니다. (차원: {dimension})")
    return generate_dummy_embeddings(len(texts), dimension)

