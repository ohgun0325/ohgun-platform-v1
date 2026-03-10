# 서비스 함수 (Services)

## mainservice.ts

인증 관련 유틸리티 함수를 제공합니다.

## Refresh Token 관리

### 1. Refresh Token을 HttpOnly 쿠키에 저장

```typescript
import { storeRefreshTokenInCookie } from '@/services/mainservice';

// 로그인 성공 시
const refreshToken = 'your-refresh-token';
const success = await storeRefreshTokenInCookie(refreshToken);

if (success) {
  console.log('Refresh token stored in HttpOnly cookie');
} else {
  console.error('Failed to store refresh token');
}
```

**보안 특징:**
- HttpOnly: JavaScript로 접근 불가 (XSS 공격 방지)
- Secure: HTTPS에서만 전송 (프로덕션 환경)
- SameSite=Strict: CSRF 공격 방지
- 만료 시간: 7일

### 2. Refresh Token 쿠키 삭제 (로그아웃)

```typescript
import { removeRefreshTokenCookie } from '@/services/mainservice';

// 로그아웃 시
const success = await removeRefreshTokenCookie();

if (success) {
  console.log('Refresh token removed');
}
```

## 전체 로그인/로그아웃 플로우

### 로그인 플로우

```typescript
import { useAuthStore } from '@/store/authStore';
import { storeRefreshTokenInCookie } from '@/services/mainservice';

// OAuth 콜백에서 토큰 받기
const accessToken = 'jwt-access-token';
const refreshToken = 'jwt-refresh-token';

// 1. Refresh Token을 HttpOnly 쿠키에 저장
await storeRefreshTokenInCookie(refreshToken);

// 2. Access Token은 메모리(Zustand)에만 저장
const { login } = useAuthStore();
login(accessToken, null, { // refreshToken은 null (쿠키에 저장됨)
  email: 'user@example.com',
  name: '홍길동'
});
```

### 로그아웃 플로우

```typescript
import { useAuthStore } from '@/store/authStore';
import { removeRefreshTokenCookie } from '@/services/mainservice';

const { logout } = useAuthStore();

const handleLogout = async () => {
  // 1. HttpOnly 쿠키에서 Refresh Token 제거
  await removeRefreshTokenCookie();
  
  // 2. Zustand 스토어에서 Access Token 제거 (메모리)
  logout();
};
```

## API 라우트

### POST /api/auth/set-cookie

Refresh Token을 HttpOnly 쿠키에 저장합니다.

**요청:**
```json
{
  "refreshToken": "jwt-refresh-token"
}
```

**응답:**
```json
{
  "success": true,
  "message": "Refresh token stored in cookie"
}
```

**쿠키 설정:**
- 이름: `refreshToken`
- HttpOnly: `true`
- Secure: `true` (프로덕션)
- SameSite: `strict`
- MaxAge: 7일
- Path: `/`

### DELETE /api/auth/set-cookie

Refresh Token 쿠키를 삭제합니다.

**응답:**
```json
{
  "success": true,
  "message": "Refresh token removed"
}
```

## 보안 고려사항

### ✅ 구현된 보안 기능

1. **Access Token**: 메모리(Zustand)에만 저장
   - XSS 공격으로부터 보호
   - 페이지 새로고침 시 소실 (의도된 동작)

2. **Refresh Token**: HttpOnly 쿠키에 저장
   - JavaScript로 접근 불가
   - XSS 공격으로부터 보호
   - CSRF 공격 방지 (SameSite=Strict)

3. **HTTPS 강제**: 프로덕션 환경에서 Secure 플래그 사용

### ⚠️ 주의사항

1. **페이지 새로고침**
   - Access Token이 소실됨
   - Refresh Token으로 재발급 필요 (향후 구현)

2. **CORS 설정**
   - `credentials: 'include'` 필수
   - 서버에서 CORS 허용 필요

3. **프로덕션 배포**
   - HTTPS 필수
   - 환경 변수 `NODE_ENV=production` 설정

## 사용 예시

### OAuth 콜백 페이지

```typescript
// app/oauth/callback/page.tsx
import { useAuthStore } from '@/store/authStore';
import { storeRefreshTokenInCookie } from '@/services/mainservice';

const { login } = useAuthStore();

// 로그인 처리
const accessToken = searchParams.get('accessToken');
const refreshToken = searchParams.get('refreshToken');

if (refreshToken) {
  await storeRefreshTokenInCookie(refreshToken);
}

login(accessToken, null, userInfo);
```

### 메인 페이지 로그아웃

```typescript
// app/page.tsx
import { useAuthStore } from '@/store/authStore';
import { removeRefreshTokenCookie } from '@/services/mainservice';

const { logout } = useAuthStore();

<button onClick={async () => {
  await removeRefreshTokenCookie();
  logout();
}}>
  로그아웃
</button>
```

## 참고 자료

- [OWASP - HttpOnly Cookie](https://owasp.org/www-community/HttpOnly)
- [MDN - Set-Cookie](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie)
- [Next.js - API Routes](https://nextjs.org/docs/app/building-your-application/routing/route-handlers)

