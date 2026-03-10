'use client';

import { useState, useRef, useEffect } from 'react';
import { MessageSquare } from 'lucide-react';
import LoginModal from '@/components/LoginModal';
import Sidebar from '@/components/Sidebar';
import { useAuthStore } from '@/store/auth';
import { removeRefreshTokenCookie } from '@/services/mainservice';

interface AttachedFile {
  id: string;
  file: File;
  preview?: string;
}

export default function ChatPage() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Array<{ role: 'user' | 'assistant'; content: string; files?: AttachedFile[] }>>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeSidebarSection, setActiveSidebarSection] = useState<'notice' | 'news' | null>(null);
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);

  // Zustand 스토어에서 인증 상태 가져오기
  const { isLoggedIn, userInfo, logout } = useAuthStore();

  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 메시지 추가 시 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 입력창 자동 높이 조절
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${inputRef.current.scrollHeight}px`;
    }
  }, [input]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const newFiles: AttachedFile[] = files.map(file => ({
      id: Math.random().toString(36).substring(7),
      file,
      preview: file.type.startsWith('image/') ? URL.createObjectURL(file) : undefined,
    }));
    setAttachedFiles(prev => [...prev, ...newFiles]);
    // 파일 입력 초기화 (같은 파일 다시 선택 가능하도록)
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeFile = (fileId: string) => {
    setAttachedFiles(prev => {
      const fileToRemove = prev.find(f => f.id === fileId);
      if (fileToRemove?.preview) {
        URL.revokeObjectURL(fileToRemove.preview);
      }
      return prev.filter(f => f.id !== fileId);
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!input.trim() && attachedFiles.length === 0) || isLoading) return;

    const userMessage = input.trim();
    const filesToSend = [...attachedFiles];
    setInput('');
    setAttachedFiles([]);
    setMessages(prev => [...prev, { role: 'user', content: userMessage, files: filesToSend }]);
    setIsLoading(true);

    try {
      // API 호출
      const response = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
        }),
      });

      if (!response.ok) {
        throw new Error('응답을 받지 못했습니다.');
      }

      const data = await response.json();
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: data.response || '응답을 받았습니다.' }
      ]);
    } catch (error) {
      setMessages(prev => [
        ...prev,
        { role: 'assistant', content: '죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.' }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-100 to-white flex flex-col">
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
            <MessageSquare className="w-6 h-6 text-[#003478]" />
            <div className="flex flex-col">
              <h1 className="text-xl font-bold text-[#003478]">대화형 업무지원 AI</h1>
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

      {/* 메인 컨텐츠 영역 */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* 채팅 메시지 영역 */}
        <div className="flex-1 overflow-y-auto px-8 py-8">
          <div className="w-full max-w-5xl mx-auto">
            {messages.length > 0 ? (
              <div className="space-y-4">
                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-3 ${message.role === 'user'
                        ? 'bg-[#003478] text-white'
                        : 'bg-white/90 backdrop-blur-sm text-gray-800 shadow-sm border border-gray-200'
                        }`}
                    >
                      {message.files && message.files.length > 0 && (
                        <div className="mb-2 flex flex-wrap gap-2">
                          {message.files.map((file) => (
                            <div
                              key={file.id}
                              className={`flex items-center gap-2 rounded-lg px-2 py-1 text-xs ${message.role === 'user'
                                ? 'bg-white/20 text-white'
                                : 'bg-gray-100 text-gray-700'
                                }`}
                            >
                              {file.preview ? (
                                <img
                                  src={file.preview}
                                  alt={file.file.name}
                                  className="w-6 h-6 object-cover rounded"
                                />
                              ) : (
                                <svg
                                  className="w-4 h-4"
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                                  />
                                </svg>
                              )}
                              <span className="max-w-[100px] truncate">{file.file.name}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      {message.content && (
                        <p className="whitespace-pre-wrap break-words">{message.content}</p>
                      )}
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-white rounded-2xl px-4 py-3 shadow-sm border border-gray-200">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            ) : (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-400 text-center">메시지를 입력하여 대화를 시작하세요.</p>
              </div>
            )}
          </div>
        </div>

        {/* 입력창 영역 (하단 고정) */}
        <div className="border-t border-[#003478]/20 bg-white/80 backdrop-blur-sm px-8 py-4">
          <div className="w-full max-w-5xl mx-auto">
            {/* 첨부된 파일 목록 */}
            {attachedFiles.length > 0 && (
              <div className="mb-3 flex flex-wrap gap-2">
                {attachedFiles.map((file) => (
                  <div
                    key={file.id}
                    className="flex items-center gap-2 bg-white/80 backdrop-blur-sm border border-[#003478]/30 rounded-lg px-3 py-2 text-sm"
                  >
                    {file.preview ? (
                      <img
                        src={file.preview}
                        alt={file.file.name}
                        className="w-8 h-8 object-cover rounded"
                      />
                    ) : (
                      <svg
                        className="w-6 h-6 text-[#003478]"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                      </svg>
                    )}
                    <span className="text-gray-700 max-w-[150px] truncate">{file.file.name}</span>
                    <button
                      type="button"
                      onClick={() => removeFile(file.id)}
                      className="text-gray-500 hover:text-red-500 transition-colors"
                      aria-label="파일 제거"
                    >
                      <svg
                        className="w-4 h-4"
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
                    </button>
                  </div>
                ))}
              </div>
            )}

            <form onSubmit={handleSubmit} className="relative w-full">
              <div className="flex items-center gap-2">
                {/* 파일 첨부 버튼 */}
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  onChange={handleFileSelect}
                  className="hidden"
                  id="file-attachment"
                  aria-label="파일 첨부"
                />
                <label
                  htmlFor="file-attachment"
                  className="p-2 rounded-lg bg-white/80 backdrop-blur-sm border border-[#003478]/30 text-[#003478] hover:bg-white hover:border-[#003478] transition-colors cursor-pointer flex-shrink-0"
                  aria-label="파일 첨부"
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
                    />
                  </svg>
                </label>

                <div className="flex-1 relative">
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="메시지를 입력하세요... (Enter로 전송, Shift+Enter로 줄바꿈)"
                    className="w-full px-4 py-3 pr-14 bg-white/80 backdrop-blur-sm border border-[#003478] rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-[#003478] focus:border-[#003478] max-h-32 overflow-y-auto text-gray-800"
                    rows={1}
                    disabled={isLoading}
                  />
                  <button
                    type="submit"
                    disabled={(!input.trim() && attachedFiles.length === 0) || isLoading}
                    className="absolute right-2 bottom-2 p-2 rounded bg-[#003478] text-white hover:bg-[#002a5c] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    aria-label="전송"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 10l7-7m0 0l7 7m-7-7v18"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            </form>

            {/* 하단 안내 문구 */}
            <p className="text-xs text-gray-500 text-center mt-3">
              AI는 실수할 수 있습니다. 중요한 정보는 확인하세요.
            </p>
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
              headers: {
                'Content-Type': 'application/json',
              },
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
