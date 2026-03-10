# 두 프로젝트 비교 분석

## 프로젝트 개요

### 1. `frontend/` - LangChain 챗봇 프론트엔드
- **목적**: LangChain + FastAPI + pgvector 기반 AI 챗봇 UI
- **기능**: 
  - 백엔드 API (`/api/chat`, `/api/health`) 호출
  - 실시간 채팅 인터페이스
  - 서버 상태 모니터링
- **포트**: 기본 3000 (명시적 설정 없음)
- **의존성**: 최소한 (Next.js, React만)

### 2. `www.ohgun.site/` - OHGUN ESG 플랫폼 랜딩 페이지
- **목적**: ESG 플랫폼 랜딩 페이지 + OAuth 인증
- **기능**:
  - OAuth 로그인 (네이버, 카카오)
  - 사용자 인증 관리 (Zustand)
  - 사이드바, 모달 등 복잡한 UI
- **포트**: 명시적으로 3000 (`"dev": "next dev -p 3000"`)
- **의존성**: 많음 (Radix UI, Zustand, Lucide 등)

---

## 충돌 분석

### ✅ 코드 충돌 없음

| 항목 | 상태 | 이유 |
|------|------|------|
| **디렉토리** | ✅ 독립 | 완전히 별도의 폴더 (`frontend/` vs `www.ohgun.site/`) |
| **Import 경로** | ✅ 독립 | 각 프로젝트는 자체 `tsconfig.json`의 `@/*` 경로 사용 |
| **빌드 산출물** | ✅ 독립 | 각 프로젝트는 자체 `.next/` 폴더 사용 |
| **의존성** | ✅ 독립 | 각 프로젝트는 자체 `node_modules/` 사용 |
| **설정 파일** | ✅ 독립 | 각 프로젝트는 자체 `package.json`, `tsconfig.json` 등 |

### ⚠️ 유일한 주의사항: 포트 충돌

```
frontend/           → 기본 3000 포트
www.ohgun.site/     → 명시적 3000 포트
```

**해결 방법**:
- 한 번에 하나만 실행하거나
- 하나의 포트를 변경하여 실행

---

## 실행 방법

### 옵션 1: 각각 실행 (권장)

```bash
# 터미널 1: frontend 실행 (기본 3000)
cd frontend
pnpm dev

# 터미널 2: www.ohgun.site 실행 (다른 포트)
cd www.ohgun.site
pnpm dev -- -p 3001
```

### 옵션 2: package.json 스크립트 수정

```json
// www.ohgun.site/package.json
{
  "scripts": {
    "dev": "next dev -p 3001"  // 포트 변경
  }
}
```

---

## 결론

### ✅ 코드 충돌 없음
- 두 프로젝트는 **완전히 독립적**으로 작동
- 서로 다른 디렉토리, 설정, 의존성을 가짐
- 주석 처리나 코드 수정 **불필요**

### ⚠️ 포트 충돌만 주의
- 동시 실행 시 포트를 다르게 설정하면 됨
- 단일 실행 시에는 문제 없음

### 📋 권장사항
1. **현재 상태 유지** - 코드 수정 불필요
2. **실행 시 포트 지정** - 필요시 `-p` 옵션 사용
3. **각 프로젝트 독립 관리** - 각각 별도 터미널에서 실행

---

## 추가 정보

### Import 경로 예시

```typescript
// frontend/app/page.tsx
import { ... } from "@/..."  // frontend/* 경로

// www.ohgun.site/app/page.tsx  
import { ... } from "@/..."  // www.ohgun.site/* 경로
```

각 프로젝트의 `tsconfig.json`에서 `@/*`는 **상대 경로(`./*`)**로 설정되어 있어,
서로 완전히 독립적으로 작동합니다.
