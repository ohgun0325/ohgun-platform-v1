import { Sparkles } from 'lucide-react';
import Link from 'next/link';

interface HeaderProps {
  onLoginClick: () => void;
}

export default function Header({ onLoginClick }: HeaderProps) {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-[72px] backdrop-blur-[20px] bg-white/85 border-b border-gray-200/50">
      <div className="max-w-[1440px] mx-auto px-8 h-full flex items-center justify-between gap-4">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 flex-shrink-0 hover:opacity-80 transition-opacity">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#0D4ABB] to-[#00D4FF] flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-6 h-6 text-white" />
          </div>
          <span className="text-2xl font-bold text-[#1a2332] whitespace-nowrap" style={{ fontFamily: 'Inter Tight, Arial, sans-serif' }}>
            AIFIX
          </span>
        </Link>

        {/* Right Section - Login Button */}
        <div className="flex items-center gap-4 flex-shrink-0 ml-auto">
          <button
            onClick={onLoginClick}
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-[#E91E8C] to-[#8B5CF6] text-white hover:shadow-lg hover:scale-105 transition-all whitespace-nowrap"
          >
            로그인
          </button>
        </div>
      </div>
    </header>
  );
}