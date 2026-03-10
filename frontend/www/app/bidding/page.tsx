'use client';

import { useState, useRef } from 'react';
import { FolderOpen, Upload, X, Image, File } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import LoginModal from '@/components/LoginModal';
import { useAuthStore } from '@/store/auth';
import { removeRefreshTokenCookie } from '@/services/mainservice';

interface UploadedFile {
  id: string;
  file: File;
  preview?: string;
}

export default function BiddingPage() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeSidebarSection, setActiveSidebarSection] = useState<'notice' | 'news' | null>(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { isLoggedIn, userInfo, logout } = useAuthStore();
  const [isDetecting, setIsDetecting] = useState(false);
  const [detectMessage, setDetectMessage] = useState<string | null>(null);
  const [detectError, setDetectError] = useState<string | null>(null);

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return;

    Array.from(files).forEach((file) => {
      const id = `${Date.now()}-${Math.random()}`;
      const uploadedFile: UploadedFile = { id, file };

      // 이미지 파일인 경우 미리보기 생성
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
          setUploadedFiles((prev) =>
            prev.map((f) => (f.id === id ? { ...f, preview: e.target?.result as string } : f))
          );
        };
        reader.readAsDataURL(file);
      }

      setUploadedFiles((prev) => [...prev, uploadedFile]);
    });
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileSelect(e.target.files);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const removeFile = (id: string) => {
    setUploadedFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const handleCheckStamp = async () => {
    if (!uploadedFiles.length || isDetecting) return;

    const targetFile = uploadedFiles[0]?.file;
    if (!targetFile) return;

    setIsDetecting(true);
    setDetectMessage(null);
    setDetectError(null);

    try {
      const formData = new FormData();
      formData.append('file', targetFile);

      const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';
      const res = await fetch(`${baseUrl}/api/v1/detect`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.detail || `검출 실패 (status: ${res.status})`);
      }

      const summary = data.summary as {
        has_stamp_any: boolean;
        has_signature_any: boolean;
      };

      const hasStamp = summary?.has_stamp_any;
      const hasSignature = summary?.has_signature_any;
      const parts: string[] = [];
      parts.push(hasStamp ? '인감 검출됨' : '인감 없음');
      parts.push(hasSignature ? '서명 검출됨' : '서명 없음');

      setDetectMessage(parts.join(' / '));
    } catch (error) {
      setDetectError(
        error instanceof Error
          ? error.message
          : '인감 유무 확인 중 오류가 발생했습니다.',
      );
    } finally {
      setIsDetecting(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
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
            <FolderOpen className="w-6 h-6 text-[#003478]" />
            <div className="flex flex-col">
              <h1 className="text-xl font-bold text-[#003478]">입찰서류 관리 AI</h1>
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
        <div className="space-y-6">
          {/* 파일 업로드 영역 */}
          <div className="bg-white/90 backdrop-blur-sm rounded-lg border-2 border-dashed border-gray-300 p-8">
            <div
              className={`text-center ${isDragging ? 'border-[#003478] bg-blue-50' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/*,.pdf,.doc,.docx,.xls,.xlsx"
                onChange={handleFileInputChange}
                className="hidden"
                id="file-upload-bidding"
              />
              <label
                htmlFor="file-upload-bidding"
                className="cursor-pointer flex flex-col items-center justify-center"
              >
                <Upload className="w-12 h-12 text-[#003478] mb-4" />
                <p className="text-lg font-semibold text-gray-700 mb-2">
                  파일을 드래그하거나 클릭하여 업로드
                </p>
                <p className="text-sm text-gray-500 mb-4">
                  이미지, PDF, 문서 파일을 업로드할 수 있습니다
                </p>
                <button
                  type="button"
                  className="px-6 py-2 bg-[#003478] text-white rounded-lg hover:bg-[#002a5c] transition-colors font-medium"
                >
                  파일 선택
                </button>
              </label>
            </div>
          </div>

          {/* 인감 유무 확인 버튼 및 결과 */}
          {uploadedFiles.length > 0 && (
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
              <button
                type="button"
                onClick={handleCheckStamp}
                disabled={isDetecting}
                className={`px-6 py-2 rounded-lg text-sm font-medium text-white transition-colors ${
                  isDetecting ? 'bg-gray-400 cursor-not-allowed' : 'bg-emerald-600 hover:bg-emerald-700'
                }`}
              >
                {isDetecting ? '검출 중...' : '인감 유무 확인'}
              </button>
              <div className="text-sm">
                {detectMessage && (
                  <p className="text-gray-700">{detectMessage}</p>
                )}
                {detectError && (
                  <p className="text-red-600">{detectError}</p>
                )}
              </div>
            </div>
          )}

          {/* 업로드된 파일 목록 */}
          {uploadedFiles.length > 0 && (
            <div className="bg-white/90 backdrop-blur-sm rounded-lg border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">
                업로드된 파일 ({uploadedFiles.length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {uploadedFiles.map((uploadedFile) => (
                  <div
                    key={uploadedFile.id}
                    className="relative border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    <button
                      onClick={() => removeFile(uploadedFile.id)}
                      className="absolute top-2 right-2 p-1 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors"
                      aria-label="파일 삭제"
                    >
                      <X className="w-4 h-4" />
                    </button>

                    {uploadedFile.preview ? (
                      <div className="mb-3">
                        <img
                          src={uploadedFile.preview}
                          alt={uploadedFile.file.name}
                          className="w-full h-32 object-cover rounded"
                        />
                      </div>
                    ) : (
                      <div className="mb-3 flex items-center justify-center h-32 bg-gray-100 rounded">
                        {uploadedFile.file.type.includes('pdf') ? (
                          <File className="w-12 h-12 text-red-500" />
                        ) : (
                          <FolderOpen className="w-12 h-12 text-[#003478]" />
                        )}
                      </div>
                    )}

                    <div className="mt-2">
                      <p className="text-sm font-medium text-gray-800 truncate" title={uploadedFile.file.name}>
                        {uploadedFile.file.name}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {formatFileSize(uploadedFile.file.size)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 안내 메시지 */}
          {uploadedFiles.length === 0 && (
            <div className="text-center py-8">
              <FolderOpen className="w-16 h-16 text-[#003478] mx-auto mb-4 opacity-50" />
              <h2 className="text-2xl font-semibold text-gray-700 mb-2">
                입찰서류 관리 AI
              </h2>
              <p className="text-gray-600">
                스캔본이나 첨부파일을 업로드하여 AI로 입찰서류를 관리할 수 있습니다.
              </p>
            </div>
          )}
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
