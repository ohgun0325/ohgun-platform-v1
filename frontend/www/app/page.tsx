'use client';

import { useState } from 'react';
import { Sparkles } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import LoginModal from '@/components/LoginModal';
import { useAuthStore } from '@/store/auth';
import { removeRefreshTokenCookie } from '@/services/mainservice';

export default function Home() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeSidebarSection, setActiveSidebarSection] = useState<'notice' | 'news' | null>(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const { isLoggedIn, userInfo, logout } = useAuthStore();

  return (
    <div className="min-h-screen bg-[#003478] flex flex-col">
      {/* 헤더 */}
      <header className="w-full flex items-center justify-between p-4 bg-[#003478] border-b border-white/10">
        <div className="flex items-center gap-4">
          {/* 햄버거 메뉴 버튼 */}
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-white/10 transition-colors"
            aria-label="메뉴 열기"
          >
            <svg
              className="w-6 h-6 text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
        </div>

        {/* 오른쪽 로그인/로그아웃 버튼 */}
        {isLoggedIn ? (
          <div className="flex items-center gap-3">
            {userInfo?.name && (
              <span className="text-sm text-white font-medium">
                {userInfo.name}님
              </span>
            )}
            <button
              onClick={async () => {
                await removeRefreshTokenCookie();
                logout();
              }}
              className="px-6 py-2 rounded-lg bg-red-500 text-white hover:bg-red-600 transition-colors font-medium text-sm"
            >
              로그아웃
            </button>
          </div>
        ) : (
          <button
            onClick={() => setIsLoginModalOpen(true)}
            className="px-6 py-2 rounded-lg bg-white text-[#003478] hover:bg-gray-100 transition-colors font-medium text-sm"
          >
            로그인
          </button>
        )}
      </header>

      {/* 메인 컨텐츠 - 로고 영역 */}
      <main className="flex-1 flex items-center justify-center px-4 py-8">
        <div className="text-center">
          {/* AI First 텍스트 */}
          <div className="flex items-center justify-center gap-3 mb-8">
            <h2 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
              AI First
            </h2>
            <div className="flex items-center gap-1">
              <Sparkles className="w-8 h-8 md:w-10 md:h-10 text-white" />
              <Sparkles className="w-6 h-6 md:w-8 md:h-8 text-white opacity-70" />
            </div>
          </div>

          {/* KOICA 텍스트 */}
          <div className="flex items-center justify-center gap-1 md:gap-2 lg:gap-3">
            <span className="text-8xl md:text-9xl lg:text-[10rem] xl:text-[12rem] font-bold text-white tracking-tight leading-none">
              KOICA
            </span>
          </div>
        </div>
      </main>

      {/* 사이드바 */}
      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => {
          setIsSidebarOpen(false);
          setActiveSidebarSection(null);
        }}
        activeSection={activeSidebarSection}
        onSectionChange={setActiveSidebarSection}
      />

      {/* 로그인 모달 */}
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onKakaoLogin={async () => {
          console.log('카카오 로그인 클릭');
          alert('카카오 로그인은 준비 중입니다.');
        }}
        onNaverLogin={async () => {
          try {
            const baseUrl = process.env.NEXT_PUBLIC_OAUTH_BASE_URL ?? 'http://localhost:8080';
            const loginUrl = `${baseUrl}/oauth/naver/login-url`;

            const response = await fetch(loginUrl, {
              method: 'GET',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
            });

            if (!response.ok) {
              const errorText = await response.text();
              alert(`로그인 URL 요청 실패: ${response.status} ${response.statusText}`);
              return;
            }

            const data = await response.json() as { url: string; state?: string };
            if (!data.url) {
              alert('로그인 URL을 받지 못했습니다.');
              return;
            }

            setIsLoginModalOpen(false);
            window.location.href = data.url;
          } catch (error) {
            alert(`로그인 요청 중 오류가 발생했습니다: ${error instanceof Error ? error.message : String(error)}`);
          }
        }}
      />
    </div>
  );
}
