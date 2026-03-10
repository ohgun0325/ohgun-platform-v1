'use client';

import { X, Bot, Send, MessageSquare, History, FolderOpen } from 'lucide-react';
import { useState } from 'react';

interface OHGUNPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

type TabType = 'chat' | 'history' | 'library';

interface ChatHistory {
  id: string;
  title: string;
  date: string;
  preview: string;
}

interface Project {
  id: string;
  name: string;
  chatCount: number;
  lastActive: string;
}

export default function OHGUNPanel({ isOpen, onClose }: OHGUNPanelProps) {
  const [activeTab, setActiveTab] = useState<TabType>('chat');
  const [message, setMessage] = useState('');
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'assistant' | 'user'; content: string }>>([
    {
      role: 'assistant',
      content: '안녕하세요! OHGUN Assistant입니다. ESG 관련 질문이나 문서 윤문, 요약 등을 도와드립니다.'
    }
  ]);
  
  // 히스토리 데이터 (예시)
  const [chatHistory] = useState<ChatHistory[]>([
    { id: '1', title: 'ESG 보고서 작성 문의', date: '2025-01-15', preview: 'ESG 보고서 작성 방법에 대해 문의드립니다...' },
    { id: '2', title: '문서 윤문 요청', date: '2025-01-14', preview: '다음 문서의 윤문을 부탁드립니다...' },
    { id: '3', title: 'ESG 등급 확인', date: '2025-01-13', preview: '우리 회사의 ESG 등급을 확인하고 싶습니다...' },
  ]);

  // 라이브러리 프로젝트 데이터 (예시)
  const [projects] = useState<Project[]>([
    { id: '1', name: '2025 ESG 보고서', chatCount: 12, lastActive: '2025-01-15' },
    { id: '2', name: '지속가능경영 전략', chatCount: 8, lastActive: '2025-01-14' },
    { id: '3', name: '탄소중립 계획', chatCount: 5, lastActive: '2025-01-13' },
  ]);

  const handleSend = () => {
    if (!message.trim()) return;
    
    setChatMessages([...chatMessages, { role: 'user', content: message }]);
    setMessage('');
    
    // Simulate AI response
    setTimeout(() => {
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: '죄송합니다. 현재 데모 버전입니다. 실제 서비스에서는 AI가 답변을 제공합니다.'
      }]);
    }, 1000);
  };

  return (
    <>
      {/* Sidebar Panel */}
      <div
        className={`fixed top-0 right-0 h-screen z-50 w-[500px] transition-all duration-300 ${
          isOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="h-full flex flex-col shadow-2xl backdrop-blur-[20px] bg-white border-l border-gray-200/50">
        {/* Header */}
        <div className="p-6 bg-gradient-to-r from-[#00D4FF] to-[#0D4ABB] text-white">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                <Bot className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-semibold" style={{ fontSize: '18px' }}>
                  OHGUN Assistant
                </h3>
                <p className="text-white/80" style={{ fontSize: '12px' }}>
                  온라인
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-full hover:bg-white/20 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                activeTab === 'chat'
                  ? 'bg-white/20 text-white'
                  : 'text-white/70 hover:bg-white/10'
              }`}
            >
              <MessageSquare className="w-4 h-4" />
              <span style={{ fontSize: '14px' }}>채팅</span>
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                activeTab === 'history'
                  ? 'bg-white/20 text-white'
                  : 'text-white/70 hover:bg-white/10'
              }`}
            >
              <History className="w-4 h-4" />
              <span style={{ fontSize: '14px' }}>히스토리</span>
            </button>
            <button
              onClick={() => setActiveTab('library')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                activeTab === 'library'
                  ? 'bg-white/20 text-white'
                  : 'text-white/70 hover:bg-white/10'
              }`}
            >
              <FolderOpen className="w-4 h-4" />
              <span style={{ fontSize: '14px' }}>라이브러리</span>
            </button>
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {activeTab === 'chat' && (
            <>
              {/* Chat Body */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {chatMessages.map((msg, index) => (
                <div
                  key={index}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[80%] p-4 rounded-2xl ${
                      msg.role === 'user'
                        ? 'bg-gradient-to-r from-[#0D4ABB] to-[#00D4FF] text-white'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    <p style={{ fontSize: '14px', lineHeight: '1.5' }}>
                      {msg.content}
                    </p>
                  </div>
                </div>
              ))}
            </div>

              {/* Input Footer */}
              <div className="p-4 border-t border-gray-200/50 flex-shrink-0">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                  placeholder="메시지를 입력하세요..."
                  className="flex-1 px-4 py-3 rounded-xl border border-gray-300 focus:outline-none focus:border-[#0D4ABB] transition-colors"
                  style={{ fontSize: '14px' }}
                />
                <button
                  onClick={handleSend}
                  className="p-3 rounded-xl bg-gradient-to-r from-[#00D4FF] to-[#0D4ABB] text-white hover:shadow-lg hover:scale-105 transition-all"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </>
        )}

          {activeTab === 'history' && (
            <div className="flex-1 overflow-y-auto p-6">
            <div className="space-y-3">
              {chatHistory.length === 0 ? (
                <div className="text-center text-gray-400 py-12">
                  <History className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p style={{ fontSize: '14px' }}>대화 내역이 없습니다</p>
                </div>
              ) : (
                chatHistory.map((history) => (
                  <button
                    key={history.id}
                    className="w-full text-left p-4 rounded-xl border border-gray-200 hover:bg-gray-50 hover:border-[#0D4ABB] transition-all"
                    onClick={() => setActiveTab('chat')}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <h4 className="font-semibold text-gray-800" style={{ fontSize: '14px' }}>
                        {history.title}
                      </h4>
                      <span className="text-gray-400 text-xs">{history.date}</span>
                    </div>
                    <p className="text-gray-600 text-sm line-clamp-2">{history.preview}</p>
                  </button>
                ))
              )}
            </div>
          </div>
        )}

          {activeTab === 'library' && (
            <div className="flex-1 overflow-y-auto p-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="font-semibold text-gray-800" style={{ fontSize: '16px' }}>
                프로젝트
              </h4>
              <button
                className="px-4 py-2 rounded-lg bg-gradient-to-r from-[#00D4FF] to-[#0D4ABB] text-white text-sm hover:shadow-lg transition-all"
                onClick={() => {
                  // 새 프로젝트 생성 로직
                  const newProject: Project = {
                    id: String(projects.length + 1),
                    name: `새 프로젝트 ${projects.length + 1}`,
                    chatCount: 0,
                    lastActive: new Date().toISOString().split('T')[0]
                  };
                  // 실제로는 state 업데이트 필요
                }}
              >
                + 새 프로젝트
              </button>
            </div>
            <div className="space-y-3">
              {projects.length === 0 ? (
                <div className="text-center text-gray-400 py-12">
                  <FolderOpen className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p style={{ fontSize: '14px' }}>프로젝트가 없습니다</p>
                </div>
              ) : (
                projects.map((project) => (
                  <button
                    key={project.id}
                    className="w-full text-left p-4 rounded-xl border border-gray-200 hover:bg-gray-50 hover:border-[#0D4ABB] transition-all"
                    onClick={() => setActiveTab('chat')}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <FolderOpen className="w-5 h-5 text-[#0D4ABB]" />
                        <h4 className="font-semibold text-gray-800" style={{ fontSize: '14px' }}>
                          {project.name}
                        </h4>
                      </div>
                      <span className="text-gray-400 text-xs">{project.lastActive}</span>
                    </div>
                    <p className="text-gray-600 text-sm">
                      채팅 {project.chatCount}개
                    </p>
                  </button>
                ))
              )}
            </div>
          </div>
          )}
        </div>
        </div>
      </div>
    </>
  );
}
