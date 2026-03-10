'use client';

import { useState, useRef } from 'react';
import { Stamp, Upload, X, File, AlertCircle, CheckCircle2 } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import LoginModal from '@/components/LoginModal';
import { useAuthStore } from '@/store/auth';
import { removeRefreshTokenCookie } from '@/services/mainservice';

interface UploadedFile {
  id: string;
  file: File;
}

interface Detection {
  cls: string;
  conf: number;
  xyxy: [number, number, number, number];
}

interface PageResult {
  page_index: number;
  has_stamp: boolean;
  has_signature: boolean;
  detections: Detection[];
}

interface DetectResponse {
  job_id: string;
  filename: string;
  num_pages: number;
  summary: {
    has_stamp_any: boolean;
    has_signature_any: boolean;
    stamp_pages: number[];
    signature_pages: number[];
  };
  pages: PageResult[];
}

export default function StampDetectPage() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeSidebarSection, setActiveSidebarSection] = useState<'notice' | 'news' | null>(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isDetecting, setIsDetecting] = useState(false);
  const [detectError, setDetectError] = useState<string | null>(null);
  const [detectResult, setDetectResult] = useState<DetectResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { isLoggedIn, userInfo, logout } = useAuthStore();

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return;
    const pdfFiles = Array.from(files).filter((f) => f.name.toLowerCase().endsWith('.pdf'));
    if (pdfFiles.length === 0) {
      setDetectError('PDF 파일만 업로드할 수 있습니다.');
      return;
    }
    setUploadedFiles(pdfFiles.map((file) => ({ id: `${Date.now()}-${Math.random()}`, file })));
    setDetectResult(null);
    setDetectError(null);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileSelect(e.target.files);
    if (fileInputRef.current) fileInputRef.current.value = '';
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
    setDetectResult(null);
    setDetectError(null);
  };

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

  const handleDetect = async () => {
    const pdfFile = uploadedFiles[0]?.file;
    if (!pdfFile) {
      setDetectError('PDF 파일을 먼저 업로드해 주세요.');
      return;
    }
    setDetectError(null);
    setDetectResult(null);
    setIsDetecting(true);
    try {
      const formData = new FormData();
      formData.append('file', pdfFile);
      const res = await fetch(`${apiBaseUrl}/api/v1/detect`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const rawDetail = data.detail ?? data.error ?? `검출 실패 (${res.status})`;
        const message = typeof rawDetail === 'string'
          ? rawDetail
          : Array.isArray(rawDetail) && rawDetail[0]?.msg
            ? rawDetail[0].msg
            : String(rawDetail);
        const isModelNotLoaded =
          res.status === 503 ||
          /검출 모델이 로드되지 않았습니다|YOLO_MODEL_PATH/i.test(message);
        setDetectError(
          isModelNotLoaded
            ? '인감도장 검출 모델이 서버에 설정되지 않았습니다. 서버의 models/stamp_detector/ 폴더에 학습된 모델(best.pt)을 배치하거나, 환경변수 YOLO_MODEL_PATH를 설정해 주세요. 관리자에게 문의하시면 됩니다.'
            : message
        );
        return;
      }
      setDetectResult(data as DetectResponse);
    } catch (e) {
      setDetectError(e instanceof Error ? e.message : '검출 요청 중 오류가 발생했습니다.');
    } finally {
      setIsDetecting(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-blue-100 to-white">
      <header className="w-full flex items-center justify-between p-4 bg-white/80 backdrop-blur-sm border-b border-[#003478]/20">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setIsSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-gray-200 transition-colors"
            aria-label="메뉴 열기"
          >
            <svg className="w-6 h-6 text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="flex items-center gap-3">
            <Stamp className="w-6 h-6 text-[#003478]" />
            <div className="flex flex-col">
              <h1 className="text-xl font-bold text-[#003478]">인감도장/서명 검출 AI</h1>
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold text-[#003478]">KOICA</span>
                <span className="text-xs text-gray-600 font-serif">Korea International Cooperation Agency</span>
              </div>
            </div>
          </div>
        </div>

        {isLoggedIn ? (
          <div className="flex items-center gap-3">
            {userInfo?.name && <span className="text-sm text-gray-700 font-medium">{userInfo.name}님</span>}
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

      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="space-y-6">
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
                accept=".pdf"
                onChange={handleFileInputChange}
                className="hidden"
                id="file-upload-stamp"
              />
              <label htmlFor="file-upload-stamp" className="cursor-pointer flex flex-col items-center justify-center">
                <Upload className="w-12 h-12 text-[#003478] mb-4" />
                <p className="text-lg font-semibold text-gray-700 mb-2">PDF 파일을 드래그하거나 클릭하여 업로드</p>
                <p className="text-sm text-gray-500 mb-4">입찰서류 PDF에서 인감도장과 서명을 자동으로 검출합니다</p>
                <button
                  type="button"
                  className="px-6 py-2 bg-[#003478] text-white rounded-lg hover:bg-[#002a5c] transition-colors font-medium"
                >
                  파일 선택
                </button>
              </label>
            </div>
          </div>

          {uploadedFiles.length > 0 && (
            <div className="flex justify-center">
              <button
                type="button"
                onClick={handleDetect}
                disabled={isDetecting}
                className="px-6 py-3 bg-[#003478] text-white rounded-lg hover:bg-[#002a5c] disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
              >
                {isDetecting ? '검출 중...' : '인감도장/서명 검출 시작'}
              </button>
            </div>
          )}

          {detectError && (
            <div
              className={
                detectError.includes('모델이 서버에 설정되지 않았습니다')
                  ? 'bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start gap-3'
                  : 'bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3'
              }
            >
              <AlertCircle
                className={
                  detectError.includes('모델이 서버에 설정되지 않았습니다')
                    ? 'w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5'
                    : 'w-5 h-5 text-red-600 flex-shrink-0 mt-0.5'
                }
              />
              <p
                className={
                  detectError.includes('모델이 서버에 설정되지 않았습니다')
                    ? 'text-amber-800'
                    : 'text-red-700'
                }
              >
                {detectError}
              </p>
            </div>
          )}

          {detectResult && (
            <div className="space-y-4">
              <div className="bg-white/90 backdrop-blur-sm rounded-lg border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-green-600" />
                  검출 결과 요약
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="bg-blue-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600 mb-1">총 페이지</p>
                    <p className="text-2xl font-bold text-[#003478]">{detectResult.num_pages}</p>
                  </div>
                  <div className="bg-green-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600 mb-1">인감도장 검출</p>
                    <p className="text-2xl font-bold text-green-600">
                      {detectResult.summary.has_stamp_any ? '있음' : '없음'}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {detectResult.summary.stamp_pages.length}개 페이지
                    </p>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600 mb-1">서명 검출</p>
                    <p className="text-2xl font-bold text-purple-600">
                      {detectResult.summary.has_signature_any ? '있음' : '없음'}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {detectResult.summary.signature_pages.length}개 페이지
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <p className="text-sm text-gray-600 mb-1">Job ID</p>
                    <p className="text-xs font-mono text-gray-700 break-all">{detectResult.job_id}</p>
                  </div>
                </div>
              </div>

              <div className="bg-white/90 backdrop-blur-sm rounded-lg border border-gray-200 p-6">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">페이지별 검출 상세</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b">
                      <tr>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">페이지</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">인감도장</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">서명</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">검출 개수</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">상세</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {detectResult.pages.map((page) => (
                        <tr key={page.page_index} className="hover:bg-gray-50">
                          <td className="px-4 py-3 font-medium text-gray-900">{page.page_index + 1}</td>
                          <td className="px-4 py-3">
                            {page.has_stamp ? (
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700">
                                있음
                              </span>
                            ) : (
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                                없음
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            {page.has_signature ? (
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-700">
                                있음
                              </span>
                            ) : (
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                                없음
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3 text-gray-700">{page.detections.length}개</td>
                          <td className="px-4 py-3">
                            {page.detections.length > 0 && (
                              <details className="cursor-pointer">
                                <summary className="text-[#003478] hover:underline">보기</summary>
                                <div className="mt-2 space-y-1 text-xs text-gray-600">
                                  {page.detections.map((det, idx) => (
                                    <div key={idx} className="pl-4 border-l-2 border-gray-200">
                                      <span className="font-semibold">{det.cls}</span> (신뢰도: {(det.conf * 100).toFixed(1)}%)
                                      <br />
                                      좌표: [{det.xyxy.map((v) => v.toFixed(0)).join(', ')}]
                                    </div>
                                  ))}
                                </div>
                              </details>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {uploadedFiles.length > 0 && (
            <div className="bg-white/90 backdrop-blur-sm rounded-lg border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-800 mb-4">업로드된 파일</h3>
              {uploadedFiles.map((uploadedFile) => (
                <div key={uploadedFile.id} className="flex items-center justify-between border border-gray-200 rounded-lg p-4">
                  <div className="flex items-center gap-3">
                    <File className="w-8 h-8 text-red-500" />
                    <div>
                      <p className="text-sm font-medium text-gray-800">{uploadedFile.file.name}</p>
                      <p className="text-xs text-gray-500">{formatFileSize(uploadedFile.file.size)}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => removeFile(uploadedFile.id)}
                    className="p-2 bg-red-500 text-white rounded-full hover:bg-red-600 transition-colors"
                    aria-label="파일 삭제"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {uploadedFiles.length === 0 && !detectResult && (
            <div className="text-center py-8">
              <Stamp className="w-16 h-16 text-[#003478] mx-auto mb-4 opacity-50" />
              <h2 className="text-2xl font-semibold text-gray-700 mb-2">인감도장/서명 검출 AI</h2>
              <p className="text-gray-600">입찰서류 PDF를 업로드하여 인감도장과 서명을 자동으로 검출합니다.</p>
            </div>
          )}
        </div>
      </main>

      <Sidebar
        isOpen={isSidebarOpen}
        onClose={() => {
          setIsSidebarOpen(false);
          setActiveSidebarSection(null);
        }}
        activeSection={activeSidebarSection}
        onSectionChange={setActiveSidebarSection}
      />

      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onKakaoLogin={async () => alert('카카오 로그인은 준비 중입니다.')}
        onNaverLogin={async () => {
          try {
            const baseUrl = process.env.NEXT_PUBLIC_OAUTH_BASE_URL ?? 'http://localhost:8080';
            const res = await fetch(`${baseUrl}/oauth/naver/login-url`, {
              method: 'GET',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
            });
            if (!res.ok) {
              alert(`로그인 URL 요청 실패: ${res.status}`);
              return;
            }
            const data = (await res.json()) as { url: string };
            if (!data.url) {
              alert('로그인 URL을 받지 못했습니다.');
              return;
            }
            setIsLoginModalOpen(false);
            window.location.href = data.url;
          } catch (error) {
            alert(`로그인 요청 중 오류: ${error instanceof Error ? error.message : String(error)}`);
          }
        }}
      />
    </div>
  );
}
