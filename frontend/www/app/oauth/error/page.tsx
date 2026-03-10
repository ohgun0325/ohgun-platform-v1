'use client';

import { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

function OAuthErrorContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [error, setError] = useState('');

  useEffect(() => {
    const errorMessage = searchParams.get('error');
    const provider = searchParams.get('provider');
    
    if (errorMessage) {
      setError(errorMessage);
    } else {
      setError('알 수 없는 오류가 발생했습니다.');
    }
  }, [searchParams]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-100 to-white flex items-center justify-center">
      <div className="text-center space-y-4 max-w-md">
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
        <h1 className="text-2xl font-bold text-gray-800">로그인 오류</h1>
        <p className="text-gray-600">{error}</p>
        <button
          onClick={() => router.push('/')}
          className="px-6 py-2 bg-[#003478] text-white rounded-lg hover:bg-[#002a5c] transition-colors"
        >
          메인으로 돌아가기
        </button>
      </div>
    </div>
  );
}

export default function OAuthError() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-100 to-white flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 border-4 border-[#003478] border-t-transparent rounded-full animate-spin mx-auto"></div>
          <p className="text-gray-600">로딩 중...</p>
        </div>
      </div>
    }>
      <OAuthErrorContent />
    </Suspense>
  );
}

