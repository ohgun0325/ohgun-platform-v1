'use client';

/**
 * 인증 스토어 Provider (Ducks Pattern)
 * 
 * 참고: Zustand는 Provider가 필요 없지만, 구조를 명확하게 하기 위해 제공합니다.
 * 실제로는 Provider 없이도 useAuthStore를 직접 사용할 수 있습니다.
 */

import { ReactNode } from 'react';

interface AuthProviderProps {
  children: ReactNode;
}

/**
 * 인증 스토어 Provider
 * 
 * 사용법:
 * ```tsx
 * <AuthProvider>
 *   <App />
 * </AuthProvider>
 * ```
 */
export function AuthProvider({ children }: AuthProviderProps) {
  // Zustand는 Provider가 필요 없지만, 구조를 명확하게 하기 위해 제공
  // 실제로는 children을 그대로 반환
  return <>{children}</>;
}

