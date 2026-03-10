'use client';

import { useState, useRef } from 'react';
import { FolderOpen, Upload, X, FileText, FileCheck } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import LoginModal from '@/components/LoginModal';
import { useAuthStore } from '@/store/auth';
import { removeRefreshTokenCookie } from '@/services/mainservice';

export default function EvaluationPage() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeSidebarSection, setActiveSidebarSection] = useState<'notice' | 'news' | null>(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  // RfP PDF
  const [rfpFile, setRfpFile] = useState<File | null>(null);
  const [rfpId, setRfpId] = useState<string | null>(null);
  const [isRfpUploading, setIsRfpUploading] = useState(false);
  const [rfpError, setRfpError] = useState<string | null>(null);
  const rfpInputRef = useRef<HTMLInputElement>(null);

  // 제안서 PDF
  const [proposalFile, setProposalFile] = useState<File | null>(null);
  const [proposalId, setProposalId] = useState<string | null>(null);
  const [isProposalUploading, setIsProposalUploading] = useState(false);
  const [proposalError, setProposalError] = useState<string | null>(null);
  const proposalInputRef = useRef<HTMLInputElement>(null);

  // 평가 실행
  const [isEvaluating, setIsEvaluating] = useState(false);
  const [evaluateError, setEvaluateError] = useState<string | null>(null);
  const [evaluateResult, setEvaluateResult] = useState<{ total_score?: number; summary?: string } | null>(null);

  const { isLoggedIn, userInfo, logout } = useAuthStore();

  const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

  const handleRfpSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setRfpFile(file);
      setRfpId(null);
      setRfpError(null);
      setEvaluateResult(null);
    }
    if (rfpInputRef.current) rfpInputRef.current.value = '';
  };

  const handleProposalSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setProposalFile(file);
      setProposalId(null);
      setProposalError(null);
      setEvaluateResult(null);
    }
    if (proposalInputRef.current) proposalInputRef.current.value = '';
  };

  const uploadRfp = async () => {
    if (!rfpFile || isRfpUploading) return;
    setIsRfpUploading(true);
    setRfpError(null);
    try {
      const formData = new FormData();
      formData.append('file', rfpFile);
      const res = await fetch(`${baseUrl}/api/v1/evaluation/rfp/upload`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.message || data.detail || `업로드 실패 (${res.status})`);
      const id = data.document?.metadata?.rfp_id ?? data.document?.rfp_id;
      setRfpId(id || '업로드됨');
    } catch (err) {
      setRfpError(err instanceof Error ? err.message : 'RfP 업로드 중 오류가 발생했습니다.');
    } finally {
      setIsRfpUploading(false);
    }
  };

  const uploadProposal = async () => {
    if (!proposalFile || isProposalUploading) return;
    setIsProposalUploading(true);
    setProposalError(null);
    try {
      const formData = new FormData();
      formData.append('file', proposalFile);
      const res = await fetch(`${baseUrl}/api/v1/evaluation/proposal/upload`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.message || data.detail || `업로드 실패 (${res.status})`);
      const id = data.document?.metadata?.proposal_id ?? data.document?.proposal_id;
      setProposalId(id || '업로드됨');
    } catch (err) {
      setProposalError(err instanceof Error ? err.message : '제안서 업로드 중 오류가 발생했습니다.');
    } finally {
      setIsProposalUploading(false);
    }
  };

  const runEvaluation = async () => {
    if (!rfpId || rfpId === '업로드됨' || !proposalId || proposalId === '업로드됨') {
      setEvaluateError('먼저 RfP와 제안서를 업로드해 주세요.');
      return;
    }
    setIsEvaluating(true);
    setEvaluateError(null);
    setEvaluateResult(null);
    try {
      const res = await fetch(`${baseUrl}/api/v1/evaluation/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          rfp_id: rfpId,
          proposal_id: proposalId,
          use_llm: true,
          detailed_analysis: true,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.message || data.detail || `평가 실패 (${res.status})`);
      setEvaluateResult({
        total_score: data.report?.total_score ?? data.report?.percentage,
        summary: data.report?.summary,
      });
    } catch (err) {
      setEvaluateError(err instanceof Error ? err.message : '평가 실행 중 오류가 발생했습니다.');
    } finally {
      setIsEvaluating(false);
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
      {/* 헤더 */}
      <header className="w-full flex items-center justify-between p-4 bg-white/80 backdrop-blur-sm border-b border-[#003478]/20">
        <div className="flex items-center gap-4">
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
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div className="flex items-center gap-3">
            <FileCheck className="w-6 h-6 text-[#003478]" />
            <div className="flex flex-col">
              <h1 className="text-xl font-bold text-[#003478]">RfP 평가 시스템</h1>
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
          {/* 1. RfP PDF 업로드 */}
          <div className="bg-white/90 backdrop-blur-sm rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-[#003478] mb-3 flex items-center gap-2">
              <FileText className="w-5 h-5" />
              1. RfP PDF 업로드
            </h2>
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
              <input
                ref={rfpInputRef}
                type="file"
                accept=".pdf,application/pdf"
                onChange={handleRfpSelect}
                className="hidden"
                id="rfp-upload"
              />
              <label
                htmlFor="rfp-upload"
                className="cursor-pointer px-4 py-2 rounded-lg border-2 border-dashed border-gray-300 hover:border-[#003478] hover:bg-blue-50/50 transition-colors text-sm font-medium text-gray-700"
              >
                RfP PDF 선택
              </label>
              {rfpFile && (
                <>
                  <span className="text-sm text-gray-600">
                    {rfpFile.name} ({formatFileSize(rfpFile.size)})
                  </span>
                  <button
                    type="button"
                    onClick={uploadRfp}
                    disabled={isRfpUploading}
                    className={`px-4 py-2 rounded-lg text-sm font-medium text-white ${
                      isRfpUploading ? 'bg-gray-400 cursor-not-allowed' : 'bg-[#003478] hover:bg-[#002a5c]'
                    }`}
                  >
                    {isRfpUploading ? '업로드 중...' : '업로드'}
                  </button>
                  {rfpId && (
                    <span className="text-sm text-emerald-600 font-medium">RfP ID: {rfpId}</span>
                  )}
                </>
              )}
            </div>
            {rfpError && <p className="mt-2 text-sm text-red-600">{rfpError}</p>}
          </div>

          {/* 2. 제안서 PDF 업로드 */}
          <div className="bg-white/90 backdrop-blur-sm rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-[#003478] mb-3 flex items-center gap-2">
              <FileCheck className="w-5 h-5" />
              2. 제안서 PDF 업로드
            </h2>
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
              <input
                ref={proposalInputRef}
                type="file"
                accept=".pdf,application/pdf"
                onChange={handleProposalSelect}
                className="hidden"
                id="proposal-upload"
              />
              <label
                htmlFor="proposal-upload"
                className="cursor-pointer px-4 py-2 rounded-lg border-2 border-dashed border-gray-300 hover:border-[#003478] hover:bg-blue-50/50 transition-colors text-sm font-medium text-gray-700"
              >
                제안서 PDF 선택
              </label>
              {proposalFile && (
                <>
                  <span className="text-sm text-gray-600">
                    {proposalFile.name} ({formatFileSize(proposalFile.size)})
                  </span>
                  <button
                    type="button"
                    onClick={uploadProposal}
                    disabled={isProposalUploading}
                    className={`px-4 py-2 rounded-lg text-sm font-medium text-white ${
                      isProposalUploading ? 'bg-gray-400 cursor-not-allowed' : 'bg-[#003478] hover:bg-[#002a5c]'
                    }`}
                  >
                    {isProposalUploading ? '업로드 중...' : '업로드'}
                  </button>
                  {proposalId && (
                    <span className="text-sm text-emerald-600 font-medium">제안서 ID: {proposalId}</span>
                  )}
                </>
              )}
            </div>
            {proposalError && <p className="mt-2 text-sm text-red-600">{proposalError}</p>}
          </div>

          {/* 3. 평가 실행 */}
          <div className="bg-white/90 backdrop-blur-sm rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-[#003478] mb-3">3. 평가 실행</h2>
            <button
              type="button"
              onClick={runEvaluation}
              disabled={isEvaluating || !rfpId || !proposalId}
              className={`px-6 py-2 rounded-lg text-sm font-medium text-white ${
                isEvaluating || !rfpId || !proposalId
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-emerald-600 hover:bg-emerald-700'
              }`}
            >
              {isEvaluating ? '평가 중...' : '평가 실행'}
            </button>
            {evaluateError && <p className="mt-2 text-sm text-red-600">{evaluateError}</p>}
            {evaluateResult && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                {evaluateResult.total_score != null && (
                  <p className="font-medium text-gray-800">종합 점수: {evaluateResult.total_score.toFixed(1)}점</p>
                )}
                {evaluateResult.summary && (
                  <p className="mt-2 text-sm text-gray-600">{evaluateResult.summary}</p>
                )}
              </div>
            )}
          </div>

          {/* 안내 메시지 */}
          <div className="text-center py-8">
            <FolderOpen className="w-16 h-16 text-[#003478] mx-auto mb-4 opacity-50" />
            <h2 className="text-2xl font-semibold text-gray-700 mb-2">RfP 평가 시스템</h2>
            <p className="text-gray-600">
              RfP(Request for Proposal)와 제안서 PDF를 업로드하여 AI로 요구사항 매칭 및 자동 평가를 수행할 수 있습니다.
            </p>
          </div>
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
        onKakaoLogin={async () => {
          alert('카카오 로그인은 준비 중입니다.');
        }}
        onNaverLogin={async () => {
          try {
            const oauthBase = process.env.NEXT_PUBLIC_OAUTH_BASE_URL ?? 'http://localhost:8080';
            const res = await fetch(`${oauthBase}/oauth/naver/login-url`, {
              method: 'GET',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
            });
            if (!res.ok) throw new Error('로그인 URL 요청 실패');
            const data = (await res.json()) as { url: string };
            if (!data.url) throw new Error('URL 없음');
            setIsLoginModalOpen(false);
            window.location.href = data.url;
          } catch (e) {
            alert(`로그인 요청 오류: ${e instanceof Error ? e.message : String(e)}`);
          }
        }}
      />
    </div>
  );
}
