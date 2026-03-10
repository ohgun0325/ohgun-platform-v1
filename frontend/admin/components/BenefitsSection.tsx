import { Database, Zap, FileCheck } from 'lucide-react';

export default function BenefitsSection() {
  const benefits = [
    {
      icon: Database,
      title: '정확한 ESG 데이터',
      description: '신뢰할 수 있는 출처에서 수집한 최신 ESG 데이터를 제공하여 의사결정을 지원합니다',
      gradient: 'from-[#0D4ABB] to-[#00D4FF]',
      glow: 'rgba(13, 74, 187, 0.3)'
    },
    {
      icon: Zap,
      title: '빠른 자동 보고서',
      description: 'AI 기술을 활용하여 몇 분 안에 전문적인 ESG 보고서를 자동으로 생성합니다',
      gradient: 'from-[#E91E8C] to-[#8B5CF6]',
      glow: 'rgba(233, 30, 140, 0.3)'
    },
    {
      icon: FileCheck,
      title: '윤문·요약 등 AI 문서 지원',
      description: 'OHGUN이 문서의 품질을 향상시키고 핵심 내용을 명확하게 정리해드립니다',
      gradient: 'from-[#00D4FF] to-[#8B5CF6]',
      glow: 'rgba(0, 212, 255, 0.3)'
    }
  ];

  return (
    <section className="py-24 bg-gradient-to-b from-gray-50 to-white">
      <div className="max-w-[1440px] mx-auto px-8">
        {/* Section Title */}
        <div className="text-center mb-16">
          <h2 className="mb-4 text-[#1a2332]">AI 자동화의 장점</h2>
          <p className="text-gray-600">
            AIFIX만의 AI 기술로 ESG 업무의 효율을 극대화하세요
          </p>
        </div>

        {/* Benefits Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {benefits.map((benefit, index) => (
            <div
              key={index}
              className="relative group p-10 rounded-3xl bg-white hover:shadow-2xl transition-all duration-500"
              style={{
                border: '1px solid rgba(0,0,0,0.08)',
              }}
            >
              {/* Gradient Background on Hover */}
              <div 
                className="absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 -z-10"
                style={{
                  background: `linear-gradient(135deg, ${benefit.glow} 0%, transparent 100%)`
                }}
              />

              {/* Icon with Gradient */}
              <div className="mb-6 flex justify-center">
                <div 
                  className={`w-20 h-20 rounded-2xl bg-gradient-to-br ${benefit.gradient} flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300`}
                  style={{
                    boxShadow: `0 10px 30px ${benefit.glow}`
                  }}
                >
                  <benefit.icon className="w-10 h-10 text-white" />
                </div>
              </div>

              {/* Title */}
              <h3 className="mb-4 text-center text-[#1a2332]">
                {benefit.title}
              </h3>

              {/* Description */}
              <p className="text-center text-gray-600" style={{ fontSize: '16px' }}>
                {benefit.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
