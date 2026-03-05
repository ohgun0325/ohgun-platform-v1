"""Admin 도메인 라우터 - 훈련 관련 기능"""

from fastapi import APIRouter

router = APIRouter(tags=["admin", "training"])


# TODO: 훈련 관련 엔드포인트 구현
# POST /api/train/start - 특정 데이터셋/모델 설정으로 학습 시작
# GET /api/train/status/{job_id} - 현재 학습 진행 상황 조회
