import { X } from 'lucide-react';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
  onKakaoLogin?: () => void;
  onNaverLogin?: () => void;
}

export default function LoginModal({ isOpen, onClose, onKakaoLogin, onNaverLogin }: LoginModalProps) {
  if (!isOpen) return null;

  const handleKakaoLogin = () => {
    // TODO: 카카오 로그인 API 연동
    if (onKakaoLogin) {
      onKakaoLogin();
    } else {
      console.log('카카오 로그인');
      // 카카오 로그인 로직 구현
    }
  };

  const handleNaverLogin = () => {
    // TODO: 네이버 로그인 API 연동
    if (onNaverLogin) {
      onNaverLogin();
    } else {
      console.log('네이버 로그인');
      // 네이버 로그인 로직 구현
      // 예: window.location.href = '/oauth/naver/login-url';
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative w-full max-w-md mx-4 p-8 rounded-3xl bg-white shadow-2xl animate-in fade-in zoom-in duration-300">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 rounded-full hover:bg-gray-100 transition-colors"
          aria-label="닫기"
        >
          <X className="w-5 h-5 text-gray-500" />
        </button>

        {/* Title */}
        <h3 className="mb-2 text-2xl font-bold text-center text-[#1a2332]">
          로그인
        </h3>

        {/* Description */}
        <p className="mb-8 text-center text-gray-600 text-sm">
          소셜 계정으로 간편하게 로그인하세요
        </p>

        {/* Social Login Buttons */}
        <div className="flex flex-col gap-3">
          {/* 카카오톡 로그인 (노란색) */}
          <button
            onClick={handleKakaoLogin}
            className="w-full px-6 py-4 rounded-xl bg-[#FEE500] text-[#000000] hover:bg-[#FDD835] hover:shadow-lg transition-all font-medium flex items-center justify-center gap-2"
          >
            <svg
              className="w-5 h-5"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M12 3C6.48 3 2 6.48 2 11c0 2.84 1.55 5.36 4 6.72V21l3.5-1.92c.5.08 1 .12 1.5.12 5.52 0 10-3.48 10-8s-4.48-8-10-8z"/>
            </svg>
            카카오톡 로그인
          </button>

          {/* 네이버 로그인 (초록색) */}
          <button
            onClick={handleNaverLogin}
            className="w-full px-6 py-4 rounded-xl bg-[#03C75A] text-white hover:bg-[#02B350] hover:shadow-lg transition-all font-medium flex items-center justify-center gap-2"
          >
            <svg
              className="w-5 h-5"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M16.273 12.845L7.376 0H0v24h7.726V11.156L16.624 24H24V0h-7.727v12.845z"/>
            </svg>
            네이버 로그인
          </button>
        </div>
      </div>
    </div>
  );
}
