import { Play } from 'lucide-react';

export default function FeatureDemoSection() {
  const demos = [
    {
      title: 'K-ESG ↔ ESRS Lite 토글',
      description: '한 번의 입력으로 두 기준을 자동 매핑하여 대응합니다',
      type: 'gif',
      placeholder: 'K-ESG ↔ ESRS Lite 토글 UI 화면'
    },
    {
      title: 'GRI 보고서 자동 생성',
      description: '입력 데이터를 기반으로 전문적인 ESG 보고서를 자동 생성합니다',
      type: 'screenshot',
      placeholder: '보고서 자동 생성 과정'
    },
    {
      title: 'Enterprise Portal Heatmap',
      description: '협력사 ESG 현황을 한눈에 파악하고 리스크를 모니터링합니다',
      type: 'video',
      placeholder: 'Enterprise Portal Heatmap 화면 흐름'
    }
  ];

  return (
    <section className="py-24 bg-white">
      <div className="max-w-[1440px] mx-auto px-8">
        {/* Section Title */}
        <div className="text-center mb-16">
          <h2 className="mb-4 text-3xl lg:text-4xl font-bold text-[#1a2332]" style={{ fontFamily: 'Inter Tight, Arial, sans-serif' }}>
            핵심 기능 시연
          </h2>
          <p className="text-gray-600 text-lg">
            AIFix의 주요 기능을 직접 확인해보세요
          </p>
        </div>

        {/* Demo Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {demos.map((demo, index) => (
            <div
              key={index}
              className="group relative rounded-2xl overflow-hidden bg-gradient-to-br from-gray-50 to-white border border-gray-200 hover:shadow-2xl transition-all duration-300"
            >
              {/* Visual Placeholder */}
              <div className="relative w-full aspect-video bg-gradient-to-br from-[#0D4ABB]/10 via-[#E91E8C]/10 to-[#8B5CF6]/10">
                {/* Animated Background Pattern */}
                <div className="absolute inset-0 opacity-30">
                  <div className="absolute top-1/4 left-1/4 w-32 h-32 rounded-full bg-[#00D4FF]/20 blur-2xl animate-pulse" />
                  <div className="absolute bottom-1/4 right-1/4 w-40 h-40 rounded-full bg-[#E91E8C]/20 blur-2xl animate-pulse" style={{ animationDelay: '1s' }} />
                </div>

                {/* Play Button (for video type) */}
                {demo.type === 'video' && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-16 h-16 rounded-full bg-white/90 backdrop-blur-sm flex items-center justify-center shadow-xl group-hover:scale-110 transition-transform cursor-pointer">
                      <Play className="w-8 h-8 text-[#0D4ABB] ml-1" fill="currentColor" />
                    </div>
                  </div>
                )}

                {/* Placeholder Text */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <p className="text-gray-400 text-sm font-medium px-4 text-center">
                    {demo.placeholder}
                  </p>
                </div>
              </div>

              {/* Description */}
              <div className="p-6">
                <h3 className="mb-2 text-lg font-bold text-[#1a2332]">
                  {demo.title}
                </h3>
                <p className="text-gray-600" style={{ fontSize: '14px' }}>
                  {demo.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

