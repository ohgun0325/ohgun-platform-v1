/**
 * 인증 관련 타입 정의 (Ducks Pattern)
 */

export interface UserInfo {
  email?: string;
  name?: string;
}

export interface AuthState {
  // Access Token은 메모리에만 보관 (짧은 만료 시간: 5~15분)
  accessToken: string | null;
  
  // 사용자 정보
  userInfo: UserInfo | null;
  
  // 로그인 여부
  isLoggedIn: boolean;
}

export interface AuthActions {
  // Access Token 설정
  setAccessToken: (token: string | null) => void;
  
  // 사용자 정보 설정
  setUserInfo: (info: UserInfo | null) => void;
  
  // 로그인 (Access Token과 사용자 정보 저장)
  login: (accessToken: string, userInfo: UserInfo | null) => void;
  
  // 로그아웃
  logout: () => void;
}

export type AuthStore = AuthState & AuthActions;

