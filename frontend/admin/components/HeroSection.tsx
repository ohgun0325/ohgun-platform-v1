'use client';

import { ArrowRight, Play, Sparkles } from 'lucide-react';
import { useState } from 'react';

interface HeroSectionProps {
  onStartDiagnosis: () => void;
  onWatchDemo: () => void;
}

export default function HeroSection({ onStartDiagnosis, onWatchDemo }: HeroSectionProps) {
  const [isVideoModalOpen, setIsVideoModalOpen] = useState(false);

  const handleWatchDemo = () => {
    setIsVideoModalOpen(true);
    onWatchDemo();
  };

  return (
    <>
      <section className="relative pt-[200px] pb-32 overflow-hidden">
        {/* Background Gradient */}
        <div 
          className="absolute inset-0 z-0"
          style={{
            background: 'linear-gradient(135deg, #0D4ABB 0%, #1a2332 50%, #8B5CF6 100%)',
            opacity: 0.05
          }}
        />
        
        {/* Animated Background Elements */}
        <div className="absolute inset-0 z-0 overflow-hidden">
          <div className="absolute top-20 left-10 w-64 h-64 rounded-full bg-[#00D4FF]/10 blur-3xl animate-pulse" />
          <div className="absolute bottom-20 right-10 w-96 h-96 rounded-full bg-[#E91E8C]/10 blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
          <div className="absolute top-1/2 left-1/2 w-80 h-80 rounded-full bg-[#8B5CF6]/10 blur-3xl animate-pulse" style={{ animationDelay: '2s' }} />
        </div>

        <div className="relative z-10 max-w-[1440px] mx-auto px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left Column: Content */}
            <div className="text-center lg:text-left">
              {/* 3D AI Visual Representation */}
              <div className="mb-8 flex justify-center lg:justify-start">
                <div className="relative">
                  <div className="w-32 h-32 rounded-3xl bg-gradient-to-br from-[#0D4ABB] to-[#00D4FF] flex items-center justify-center shadow-2xl" style={{ animation: 'float 3s ease-in-out infinite' }}>
                    <Sparkles className="w-16 h-16 text-white" />
                  </div>
                  {/* Orbiting Elements */}
                  <div className="absolute -top-4 -right-4 w-12 h-12 rounded-full bg-gradient-to-br from-[#E91E8C] to-[#8B5CF6] animate-pulse" />
                  <div className="absolute -bottom-4 -left-4 w-16 h-16 rounded-full bg-gradient-to-br from-[#00D4FF] to-[#0D4ABB] opacity-50 blur-sm" />
                </div>
              </div>

              {/* H1 Headline */}
              <h1 className="mb-6 text-3xl lg:text-5xl font-bold bg-gradient-to-r from-[#0D4ABB] via-[#E91E8C] to-[#8B5CF6] bg-clip-text text-transparent leading-normal" style={{ fontFamily: 'Inter Tight, Arial, sans-serif' }}>
                AIFIX로 ESG 진단부터  <br className="hidden lg:block" />
                보고서, 공급망까지 한 번에
              </h1>

              {/* H2 Subheadline */}
              <h2 className="mb-8 text-xl lg:text-2xl font-semibold text-gray-700 leading-relaxed">
                중소기업은 자가진단·자동 보고서·개선 가이드를 한 플랫폼에서.<br />
                대기업은 협력사 ESG 현황을 정확하고 투명하게 모니터링합니다.
              </h2>

              {/* CTA Buttons */}
              <div className="flex items-center justify-center lg:justify-start gap-4 flex-wrap">
                <button
                  onClick={onStartDiagnosis}
                  className="group px-8 py-4 rounded-2xl bg-[#0D4ABB] text-white hover:shadow-xl hover:scale-105 transition-all flex items-center gap-2 font-semibold"
                >
                  무료 ESG 진단 시작
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </button>
                <button
                  onClick={handleWatchDemo}
                  className="px-8 py-4 rounded-2xl bg-gradient-to-r from-[#E91E8C] to-[#8B5CF6] text-white hover:shadow-xl hover:scale-105 transition-all font-semibold"
                >
                  데모 영상 보기
                </button>
              </div>
            </div>

            {/* Right Column: Demo Video Placeholder */}
            <div className="relative">
              <div 
                className="relative w-full aspect-video rounded-2xl overflow-hidden shadow-2xl bg-gradient-to-br from-[#0D4ABB]/20 via-[#E91E8C]/20 to-[#8B5CF6]/20 border border-gray-200/50 cursor-pointer"
                onClick={handleWatchDemo}
              >
                {/* Video Placeholder Background */}
                <div className="absolute inset-0 bg-gradient-to-br from-[#0D4ABB]/10 to-[#8B5CF6]/10" />
                
                {/* Animated Background Pattern */}
                <div className="absolute inset-0 opacity-30">
                  <div className="absolute top-1/4 left-1/4 w-32 h-32 rounded-full bg-[#00D4FF]/20 blur-2xl animate-pulse" />
                  <div className="absolute bottom-1/4 right-1/4 w-40 h-40 rounded-full bg-[#E91E8C]/20 blur-2xl animate-pulse" style={{ animationDelay: '1s' }} />
                </div>

                {/* Play Button Overlay */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="relative">
                    <div className="w-20 h-20 rounded-full bg-white/90 backdrop-blur-sm flex items-center justify-center shadow-xl hover:scale-110 transition-transform group">
                      <Play className="w-10 h-10 text-[#0D4ABB] ml-1 group-hover:text-[#E91E8C] transition-colors" fill="currentColor" />
                    </div>
                    {/* Ripple Effect */}
                    <div className="absolute inset-0 w-20 h-20 rounded-full bg-white/30 animate-ping" style={{ animationDuration: '2s' }} />
                  </div>
                </div>

                {/* Corner Decoration */}
                <div className="absolute top-4 right-4 w-16 h-16 rounded-full bg-gradient-to-br from-[#E91E8C] to-[#8B5CF6] opacity-20 blur-xl" />
                <div className="absolute bottom-4 left-4 w-20 h-20 rounded-full bg-gradient-to-br from-[#00D4FF] to-[#0D4ABB] opacity-20 blur-xl" />
              </div>

              {/* Video Label */}
              <div className="mt-4 text-center">
                <p className="text-sm text-gray-600 font-medium">서비스 데모 영상 (30~45초)</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Video Modal */}
      {isVideoModalOpen && (
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={() => setIsVideoModalOpen(false)}
        >
          <div 
            className="relative w-full max-w-4xl mx-4 aspect-video bg-black rounded-2xl overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Video placeholder - 실제 영상 URL로 교체 필요 */}
            <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-[#0D4ABB]/20 to-[#8B5CF6]/20">
              <p className="text-white text-lg">데모 영상이 여기에 표시됩니다</p>
            </div>
            <button
              onClick={() => setIsVideoModalOpen(false)}
              className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center text-white hover:bg-white/30 transition-colors"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </>
  );
}
