import { useAuthStore } from '@/store/auth';
import type { UserInfo } from '@/store/auth';

/**
 * JWT 토큰에서 사용자 정보 추출
 */
function extractUserInfoFromToken(accessToken: string): UserInfo | null {
  try {
    const payload = JSON.parse(atob(accessToken.split('.')[1]));
    return {
      email: payload.email,
      name: payload.name,
    };
  } catch (e) {
    console.error('Failed to parse token:', e);
    return null;
  }
}

/**
 * 로그인 성공 시 토큰 저장
 *
 * @param accessToken - Access Token (Zustand 스토어에 저장)
 * @param refreshToken - Refresh Token (HttpOnly 쿠키에 저장)
 * @returns Promise<boolean> - 성공 여부
 */
export async function handleLoginSuccess(
  accessToken: string,
  refreshToken: string | null
): Promise<boolean> {
  try {
    // 1. Refresh Token을 HttpOnly 쿠키에 저장 (XSS 공격 방지)
    if (refreshToken) {
      const cookieStored = await storeRefreshTokenInCookie(refreshToken);
      if (!cookieStored) {
        console.warn('Failed to store refresh token in cookie, but continuing...');
      }
    }

    // 2. Access Token은 메모리(Zustand)에만 저장
    // Refresh Token은 쿠키에 저장되었으므로 Zustand에는 저장하지 않음
    const userInfo = extractUserInfoFromToken(accessToken);
    useAuthStore.getState().login(accessToken, userInfo);

    console.log('Login success: Access token stored in Zustand, Refresh token stored in HttpOnly cookie');
    return true;
  } catch (error) {
    console.error('Error handling login success:', error);
    return false;
  }
}

/**
 * Refresh Token을 HttpOnly 쿠키에 저장하는 함수
 *
 * @param refreshToken - 저장할 Refresh Token
 * @returns Promise<boolean> - 성공 여부
 */
export async function storeRefreshTokenInCookie(refreshToken: string): Promise<boolean> {
  try {
    const response = await fetch('/api/auth/set-cookie', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refreshToken }),
      credentials: 'include', // 쿠키 포함
    });

    if (!response.ok) {
      console.error('Failed to store refresh token in cookie:', response.statusText);
      return false;
    }

    console.log('Refresh token stored in HttpOnly cookie');
    return true;
  } catch (error) {
    console.error('Error storing refresh token in cookie:', error);
    return false;
  }
}

/**
 * Refresh Token 쿠키 삭제 (로그아웃)
 *
 * @returns Promise<boolean> - 성공 여부
 */
export async function removeRefreshTokenCookie(): Promise<boolean> {
  try {
    const response = await fetch('/api/auth/set-cookie', {
      method: 'DELETE',
      credentials: 'include', // 쿠키 포함
    });

    if (!response.ok) {
      console.error('Failed to remove refresh token cookie:', response.statusText);
      return false;
    }

    console.log('Refresh token cookie removed');
    return true;
  } catch (error) {
    console.error('Error removing refresh token cookie:', error);
    return false;
  }
}

export function createMainHandlers(setIsLoginModalOpen: (value: boolean) => void) {
  const handleLoginClick = () => {
    setIsLoginModalOpen(true);
  };

  const handleLoginRequired = () => {
    setIsLoginModalOpen(true);
  };

  const handleExplore = () => {
    // Scroll to features section
    const featuresSection = document.getElementById('features');
    if (featuresSection) {
      featuresSection.scrollIntoView({ behavior: 'smooth' });
    }
  };

  /**
   * 소셜 로그인 버튼 클릭 시 동작:
   * 1. oauth-service에 네이버 로그인 URL을 요청
   * 2. 응답으로 받은 URL로 브라우저를 리다이렉트
   *
   * NOTE: 현재는 네이버만 사용하므로 단일 엔드포인트로 호출합니다.
   *       추후 Kakao/Google 추가 시 provider 파라미터를 받을 수 있도록 확장할 수 있습니다.
   */
  const handleLogin = async () => {
    try {
      console.log('Login action triggered');

      const baseUrl =
        process.env.NEXT_PUBLIC_OAUTH_BASE_URL ?? 'http://localhost:8080';

      console.log('Requesting login URL from:', `${baseUrl}/oauth/naver/login-url`);

      const response = await fetch(`${baseUrl}/oauth/naver/login-url`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      console.log('Response status:', response.status);
      console.log('Response ok:', response.ok);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Failed to get login url from oauth-service', {
          status: response.status,
          statusText: response.statusText,
          error: errorText,
        });
        alert(`로그인 URL 요청 실패: ${response.status} ${response.statusText}`);
        return;
      }

      const data = (await response.json()) as { url: string; state?: string };
      console.log('Received login URL:', data.url);

      if (!data.url) {
        console.error('No URL in response:', data);
        alert('로그인 URL을 받지 못했습니다.');
        return;
      }

      // 모달 닫고 네이버 로그인 페이지로 이동
      setIsLoginModalOpen(false);
      console.log('Redirecting to:', data.url);
      window.location.href = data.url;
    } catch (error) {
      console.error('Error while requesting Naver login URL', error);
      alert(`로그인 요청 중 오류가 발생했습니다: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  return {
    handleLoginClick,
    handleLoginRequired,
    handleExplore,
    handleLogin,
  };
}

