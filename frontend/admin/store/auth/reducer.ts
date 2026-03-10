/**
 * 인증 리듀서 로직 (Ducks Pattern)
 */

import { StateCreator } from 'zustand';
import { AuthStore, UserInfo } from './types';

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
 * 인증 스토어 리듀서
 */
export const createAuthSlice: StateCreator<AuthStore> = (set) => ({
  // 초기 상태
  accessToken: null,
  userInfo: null,
  isLoggedIn: false,

  // Access Token 설정
  setAccessToken: (token) =>
    set({
      accessToken: token,
      isLoggedIn: !!token,
    }),

  // 사용자 정보 설정
  setUserInfo: (info) =>
    set({ userInfo: info }),

  // 로그인
  login: (accessToken, userInfo) => {
    // userInfo가 제공되지 않았다면 accessToken에서 추출 시도
    let parsedUserInfo = userInfo;
    if (!userInfo && accessToken) {
      parsedUserInfo = extractUserInfoFromToken(accessToken);
    }

    set({
      accessToken,
      userInfo: parsedUserInfo,
      isLoggedIn: true,
    });
  },

  // 로그아웃
  logout: () =>
    set({
      accessToken: null,
      userInfo: null,
      isLoggedIn: false,
    }),
});

