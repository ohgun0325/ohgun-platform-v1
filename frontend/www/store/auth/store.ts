/**
 * 인증 스토어 생성 (Ducks Pattern)
 * 
 * 보안 원칙:
 * - Access Token: 메모리(Zustand)에만 저장, localStorage 사용 금지
 * - Refresh Token: httpOnly 쿠키에 저장 (클라이언트 스토어에 저장하지 않음)
 * - 페이지 새로고침 시 Access Token 소실 → Refresh Token으로 재발급 로직 필요
 */

import { create } from 'zustand';
import { createAuthSlice } from './reducer';
import { AuthStore } from './types';

/**
 * 인증 상태 관리 스토어
 */
export const useAuthStore = create<AuthStore>()((...a) => ({
  ...createAuthSlice(...a),
}));

