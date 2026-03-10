'use client';

import { useState, useRef } from 'react';
import { ScanText, Upload, X } from 'lucide-react';
import Sidebar from '@/components/Sidebar';
import LoginModal from '@/components/LoginModal';
import { useAuthStore } from '@/store/auth';
import { removeRefreshTokenCookie } from '@/services/mainservice';

const TEMPLATE_FIELDS = [
  { key: '담당자이름', label: '담당자 이름' },
  { key: '회사명', label: '회사명' },
  { key: '사업자번호', label: '사업자 번호' },
  { key: '회사연락처', label: '회사 연락처' },
  { key: '회사주소', label: '회사 주소' },
  { key: '주요내용', label: '주요 내용' },
  { key: '작성날짜', label: '작성 날짜' },
] as const;

type TemplateState = Record<(typeof TEMPLATE_FIELDS)[number]['key'], string>;

const initialTemplate: TemplateState = {
  담당자이름: '',
  회사명: '',
  사업자번호: '',
  회사연락처: '',
  회사주소: '',
  주요내용: '',
  작성날짜: '',
};

/** 위임장 등 문서에서 라벨 다음 값 추출 (다음 라벨 전까지) */
function extractAfterLabel(text: string, labels: string[], stopLabels?: string[]): string {
  const s = text.replace(/\s+/g, ' ').trim();
  const stop = stopLabels ?? ['사업자', '연락처', '주소', '회사명', '성명', '담당', '본인', '생년월일', '위임', '주요', '발행', '주식'];
  for (const label of labels) {
    const idx = s.indexOf(label);
    if (idx === -1) continue;
    let start = idx + label.length;
    while (start < s.length && /[\s:：\/]/.test(s[start])) start++;
    let end = start;
    while (end < s.length) {
      const rest = s.slice(end);
      const nextMatch = rest.match(/\s+(사업자|연락처|주\s*소|회사명|성\s*명|담당|본인|생년월일|위임내용|위임\s*내용|위임사항|주요|발행|주식수)/);
      if (nextMatch && nextMatch.index !== undefined && nextMatch.index > 0) {
        end += nextMatch.index;
        break;
      }
      if (nextMatch && nextMatch.index === 0) break;
      end++;
    }
    const value = s.slice(start, end).trim();
    if (value.length > 0 && value.length < 300) return value;
  }
  return '';
}

/** 담당자 이름: 수임인(대리인) 성명 — 첫 번째 "성명" 값 (한글 이름 2~5자) */
function extract담당자이름(text: string): string {
  const m = text.match(/성\s*명\s*[:：]?\s*([가-힣]{2,5})/);
  if (m?.[1]) return m[1].trim();
  return extractAfterLabel(text, ['성명', '담당자명', '담당자']);
}

/** 회사명: 발행회사명 — 숫자·괄호·주식수 앞까지만 (한글/영문 토큰만) */
function extract회사명(text: string): string {
  const m = text.match(/발행회사명\s*[:：]?\s*([가-힣a-zA-Z]+)/);
  if (m?.[1]) return m[1].trim();
  const v = extractAfterLabel(text, ['발행회사명', '회사명']);
  if (v) {
    const untilNumber = v.replace(/\d.*$/, '').replace(/\s*\(.*$/, '').trim();
    return untilNumber.replace(/\s+/g, '').slice(0, 30) || v.replace(/\s+/g, '').slice(0, 30);
  }
  return '';
}

/** 사업자 번호: XXX-XX-XXXXX (공백 허용). 위임인 쪽 마지막 매칭 */
function extract사업자번호(text: string): string {
  const withSpaces = text.match(/\d{3}\s*-\s*\d{2}\s*-\s*\d{5}/g);
  if (withSpaces && withSpaces.length > 0) {
    const last = withSpaces[withSpaces.length - 1]!.replace(/\s/g, '');
    if (last.length >= 10) return last;
  }
  const noSpaces = text.match(/\d{3}-\d{2}-\d{5}/g);
  if (noSpaces && noSpaces.length > 0) return noSpaces[noSpaces.length - 1]!;
  const afterLabel = text.match(/(?:사업자\s*번호|생년월일\s*\/\s*사업자\s*번호)\s*[:：]?\s*(\d{3}\s*-\s*\d{2}\s*-\s*\d{5})/);
  if (afterLabel?.[1]) return afterLabel[1].replace(/\s/g, '');
  return '';
}

/** 위임장에서 밑부분(위임인 블록)만 반환. 연락처/주소는 이 구간 것만 사용 */
function getBottomSection(text: string): string {
  const s = text.replace(/\s+/g, ' ').trim();
  const markers = [
    '위 사람에게 위임사항에 관한 행위 일체를 위임합니다',
    '위임합니다',
    '위임인성명',
    '위임인 성명',
    '생년월일/사업자번호',
  ];
  let lastIdx = -1;
  for (const marker of markers) {
    const idx = s.indexOf(marker);
    if (idx !== -1) lastIdx = Math.max(lastIdx, idx);
  }
  if (lastIdx !== -1) return s.slice(lastIdx);
  return s;
}

/** 회사 연락처: 밑부분(위임인) 구간에서만 추출. XXX-XXXX-XXXX 형식 */
function extract회사연락처(text: string): string {
  const bottom = getBottomSection(text);
  const strict = bottom.match(/\d{3}-\d{4}-\d{4}/g);
  if (strict && strict.length > 0) return strict[strict.length - 1]!;
  const loose = bottom.match(/\d{2,3}[-\s]?\d{3,4}[-\s]?\d{4}/g);
  if (loose) {
    const clean = loose
      .map((x) => x.replace(/\s/g, ''))
      .filter((x) => /^\d{2,3}-\d{3,4}-\d{4}$/.test(x) && !x.includes(')') && !x.includes('('));
    if (clean.length > 0) return clean[clean.length - 1]!;
  }
  const fromFull = extractAfterLabel(bottom, ['연락 처', '연락처']);
  if (fromFull) return fromFull;
  return extractAfterLabel(text, ['연락 처', '연락처']);
}

/** 회사 주소: 밑부분(위임인) 구간에서만 추출 */
function extract회사주소(text: string): string {
  const bottom = getBottomSection(text);
  const 세종 = bottom.match(/(세종\s*특별\s*자치시\s*흥덕구\s*감천로(?:\s*\d+)?)/);
  if (세종?.[1]) return 세종[1].replace(/\s+/g, ' ').trim();
  const 세종2 = bottom.match(/(세종특별자치시\s*흥덕구\s*감천로(?:\s*\d+)?)/);
  if (세종2?.[1]) return 세종2[1].replace(/\s+/g, ' ').trim();
  const 감천로 = bottom.match(/(세종[^0-9]*?흥덕구\s*감천로(?:\s*\d+)?)/);
  if (감천로?.[1]) return 감천로[1].replace(/\s+/g, ' ').trim();
  const 주소들: string[] = [];
  const re = /주\s*소\s*[:：]?\s*([^연락처사업자성명위임첨부]+?)(?=\s*(?:연락처|사업자|성명|위임인|첨부)|$)/g;
  let m;
  while ((m = re.exec(bottom)) !== null) if (m[1]) 주소들.push(m[1].trim());
  if (주소들.length > 0) return 주소들[주소들.length - 1]!;
  const fromFull = extractAfterLabel(bottom, ['주 소', '주소', '소재지']);
  if (fromFull) return fromFull;
  return extractAfterLabel(text, ['주 소', '주소', '소재지']);
}

/** 작성 날짜: 문서 맨 아래 위임일 (마지막 YYYY년 M월 D일) → "YYYY. MM. DD" */
function extract작성날짜(text: string): string {
  const format = (y: string, m: string, d: string) => `${y}. ${m.padStart(2, '0')}. ${d.padStart(2, '0')}`;
  const re1 = /(\d{4})\s*[.\s년]*\s*(\d{1,2})\s*[.\s월]*\s*(\d{1,2})\s*일?/g;
  let match;
  let last = '';
  while ((match = re1.exec(text)) !== null) {
    const [, y, m, d] = match;
    if (y && m && d) last = format(y, m, d);
  }
  if (last) return last;
  const re2 = /(\d{4})\s*[.\-]\s*(\d{1,2})\s*[.\-]\s*(\d{1,2})/g;
  while ((match = re2.exec(text)) !== null) {
    const [, y, m, d] = match;
    if (y && m && d) last = format(y, m, d);
  }
  return last;
}

/** 주요 내용(위임 내용): "위임내용" 다음 문구. OCR 오타 보정(수ㅇ→수령) */
function extract주요내용(text: string): string {
  let v = extractAfterLabel(text, ['위임내용', '위임 내용', '위임사항'], []);
  if (!v) {
    const 배당 = text.match(/배당금[^.]*행위/);
    v = 배당?.[0]?.trim() ?? '';
  }
  if (v) {
    v = v.slice(0, 200).trim();
    v = v.replace(/수ㅇ\s*예/g, '수령에').replace(/수ㅇ\s*에/g, '수령에').replace(/수ㅇ(?=[가-힣])/g, '수령');
  }
  return v;
}

/** OCR 결과를 템플릿 필드로 파싱 (위임장 등 한국어 서식 기준) */
function parseOcrToTemplate(fullText: string): Partial<TemplateState> {
  const t = fullText.replace(/\s+/g, ' ').trim();
  const result: Partial<TemplateState> = {};

  const 담당자 = extract담당자이름(t);
  if (담당자) result.담당자이름 = 담당자;

  const 회사명 = extract회사명(t);
  if (회사명) result.회사명 = 회사명;

  const 사업자 = extract사업자번호(t);
  if (사업자) result.사업자번호 = 사업자;

  const 연락처 = extract회사연락처(t);
  if (연락처) result.회사연락처 = 연락처;

  const 주소 = extract회사주소(t);
  if (주소) result.회사주소 = 주소;

  const 날짜 = extract작성날짜(t);
  if (날짜) result.작성날짜 = 날짜;

  const 내용 = extract주요내용(t);
  if (내용) result.주요내용 = 내용;

  return result;
}

export default function OcrPage() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [activeSidebarSection, setActiveSidebarSection] = useState<'notice' | 'news' | null>(null);
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);
  const [template, setTemplate] = useState<TemplateState>(initialTemplate);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isPdfFile, setIsPdfFile] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isOcrRunning, setIsOcrRunning] = useState(false);
  const [isLlmCorrecting, setIsLlmCorrecting] = useState(false);
  const [ocrError, setOcrError] = useState<string | null>(null);
  const [ocrResult, setOcrResult] = useState<{
    full_text: string;
    items: { text: string; confidence: number }[];
    used_llm?: boolean;
    corrections?: { original: string; corrected: string }[];
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { isLoggedIn, userInfo, logout } = useAuthStore();

  const handleFileSelect = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    const ext = file.name.toLowerCase().split('.').pop();
    if (!['png', 'jpg', 'jpeg', 'pdf'].includes(ext || '')) {
      setOcrError('PNG, JPG 이미지 또는 PDF 파일만 업로드할 수 있습니다.');
      return;
    }
    setOcrError(null);
    setOcrResult(null);
    setImageFile(file);
    const isPdf = ext === 'pdf';
    setIsPdfFile(isPdf);
    if (!isPdf) {
      const reader = new FileReader();
      reader.onload = (e) => setImagePreview((e.target?.result as string) ?? null);
      reader.readAsDataURL(file);
    } else {
      // PDF는 썸네일 대신 파일명만 표시
      setImagePreview(null);
    }
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

  const removeImage = () => {
    setImageFile(null);
    setImagePreview(null);
    setIsPdfFile(false);
    setOcrResult(null);
    setOcrError(null);
    setIsLlmCorrecting(false);
  };

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

  const handleRunOcr = async () => {
    if (!imageFile) {
      setOcrError('이미지 또는 PDF를 먼저 업로드해 주세요.');
      return;
    }
    setOcrError(null);
    setOcrResult(null);
    setIsOcrRunning(true);
    setIsLlmCorrecting(false);
    const formData = new FormData();
    formData.append('file', imageFile);
    const apiBaseUrlResolved = apiBaseUrl;

    try {
      // 1) 먼저 OCR만 실행해 결과를 빠르게 표시 (use_llm=false)
      const resQuick = await fetch(`${apiBaseUrlResolved}/api/v1/ocr/with-llm?use_llm=false`, {
        method: 'POST',
        body: formData,
      });
      const dataQuick = await resQuick.json().catch(() => ({}));
      if (!resQuick.ok) {
        setOcrError(dataQuick.detail ?? dataQuick.error ?? `OCR 실패 (${resQuick.status})`);
        return;
      }
      const rawFullText = dataQuick.raw_full_text ?? '';
      const items = dataQuick.raw_items ?? [];
      setOcrResult({
        full_text: rawFullText,
        items,
        used_llm: false,
      });
      const parsed = parseOcrToTemplate(rawFullText);
      setTemplate((prev) => {
        const next = { ...prev };
        (Object.keys(parsed) as (keyof TemplateState)[]).forEach((key) => {
          const v = parsed[key];
          if (v != null && v.trim() !== '') next[key] = v.trim();
        });
        return next;
      });
    } catch (e) {
      setOcrError(e instanceof Error ? e.message : 'OCR 요청 중 오류가 발생했습니다.');
      return;
    } finally {
      setIsOcrRunning(false);
    }

    // 2) 백그라운드에서 Exaone 보정 요청 (use_llm=true)
    setIsLlmCorrecting(true);
    const formDataLlm = new FormData();
    formDataLlm.append('file', imageFile);
    try {
      const resLlm = await fetch(`${apiBaseUrlResolved}/api/v1/ocr/with-llm?use_llm=true`, {
        method: 'POST',
        body: formDataLlm,
      });
      const dataLlm = await resLlm.json().catch(() => ({}));
      if (!resLlm.ok) {
        return; // 보정 실패해도 이미 OCR 결과는 보여줌
      }
      const correctedText = dataLlm.corrected_text ?? dataLlm.raw_full_text ?? '';
      const usedLlm = dataLlm.used_llm === true;
      const fields = (dataLlm.fields as Record<string, string>) ?? {};
      const corrections = (dataLlm.corrections as { original: string; corrected: string }[]) ?? [];
      setOcrResult((prev) =>
        prev
          ? {
              ...prev,
              full_text: correctedText,
              used_llm: usedLlm,
              corrections: corrections.length > 0 ? corrections : undefined,
            }
          : null
      );
      // 템플릿 채우기: API에서 내려준 fields가 있으면 우선 사용, 없으면 OCR 텍스트 파싱
      setTemplate((prev) => {
        const next = { ...prev };
        const fieldKeys = TEMPLATE_FIELDS.map((f) => f.key);
        const hasApiFields =
          usedLlm &&
          Object.keys(fields).some((k) => {
            const field = fields[k];
            return fieldKeys.includes(k as keyof TemplateState) && field?.value && String(field.value).trim() !== '';
          });
        if (hasApiFields) {
          fieldKeys.forEach((key) => {
            const field = fields[key];
            const v = field?.value;
            if (v != null && String(v).trim() !== '') next[key] = String(v).trim();
          });
        } else {
          const parsed = parseOcrToTemplate(correctedText);
          (Object.keys(parsed) as (keyof TemplateState)[]).forEach((key) => {
            const v = parsed[key];
            if (v != null && v.trim() !== '') next[key] = v.trim();
          });
        }
        return next;
      });
    } finally {
      setIsLlmCorrecting(false);
    }
  };

  const updateTemplate = (key: (typeof TEMPLATE_FIELDS)[number]['key'], value: string) => {
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
            <ScanText className="w-6 h-6 text-[#003478]" />
            <div className="flex flex-col">
              <h1 className="text-xl font-bold text-[#003478]">글자 인식 OCR</h1>
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
        {/* 템플릿 */}
        <div className="bg-white/90 backdrop-blur-sm rounded-xl border border-gray-200 shadow-sm p-6 mb-8">
          <h2 className="text-lg font-semibold text-[#003478] mb-4">작성 템플릿</h2>
          <div className="space-y-4">
            {TEMPLATE_FIELDS.map(({ key, label }) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                {key === '주요내용' ? (
                  <textarea
                    value={template[key]}
                    onChange={(e) => updateTemplate(key, e.target.value)}
                    placeholder={`${label}을(를) 입력하세요`}
                    rows={4}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#003478] focus:border-transparent"
                  />
                ) : (
                  <input
                    type="text"
                    value={template[key]}
                    onChange={(e) => updateTemplate(key, e.target.value)}
                    placeholder={`${label}을(를) 입력하세요`}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#003478] focus:border-transparent"
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 이미지 업로드 + OCR */}
        <div className="bg-white/90 backdrop-blur-sm rounded-xl border border-gray-200 shadow-sm p-6">
          <h2 className="text-lg font-semibold text-[#003478] mb-4">이미지/PDF에서 글자 인식</h2>
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragging ? 'border-[#003478] bg-blue-50' : 'border-gray-300 bg-gray-50/50'
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".png,.jpg,.jpeg,.pdf"
              onChange={handleFileInputChange}
              className="hidden"
              id="ocr-file"
            />
            {!imagePreview && (!imageFile || isPdfFile === false) ? (
              <label htmlFor="ocr-file" className="cursor-pointer flex flex-col items-center">
                <Upload className="w-12 h-12 text-[#003478] mb-3" />
                <p className="text-gray-700 font-medium mb-1">이미지 또는 PDF를 드래그하거나 클릭하여 업로드</p>
                <p className="text-sm text-gray-500">PNG, JPG, PDF (글자가 보이는 문서/명함/서류 등)</p>
              </label>
            ) : imagePreview && !isPdfFile ? (
              <div className="relative inline-block">
                <img src={imagePreview} alt="업로드 미리보기" className="max-h-64 rounded-lg border border-gray-200" />
                <button
                  type="button"
                  onClick={removeImage}
                  className="absolute -top-2 -right-2 p-1.5 bg-red-500 text-white rounded-full hover:bg-red-600"
                  aria-label="이미지 제거"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              imageFile && isPdfFile && (
                <div className="relative inline-flex items-center justify-center px-4 py-3 bg-white border border-gray-200 rounded-lg">
                  <div className="flex items-center gap-3">
                    <Upload className="w-6 h-6 text-[#003478]" />
                    <div className="flex flex-col items-start">
                      <span className="text-sm font-medium text-gray-800">{imageFile.name}</span>
                      <span className="text-xs text-gray-500">PDF 파일 (첫 페이지 기준으로 인식합니다)</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={removeImage}
                    className="absolute -top-2 -right-2 p-1.5 bg-red-500 text-white rounded-full hover:bg-red-600"
                    aria-label="파일 제거"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )
            )}
          </div>
          {imageFile && (
            <div className="mt-4 flex justify-center">
              <button
                type="button"
                onClick={handleRunOcr}
                disabled={isOcrRunning}
                className="px-6 py-3 bg-[#003478] text-white rounded-lg hover:bg-[#002a5c] disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center gap-2"
              >
                <ScanText className="w-5 h-5" />
                {isOcrRunning ? '인식 중...' : '글자 인식 실행'}
              </button>
            </div>
          )}

          {ocrError && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {ocrError}
            </div>
          )}
          {ocrResult && (
            <div className="mt-4 space-y-2">
              {isLlmCorrecting && (
                <div className="p-2 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-800 animate-pulse">
                  Exaone 보정 중... (완료되면 자동으로 갱신됩니다)
                </div>
              )}
              <div className="p-3 bg-[#003478]/10 border border-[#003478]/30 rounded-lg text-sm text-[#003478]">
                템플릿 칸에 자동으로 채웠습니다. 수정이 필요하면 위 템플릿에서 직접 편집하세요.
                {ocrResult.items.length > 0 && (
                  <span className="text-gray-600 ml-1">(총 {ocrResult.items.length}개 영역 인식)</span>
                )}
              </div>
              {ocrResult.used_llm && (
                <div className="p-2 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
                  Exaone 보정이 적용된 결과입니다.
                </div>
              )}
              {ocrResult.used_llm === false && (
                <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
                  Exaone이 적용되지 않았습니다. 서버에 Exaone 모델이 로드되어 있으면 보정 결과가 표시됩니다.
                </div>
              )}
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
