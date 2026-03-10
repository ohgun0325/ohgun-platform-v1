/**
 * 인증 스토어 모듈 (Ducks Pattern)
 * 
 * 구조:
 * - types.ts: 타입 정의
 * - reducer.ts: 리듀서 로직
 * - store.ts: 스토어 생성
 * - provider.tsx: Provider 컴포넌트
 * - index.ts: 모듈 export
 */

export { useAuthStore } from './store';
export { AuthProvider } from './provider';
export type { AuthState, AuthActions, AuthStore, UserInfo } from './types';

