import { BarChart3, FileText, ClipboardCheck, Wand2 } from 'lucide-react';

export default function FeatureSection() {
  const features = [
    {
      icon: BarChart3,
      title: 'ESG 등급 조회',
      description: '국내외 주요 기업의 ESG 등급을 실시간으로 확인하고 비교 분석할 수 있습니다',
      color: 'from-[#0D4ABB] to-[#00D4FF]',
      bgColor: 'bg-[#0D4ABB]/5'
    },
    {
      icon: FileText,
      title: '자동 보고서 생성',
      description: 'AI가 ESG 데이터를 분석하여 전문적인 보고서를 자동으로 생성합니다',
      color: 'from-[#E91E8C] to-[#8B5CF6]',
      bgColor: 'bg-[#E91E8C]/5'
    },
    {
      icon: ClipboardCheck,
      title: '자가진단',
      description: '기업의 ESG 수준을 자가 진단하고 개선 방향을 제시받을 수 있습니다',
      color: 'from-[#00D4FF] to-[#0D4ABB]',
      bgColor: 'bg-[#00D4FF]/5'
    },
    {
      icon: Wand2,
      title: '윤문 AI (OHGUN)',
      description: 'OHGUN Assistant가 문서를 다듬고 요약하여 완성도를 높여드립니다',
      color: 'from-[#8B5CF6] to-[#E91E8C]',
      bgColor: 'bg-[#8B5CF6]/5'
    }
  ];

  return (
    <section className="py-24 bg-white">
      <div className="max-w-[1440px] mx-auto px-8">
        {/* Section Title */}
        <div className="text-center mb-16">
          <h2 className="mb-4 text-[#1a2332]">AIFIX 핵심 기능</h2>
          <p className="text-gray-600">
            AI 기술로 ESG 경영을 더 쉽고 효율적으로 만듭니다
          </p>
        </div>

        {/* Feature Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature, index) => (
            <div
              key={index}
              className="group p-8 rounded-2xl bg-white border border-gray-200 hover:border-transparent hover:shadow-2xl transition-all duration-300"
              style={{
                boxShadow: '0 4px 20px rgba(0,0,0,0.03)'
              }}
            >
              {/* Icon */}
              <div className={`w-16 h-16 rounded-xl bg-gradient-to-br ${feature.color} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}>
                <feature.icon className="w-8 h-8 text-white" />
              </div>

              {/* Title */}
              <h3 className="mb-3 text-[#1a2332]">
                {feature.title}
              </h3>

              {/* Description */}
              <p className="text-gray-600" style={{ fontSize: '16px' }}>
                {feature.description}
              </p>

              {/* Hover Effect Background */}
              <div className={`absolute inset-0 rounded-2xl ${feature.bgColor} opacity-0 group-hover:opacity-100 transition-opacity -z-10`} />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
