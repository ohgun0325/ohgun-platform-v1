'use client';

import { X, ChevronDown, ChevronRight } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  activeSection: 'notice' | 'news' | null;
  onSectionChange: (section: 'notice' | 'news' | null) => void;
}

// 공지사항 샘플 데이터
const notices = [
  { id: 1, title: '2024년 KOICA 사업 안내', date: '2024-01-15' },
  { id: 2, title: '신규 프로젝트 지원 모집 공고', date: '2024-01-10' },
  { id: 3, title: '시스템 점검 안내', date: '2024-01-05' },
  { id: 4, title: '연말연시 휴무 안내', date: '2023-12-20' },
  { id: 5, title: '2024년도 예산 배정 공지', date: '2023-12-15' },
];

// 뉴스룸 샘플 데이터
const news = [
  { id: 1, title: 'KOICA, 아프리카 개발협력 프로젝트 성과 발표', date: '2024-01-20' },
  { id: 2, title: '한-아세안 협력사업 확대 협약 체결', date: '2024-01-18' },
  { id: 3, title: '글로벌 보건의료 지원 프로그램 시작', date: '2024-01-12' },
  { id: 4, title: '교육 인프라 구축 사업 완료 보고', date: '2024-01-08' },
  { id: 5, title: '기후변화 대응 프로젝트 성과 공유회 개최', date: '2024-01-03' },
];

export default function Sidebar({ isOpen, onClose, activeSection, onSectionChange }: SidebarProps) {
  const router = useRouter();
  const [isAIServiceOpen, setIsAIServiceOpen] = useState(true);

  const handleSectionClick = (section: 'notice' | 'news') => {
    if (activeSection === section) {
      onSectionChange(null);
    } else {
      onSectionChange(section);
    }
  };

  const handleAIServiceToggle = () => {
    setIsAIServiceOpen(!isAIServiceOpen);
  };

  const handleAIServiceItemClick = (path: string) => {
    onClose();
    router.push(path);
  };

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div
        className={`fixed top-0 left-0 h-full w-80 bg-white shadow-2xl z-50 transform transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h2 className="text-lg font-bold text-[#003478]">메뉴</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            aria-label="닫기"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>

        {/* Menu Items */}
        <div className="p-4 space-y-2">
          {/* 대시보드 버튼 */}
          <button
            onClick={() => {
              onClose();
              router.push('/dashboard');
            }}
            className="w-full text-left px-4 py-3 rounded-lg transition-colors bg-gray-50 text-gray-700 hover:bg-gray-100 flex items-center gap-2"
          >
            <svg
              className="w-5 h-5 text-[#003478]"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
              />
            </svg>
            <span className="font-medium">대시보드</span>
          </button>

          {/* AI 서비스 카테고리 */}
          <div>
            <button
              onClick={handleAIServiceToggle}
              className="w-full text-left px-4 py-3 rounded-lg transition-colors bg-[#003478] text-white hover:bg-[#002a5c] flex items-center justify-between"
            >
              <span className="font-medium">AI 서비스</span>
              {isAIServiceOpen ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>

            {/* AI 서비스 하위 메뉴 */}
            {isAIServiceOpen && (
              <div className="mt-2 ml-4 space-y-1">
                <button
                  onClick={() => handleAIServiceItemClick('/chat')}
                  className="w-full text-left px-4 py-2 rounded-lg transition-colors bg-gray-50 text-gray-700 hover:bg-gray-100 text-sm"
                >
                  대화형 업무지원 AI
                </button>
                <button
                  onClick={() => handleAIServiceItemClick('/report')}
                  className="w-full text-left px-4 py-2 rounded-lg transition-colors bg-gray-50 text-gray-700 hover:bg-gray-100 text-sm"
                >
                  보고서 생성 AI
                </button>
                <button
                  onClick={() => handleAIServiceItemClick('/terms')}
                  className="w-full text-left px-4 py-2 rounded-lg transition-colors bg-gray-50 text-gray-700 hover:bg-gray-100 text-sm"
                >
                  ODA 용어사전 AI
                </button>
                <button
                  onClick={() => handleAIServiceItemClick('/bidding')}
                  className="w-full text-left px-4 py-2 rounded-lg transition-colors bg-gray-50 text-gray-700 hover:bg-gray-100 text-sm"
                >
                  입찰서류 관리 AI
                </button>
                <button
                  onClick={() => handleAIServiceItemClick('/evaluation')}
                  className="w-full text-left px-4 py-2 rounded-lg transition-colors bg-gray-50 text-gray-700 hover:bg-gray-100 text-sm"
                >
                  RfP 평가 시스템
                </button>
                <button
                  onClick={() => handleAIServiceItemClick('/ocr')}
                  className="w-full text-left px-4 py-2 rounded-lg transition-colors bg-gray-50 text-gray-700 hover:bg-gray-100 text-sm"
                >
                  글자 인식 OCR
                </button>
              </div>
            )}
          </div>

          {/* 공지사항 버튼 */}
          <button
            onClick={() => handleSectionClick('notice')}
            className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
              activeSection === 'notice'
                ? 'bg-[#003478] text-white'
                : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
            }`}
          >
            <span className="font-medium">공지사항</span>
          </button>

          {/* 뉴스룸 버튼 */}
          <button
            onClick={() => handleSectionClick('news')}
            className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
              activeSection === 'news'
                ? 'bg-[#003478] text-white'
                : 'bg-gray-50 text-gray-700 hover:bg-gray-100'
            }`}
          >
            <span className="font-medium">뉴스룸</span>
          </button>
        </div>

        {/* Content Area */}
        {activeSection && (
          <div className="border-t border-gray-200 p-4 overflow-y-auto" style={{ maxHeight: 'calc(100vh - 200px)' }}>
            <h3 className="text-md font-semibold text-[#003478] mb-4">
              {activeSection === 'notice' ? '공지사항' : '뉴스룸'}
            </h3>
            <div className="space-y-3">
              {(activeSection === 'notice' ? notices : news).map((item) => (
                <div
                  key={item.id}
                  className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer border border-gray-200"
                >
                  <p className="font-medium text-gray-800 mb-1">{item.title}</p>
                  <p className="text-xs text-gray-500">{item.date}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  );
}

