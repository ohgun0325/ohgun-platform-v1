'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Search, BookOpen } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import LoginModal from '@/components/LoginModal';
import { useAuthStore } from '@/store/auth';
import { removeRefreshTokenCookie } from '@/services/mainservice';

interface TermResult {
  korean_name: string;
  english_name: string;
  abbreviation?: string;
  description: string;
  instruction: string;
  input: string;
  output: string;
}

interface SearchResponse {
  results: TermResult[];
  total: number;
  query: string;
}

export default function TermsPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchType, setSearchType] = useState<'all' | 'title' | 'content'>('all');
  const [isLoading, setIsLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeSidebarSection, setActiveSidebarSection] = useState<'notice' | 'news' | null>(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const { isLoggedIn, userInfo, logout } = useAuthStore();

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/term/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: searchQuery.trim(),
          limit: 20,
          search_type: searchType,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: '검색 실패' }));
        throw new Error(errorData.detail || '검색 중 오류가 발생했습니다');
      }

      const data: SearchResponse = await response.json();
      setSearchResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '검색 중 오류가 발생했습니다');
      setSearchResults(null);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-100 to-white">
      {/* 헤더 */}
      <header className="w-full flex items-center justify-between p-4 bg-white/80 backdrop-blur-sm border-b border-[#003478]/20">
        <div className="flex items-center gap-4">
          {/* 햄버거 메뉴 버튼 */}
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
            aria-label="메뉴 열기"
          >
            <svg
              className="w-6 h-6 text-gray-700"
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
          <div className="flex items-center gap-3">
            <BookOpen className="w-6 h-6 text-[#003478]" />
            <div className="flex flex-col">
              <h1 className="text-xl font-bold text-[#003478]">ODA 용어사전 AI</h1>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold text-[#003478]">KOICA</span>
                <span className="text-xs text-gray-600 font-serif">Korea International Cooperation Agency</span>
              </div>
            </div>
          </div>
        </div>

        {/* 오른쪽 로그인/로그아웃 버튼 */}
        {isLoggedIn ? (
          <div className="flex items-center gap-3">
            {userInfo?.name && (
              <span className="text-sm text-gray-700 font-medium">
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
            className="px-6 py-2 rounded-lg bg-[#003478] text-white hover:bg-[#002a5c] transition-colors font-medium text-sm"
          >
            로그인
          </button>
        )}
      </header>

      {/* 메인 컨텐츠 */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* 검색 영역 */}
        <div className="mb-8">
          <form onSubmit={handleSearch} className="space-y-4">
            {/* 검색 타입 선택 */}
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium text-gray-700">검색 범위:</span>
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="searchType"
                    value="all"
                    checked={searchType === 'all'}
                    onChange={(e) => setSearchType(e.target.value as 'all' | 'title' | 'content')}
                    className="w-4 h-4 text-[#003478] focus:ring-[#003478]"
                  />
                  <span className="text-sm text-gray-700">전체</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="searchType"
                    value="title"
                    checked={searchType === 'title'}
                    onChange={(e) => setSearchType(e.target.value as 'all' | 'title' | 'content')}
                    className="w-4 h-4 text-[#003478] focus:ring-[#003478]"
                  />
                  <span className="text-sm text-gray-700">제목 (한글명, 영문명, 약어)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="searchType"
                    value="content"
                    checked={searchType === 'content'}
                    onChange={(e) => setSearchType(e.target.value as 'all' | 'title' | 'content')}
                    className="w-4 h-4 text-[#003478] focus:ring-[#003478]"
                  />
                  <span className="text-sm text-gray-700">내용 (설명)</span>
                </label>
              </div>
            </div>

            {/* 검색 입력 */}
            <div className="flex items-center gap-2">
              <div className="flex-1 relative">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={
                    searchType === 'title'
                      ? '제목으로 검색하세요 (한글명, 영문명, 약어)'
                      : searchType === 'content'
                      ? '내용으로 검색하세요 (설명)'
                      : '용어를 검색하세요 (한글명, 영문명, 약어, 설명)'
                  }
                  className="w-full pl-12 pr-4 py-4 bg-white/80 backdrop-blur-sm border border-[#003478] rounded-lg focus:outline-none focus:ring-2 focus:ring-[#003478] focus:border-[#003478] text-gray-800 text-lg"
                  disabled={isLoading}
                />
              </div>
              <button
                type="submit"
                disabled={!searchQuery.trim() || isLoading}
                className="px-8 py-4 bg-[#003478] text-white rounded-lg hover:bg-[#002a5c] disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
              >
                {isLoading ? '검색 중...' : '검색'}
              </button>
            </div>
          </form>
        </div>

        {/* 에러 메시지 */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {/* 검색 결과 */}
        {searchResults && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-800">
                검색 결과: &quot;{searchResults.query}&quot;
              </h2>
              <span className="text-sm text-gray-600">
                총 {searchResults.total}개
              </span>
            </div>

            {searchResults.results.length === 0 ? (
              <div className="text-center py-12 bg-white/80 backdrop-blur-sm rounded-lg border border-gray-200">
                <p className="text-gray-600">검색 결과가 없습니다.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {searchResults.results.map((term, index) => (
                  <div
                    key={index}
                    className="bg-white/90 backdrop-blur-sm rounded-lg border border-gray-200 p-6 shadow-sm hover:shadow-md transition-shadow"
                  >
                    {/* 용어 헤더 */}
                    <div className="mb-4 pb-4 border-b border-gray-200">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <h3 className="text-xl font-bold text-[#003478] mb-2">
                            {term.korean_name}
                          </h3>
                          <p className="text-lg text-gray-700 font-medium">
                            {term.english_name}
                          </p>
                          {term.abbreviation && (
                            <p className="text-sm text-gray-500 mt-1">
                              약어: {term.abbreviation}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* 설명 */}
                    <div className="prose max-w-none">
                      <h4 className="text-sm font-semibold text-gray-700 mb-2">설명</h4>
                      <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">
                        {term.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 초기 안내 */}
        {!searchResults && !error && (
          <div className="text-center py-16">
            <BookOpen className="w-16 h-16 text-[#003478] mx-auto mb-4 opacity-50" />
            <h2 className="text-2xl font-semibold text-gray-700 mb-2">
              ODA 용어사전
            </h2>
            <p className="text-gray-600 mb-6">
              한국국제협력단 ODA 용어사전에서 용어를 검색할 수 있습니다.
            </p>
            <div className="inline-flex flex-col gap-2 text-sm text-gray-500">
              <p>• <strong>전체 검색:</strong> 제목과 내용 모두에서 검색</p>
              <p>• <strong>제목 검색:</strong> 한글명, 영문명, 약어에서만 검색</p>
              <p>• <strong>내용 검색:</strong> 설명에서만 검색</p>
            </div>
          </div>
        )}
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
