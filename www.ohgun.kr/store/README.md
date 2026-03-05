# 인증 스토어 (Auth Store)

## 개요

이 프로젝트는 **Zustand**를 사용하여 인증 상태를 메모리에서 관리합니다.

## 보안 원칙

### ✅ Access Token 저장 방식
- **메모리(Zustand 스토어)에만 저장**
- localStorage 사용 금지 (XSS 공격 방지)
- 만료 시간: 5~15분 (짧게 설정 권장)
- 페이지 새로고침 시 소실됨 → Refresh Token으로 재발급 필요

### ✅ Refresh Token 저장 방식
- **구현됨**: httpOnly 쿠키에 저장 (XSS 공격 방지)
- **API 라우트**: `/api/auth/set-cookie`
- 만료 시간: 7일
- Secure, SameSite=Strict 설정

### 🔒 보안 이점
1. **XSS 공격 방지**: JavaScript로 토큰 접근 불가 (메모리에만 존재)
2. **CSRF 공격 방지**: httpOnly 쿠키 사용 시
3. **토큰 탈취 위험 감소**: localStorage보다 안전

## 사용 방법

### 1. 스토어 가져오기

```typescript
import { useAuthStore } from '@/store/authStore';
```

### 2. 로그인

```typescript
const { login } = useAuthStore();

// 로그인 성공 시
login(accessToken, refreshToken, {
  email: 'user@example.com',
  name: '홍길동'
});
```

### 3. 로그아웃

```typescript
import { useAuthStore } from '@/store/authStore';
import { removeRefreshTokenCookie } from '@/services/mainservice';

const { logout } = useAuthStore();

// 로그아웃
const handleLogout = async () => {
  // 1. HttpOnly 쿠키에서 Refresh Token 제거
  await removeRefreshTokenCookie();
  
  // 2. Zustand 스토어에서 Access Token 제거
  logout();
};
```

### 4. 인증 상태 확인

```typescript
const { isLoggedIn, userInfo, accessToken } = useAuthStore();

if (isLoggedIn) {
  console.log('로그인됨:', userInfo?.name);
  // API 요청 시 accessToken 사용
  fetch('/api/protected', {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
}
```

### 5. 개별 상태 업데이트

```typescript
const { setAccessToken, setUserInfo } = useAuthStore();

// Access Token만 업데이트
setAccessToken(newAccessToken);

// 사용자 정보만 업데이트
setUserInfo({ email: 'new@example.com', name: '김철수' });
```

## API 요청 시 토큰 사용

```typescript
import { useAuthStore } from '@/store/authStore';

async function fetchProtectedData() {
  const { accessToken } = useAuthStore.getState();
  
  if (!accessToken) {
    throw new Error('로그인이 필요합니다');
  }
  
  const response = await fetch('/api/protected', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
  });
  
  if (response.status === 401) {
    // Access Token 만료 → Refresh Token으로 재발급
    await refreshAccessToken();
    // 재시도
    return fetchProtectedData();
  }
  
  return response.json();
}
```

## Refresh Token 재발급 로직 (구현 예정)

```typescript
async function refreshAccessToken() {
  const { refreshToken, setAccessToken, logout } = useAuthStore.getState();
  
  if (!refreshToken) {
    logout();
    throw new Error('Refresh Token이 없습니다');
  }
  
  try {
    const response = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refreshToken }),
    });
    
    if (!response.ok) {
      throw new Error('토큰 갱신 실패');
    }
    
    const { accessToken: newAccessToken } = await response.json();
    setAccessToken(newAccessToken);
    
    return newAccessToken;
  } catch (error) {
    console.error('토큰 갱신 실패:', error);
    logout();
    throw error;
  }
}
```

## 페이지 새로고침 처리

Access Token이 메모리에만 저장되므로 페이지 새로고침 시 소실됩니다.

### 해결 방법

1. **App 초기화 시 Refresh Token으로 재발급**

```typescript
// app/layout.tsx 또는 _app.tsx
useEffect(() => {
  const initAuth = async () => {
    const { refreshToken, isLoggedIn } = useAuthStore.getState();
    
    // Refresh Token이 있고 로그인 상태가 아니면 재발급 시도
    if (refreshToken && !isLoggedIn) {
      try {
        await refreshAccessToken();
      } catch (error) {
        console.error('자동 로그인 실패:', error);
      }
    }
  };
  
  initAuth();
}, []);
```

2. **httpOnly 쿠키 사용 (권장)**
   - 서버에서 Refresh Token을 httpOnly 쿠키로 설정
   - 페이지 로드 시 서버에 요청하여 Access Token 재발급

## 주의사항

⚠️ **절대 하지 말아야 할 것**
- Access Token을 localStorage에 저장
- Access Token을 sessionStorage에 저장
- Access Token을 쿠키에 저장 (httpOnly가 아닌 경우)

✅ **해야 할 것**
- Access Token은 메모리(Zustand)에만 보관
- Refresh Token은 httpOnly 쿠키 사용 권장
- Access Token 만료 시간을 짧게 설정 (5~15분)
- HTTPS 사용 필수

## 참고 자료

- [OWASP - Token Storage](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html)
- [Zustand 공식 문서](https://zustand-demo.pmnd.rs/)

