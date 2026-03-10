'use client';

import { useState, useRef } from 'react';
import { FileSpreadsheet, Upload, X } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import LoginModal from '@/components/LoginModal';
import { useAuthStore } from '@/store/auth';
import { removeRefreshTokenCookie } from '@/services/mainservice';

/** 회사정보 섹션: 구분만 표시, 입력 필드 목록 */
const COMPANY_FIELDS = [
  { key: '회사명', label: '회사명' },
  { key: '담당자명', label: '담당자명' },
  { key: '사업자번호', label: '사업자번호' },
  { key: '담당자연락처', label: '담당자 연락처' },
  { key: '회사주소', label: '회사주소' },
  { key: '담당자이메일', label: '담당자 이메일' },
  { key: '통화단위', label: '통화 단위' },
  { key: '데이터기준기간시작일', label: '데이터 기준기간 시작일' },
  { key: '데이터기준기간종료일', label: '데이터 기준기간 종료일' },
] as const;

/** 생산량 섹션: 구분만 표시, 입력 필드 목록 */
const PRODUCTION_FIELDS = [
  { key: '연도', label: '연도' },
  { key: '월', label: '월' },
  { key: '사업장명', label: '사업장명' },
  { key: '제품명', label: '제품명' },
  { key: '제품코드', label: '제품코드' },
  { key: '생산량', label: '생산량' },
  { key: '단위', label: '단위 (개, kg 등)' },
] as const;

type CompanyKey = (typeof COMPANY_FIELDS)[number]['key'];
type ProductionKey = (typeof PRODUCTION_FIELDS)[number]['key'];
type TemplateState = Record<CompanyKey | ProductionKey, string>;

const initialTemplate = (): TemplateState => {
  const state = {} as TemplateState;
  [...COMPANY_FIELDS, ...PRODUCTION_FIELDS].forEach(({ key }) => {
    state[key] = '';
  });
  return state;
};

export default function ExcelPage() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeSidebarSection, setActiveSidebarSection] = useState<'notice' | 'news' | null>(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [template, setTemplate] = useState<TemplateState>(initialTemplate());
  const [excelFile, setExcelFile] = useState<File | null>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [extractMessage, setExtractMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { isLoggedIn, userInfo, logout } = useAuthStore();

  const handleFileSelect = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    const ext = file.name.toLowerCase().split('.').pop();
    if (!['xlsx', 'xls'].includes(ext || '')) {
      setExtractError('Excel 파일(.xlsx, .xls)만 업로드할 수 있습니다.');
      return;
    }
    setExtractError(null);
    setExtractMessage(null);
    setExcelFile(file);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileSelect(e.target.files);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeFile = () => {
    setExcelFile(null);
    setExtractError(null);
    setExtractMessage(null);
  };

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

  const handleExtractFromExcel = async () => {
    if (!excelFile) {
      setExtractError('Excel 파일을 먼저 업로드해 주세요.');
      return;
    }
    setExtractError(null);
    setExtractMessage(null);
    setIsExtracting(true);

    const formData = new FormData();
    formData.append('file', excelFile);

    try {
      const res = await fetch(
        `${apiBaseUrl}/api/v1/excel/extract-and-correct?use_semantic_matching=true&use_gemini=true`,
        {
          method: 'POST',
          body: formData,
        }
      );
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        setExtractError(data.detail ?? data.error ?? `필드 추출 실패 (${res.status})`);
        return;
      }

      const fields = data.fields ?? {};
      const corrections = data.corrections ?? [];
      const usedGemini = data.used_gemini === true;

      setTemplate((prev) => {
        const next = { ...prev };
        (Object.keys(fields) as (keyof TemplateState)[]).forEach((key) => {
          const item = fields[key];
          const value = item?.value;
          if (value != null && String(value).trim() !== '') {
            next[key] = String(value).trim();
          }
        });
        return next;
      });

      const count = Object.keys(fields).length;
      let message = `Excel에서 ${count}개 항목을 추출해 템플릿에 반영했습니다.`;
      if (usedGemini && corrections.length > 0) {
        message += ` (Gemini 보정 ${corrections.length}건 적용)`;
      }
      message += ' 필요하면 수정해 주세요.';
      setExtractMessage(message);
    } catch (e) {
      setExtractError(e instanceof Error ? e.message : 'Excel 필드 추출 중 오류가 발생했습니다.');
    } finally {
      setIsExtracting(false);
    }
  };

  const updateTemplate = (key: keyof TemplateState, value: string) => {
    setTemplate((prev) => ({ ...prev, [key]: value }));
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
            <FileSpreadsheet className="w-6 h-6 text-[#003478]" />
            <div className="flex flex-col">
              <h1 className="text-xl font-bold text-[#003478]">Excel 템플릿 자동완성</h1>
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

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* 회사정보 섹션 (구분만) */}
        <div className="bg-white/90 backdrop-blur-sm rounded-xl border border-gray-200 shadow-sm p-6 mb-6">
          <h2 className="text-base font-semibold text-[#003478] border-b border-gray-200 pb-2 mb-4">회사정보</h2>
          <div className="space-y-4">
            {COMPANY_FIELDS.map(({ key, label }) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                <input
                  type="text"
                  value={template[key]}
                  onChange={(e) => updateTemplate(key, e.target.value)}
                  placeholder={`${label}을(를) 입력하세요`}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#003478] focus:border-transparent"
                />
              </div>
            ))}
          </div>
        </div>

        {/* 생산량 섹션 (구분만) */}
        <div className="bg-white/90 backdrop-blur-sm rounded-xl border border-gray-200 shadow-sm p-6 mb-8">
          <h2 className="text-base font-semibold text-[#003478] border-b border-gray-200 pb-2 mb-4">생산량</h2>
          <div className="space-y-4">
            {PRODUCTION_FIELDS.map(({ key, label }) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                <input
                  type="text"
                  value={template[key]}
                  onChange={(e) => updateTemplate(key, e.target.value)}
                  placeholder={`${label}을(를) 입력하세요`}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#003478] focus:border-transparent"
                />
              </div>
            ))}
          </div>
        </div>

        {/* Excel 업로드 + 자동 추출 */}
        <div className="bg-white/90 backdrop-blur-sm rounded-xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-lg font-semibold text-[#003478] mb-4">Excel에서 필드 자동 추출 + Gemini 보정</h2>
          <div
            className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center bg-gray-50/50"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls"
              onChange={handleFileInputChange}
              className="hidden"
              id="excel-file"
            />
            {!excelFile ? (
              <label htmlFor="excel-file" className="cursor-pointer flex flex-col items-center">
                <Upload className="w-12 h-12 text-[#003478] mb-3" />
                <p className="text-gray-700 font-medium mb-1">Excel 파일을 클릭하여 업로드</p>
                <p className="text-sm text-gray-500">.xlsx, .xls (항목·내용 열이 있는 시트)</p>
              </label>
            ) : (
              <div className="relative inline-flex items-center justify-center px-4 py-3 bg-white border border-gray-200 rounded-lg">
                <div className="flex items-center gap-3">
                  <FileSpreadsheet className="w-6 h-6 text-[#003478]" />
                  <div className="flex flex-col items-start">
                    <span className="text-sm font-medium text-gray-800">{excelFile.name}</span>
                    <span className="text-xs text-gray-500">Excel 파일 — 추출 실행 시 위 템플릿에 자동 반영됩니다</span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={removeFile}
                  className="absolute -top-2 -right-2 p-1.5 bg-red-500 text-white rounded-full hover:bg-red-600"
                  aria-label="파일 제거"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
          {excelFile && (
            <div className="mt-4 flex justify-center">
              <button
                type="button"
                onClick={handleExtractFromExcel}
                disabled={isExtracting}
                className="px-6 py-3 bg-[#003478] text-white rounded-lg hover:bg-[#002a5c] disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center gap-2"
              >
                <FileSpreadsheet className="w-5 h-5" />
                {isExtracting ? '추출 및 보정 중...' : 'Excel 추출 + Gemini 보정'}
              </button>
            </div>
          )}

          {extractError && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {extractError}
            </div>
          )}
          {extractMessage && (
            <div className="mt-4 p-3 bg-[#003478]/10 border border-[#003478]/30 rounded-lg text-sm text-[#003478]">
              {extractMessage}
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
            const data = (await res.json()) as { url?: string };
            if (data.url) {
              setIsLoginModalOpen(false);
              window.location.href = data.url;
            } else {
              alert('로그인 URL을 받지 못했습니다.');
            }
          } catch (e) {
            alert(`로그인 요청 오류: ${e instanceof Error ? e.message : String(e)}`);
          }
        }}
      />
    </div>
  );
}
