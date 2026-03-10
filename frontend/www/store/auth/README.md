# 인증 스토어 구조 설명

## 현재 구조 vs 덕스 패턴

### 현재 구조 (모듈화된 구조)

```
auth/
├── types.ts      # 타입 정의만
├── reducer.ts    # 리듀서 로직만
├── store.ts      # 스토어 생성만
├── provider.tsx  # Provider 컴포넌트만
└── index.ts      # 모듈 export
```

### 진정한 덕스 패턴 (원래 개념)

```
auth.ts (또는 auth.js)
├── 타입 정의
├── 액션 타입
├── 액션 생성자
├── 리듀서
└── export
```

**모든 것을 하나의 파일에 모음**

---

## 왜 파일을 나누는가?

### 1. 관심사 분리 (Separation of Concerns)

각 파일이 **하나의 책임**만 가집니다:

- **types.ts**: 타입 정의만 담당
- **reducer.ts**: 비즈니스 로직만 담당
- **store.ts**: 스토어 생성만 담당
- **provider.tsx**: Provider 컴포넌트만 담당

### 2. 유지보수성 향상

```typescript
// ❌ 하나의 파일에 모든 것이 있을 때
// auth.ts (500줄)
// - 타입 수정하려면 500줄 파일에서 찾아야 함
// - 리듀서 수정하려면 500줄 파일에서 찾아야 함

// ✅ 파일이 분리되어 있을 때
// types.ts 수정 → types.ts만 열면 됨
// reducer.ts 수정 → reducer.ts만 열면 됨
```

### 3. 테스트 용이성

```typescript
// types.ts만 테스트
import { UserInfo } from './types';

// reducer.ts만 테스트
import { createAuthSlice } from './reducer';
```

### 4. 가독성

- 작은 파일 = 이해하기 쉬움
- 큰 파일 = 이해하기 어려움

### 5. 협업 효율성

- 여러 사람이 동시에 작업 가능
- Git 충돌 최소화

---

## 현재 구조의 장단점

### 장점 ✅

1. **명확한 책임 분리**
   - 각 파일의 역할이 명확함
   - 코드 찾기 쉬움

2. **확장성**
   - 새로운 기능 추가 시 적절한 파일에 추가
   - 파일이 커지면 다시 분리 가능

3. **재사용성**
   - `types.ts`를 다른 곳에서도 import 가능
   - `reducer.ts`를 다른 스토어에서도 사용 가능

4. **타입 안정성**
   - TypeScript에서 타입만 import 가능
   - 번들 크기 최적화

### 단점 ❌

1. **파일 수 증가**
   - 작은 기능에도 여러 파일 필요
   - 프로젝트 구조가 복잡해 보일 수 있음

2. **import 경로 증가**
   ```typescript
   // 하나의 파일이면
   import { useAuthStore } from './auth';
   
   // 분리된 구조면 (실제로는 index.ts로 해결)
   import { useAuthStore } from './auth'; // 동일
   ```

---

## 덕스 패턴 vs 현재 구조

### 덕스 패턴 (원래 개념)

```typescript
// auth.ts (모든 것을 하나의 파일에)
export const SET_TOKEN = 'auth/SET_TOKEN';
export const LOGIN = 'auth/LOGIN';

export const setToken = (token: string) => ({
  type: SET_TOKEN,
  payload: token,
});

export default function reducer(state, action) {
  // ...
}
```

**특징:**
- Redux에서 사용
- 관련된 모든 것을 하나의 파일에 모음
- 파일 이름으로 기능 구분 (예: `auth.js`, `user.js`)

### 현재 구조 (모듈화된 구조)

```typescript
// types.ts
export interface AuthState { ... }

// reducer.ts
export const createAuthSlice = ... 

// store.ts
export const useAuthStore = ...
```

**특징:**
- Zustand에서 사용
- 관심사별로 파일 분리
- 폴더 이름으로 기능 구분 (예: `auth/`, `user/`)

---

## 결론

### 현재 구조는 "덕스 패턴"이 아닙니다

정확히는:
- **모듈화된 구조 (Modular Structure)**
- **관심사 분리 (Separation of Concerns)**
- **덕스 패턴의 정신을 Zustand에 적용한 변형**

### 왜 이렇게 나누는가?

1. **유지보수성**: 코드 수정이 쉬움
2. **가독성**: 작은 파일 = 이해하기 쉬움
3. **테스트**: 각 부분을 독립적으로 테스트 가능
4. **협업**: 여러 사람이 동시에 작업 가능
5. **확장성**: 기능 추가가 쉬움

### Provider는 왜 필요한가?

Zustand는 Provider가 **필수는 아닙니다**. 하지만:

1. **구조 명확성**: React의 일반적인 패턴과 일치
2. **미래 확장성**: 나중에 Provider가 필요할 수 있음
3. **일관성**: 다른 상태 관리 라이브러리와 유사한 구조

---

## 참고: 진정한 덕스 패턴으로 변경하려면?

하나의 파일로 합칠 수 있습니다:

```typescript
// auth.ts (모든 것을 하나의 파일에)
export interface UserInfo { ... }
export interface AuthState { ... }
export interface AuthActions { ... }

export const createAuthSlice: StateCreator<AuthStore> = (set) => ({ ... });

export const useAuthStore = create<AuthStore>()((...a) => ({
  ...createAuthSlice(...a),
}));

export function AuthProvider({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
```

하지만 현재 구조가 더 **유지보수하기 쉽고 확장 가능**합니다.

