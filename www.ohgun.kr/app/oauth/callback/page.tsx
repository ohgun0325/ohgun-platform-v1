'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { handleLoginSuccess } from '@/services/mainservice';

function OAuthCallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const processLogin = async () => {
      const accessToken = searchParams.get('accessToken');
      const refreshToken = searchParams.get('refreshToken');
      const provider = searchParams.get('provider');
      const success = searchParams.get('success');

      if (success === 'true' && accessToken) {
        // 로그인 성공 처리: Access Token은 Zustand에, Refresh Token은 HttpOnly 쿠키에 저장
        const loginSuccess = await handleLoginSuccess(accessToken, refreshToken);

        if (loginSuccess) {
          setStatus('success');
          setMessage(`${provider || '네이버'} 로그인에 성공했습니다!`);
        } else {
          setStatus('error');
          setMessage('로그인 토큰 저장에 실패했습니다.');
          return;
        }

        // 2초 후 메인 페이지로 리다이렉트
        setTimeout(() => {
          router.push('/');
        }, 2000);
      } else {
        setStatus('error');
        setMessage('로그인에 실패했습니다.');
      }
    };

    processLogin();
  }, [searchParams, router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-100 to-white flex items-center justify-center">
      <div className="text-center">
        {status === 'loading' && (
          <div className="space-y-4">
            <div className="w-16 h-16 border-4 border-[#003478] border-t-transparent rounded-full animate-spin mx-auto"></div>
            <p className="text-gray-600">로그인 처리 중...</p>
          </div>
        )}
        {status === 'success' && (
          <div className="space-y-4">
            <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mx-auto">
              <svg
                className="w-8 h-8 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <p className="text-lg font-semibold text-gray-800">{message}</p>
            <p className="text-sm text-gray-500">잠시 후 메인 페이지로 이동합니다...</p>
          </div>
        )}
        {status === 'error' && (
          <div className="space-y-4">
            <div className="w-16 h-16 bg-red-500 rounded-full flex items-center justify-center mx-auto">
              <svg
                className="w-8 h-8 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </div>
            <p className="text-lg font-semibold text-gray-800">{message}</p>
            <button
              onClick={() => router.push('/')}
              className="px-6 py-2 bg-[#003478] text-white rounded-lg hover:bg-[#002a5c] transition-colors"
            >
              메인으로 돌아가기
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function OAuthCallback() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-100 to-white flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 border-4 border-[#003478] border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-gray-600">로딩 중...</p>
        </div>
      </div>
    }>
      <OAuthCallbackContent />
    </Suspense>
  );
}

