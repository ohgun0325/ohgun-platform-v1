import { Link, FileText, Network } from 'lucide-react';

export default function PainSolutionSection() {
  const solutions = [
    {
      icon: Link,
      title: '입력 한 번, K-ESG/ESRS Lite 자동 매핑',
      description: '중복 입력 없이 두 기준 동시 대응 가능, 공시 대응 시간을 획기적으로 절감',
      iconColor: 'bg-[#0D4ABB]',
      cardBg: 'from-[#0D4ABB]/10 to-[#00D4FF]/10',
      borderColor: 'border-[#0D4ABB]/20'
    },
    {
      icon: FileText,
      title: 'GRI 기반 ESG 보고서 자동 생성',
      description: '보고서 작성 부담과 시간을 크게 줄이며, AI가 전문성을 높여줌',
      iconColor: 'bg-[#E91E8C]',
      cardBg: 'from-[#E91E8C]/10 to-[#8B5CF6]/10',
      borderColor: 'border-[#E91E8C]/20'
    },
    {
      icon: Network,
      title: 'Enterprise Portal로 전체 리스크 한눈에',
      description: '대기업이 협력사 ESG를 확인하기 어려웠던 문제 해결, 공급망 전체 리스크 실시간 파악',
      iconColor: 'bg-[#00D4FF]',
      cardBg: 'from-[#00D4FF]/10 to-[#0D4ABB]/10',
      borderColor: 'border-[#00D4FF]/20'
    }
  ];

  return (
    <section className="py-24 bg-white">
      <div className="max-w-[1440px] mx-auto px-8">
        {/* Section Title */}
        <div className="text-center mb-16">
          <h2 className="mb-4 text-[#1a2332]">ESG가 어렵고, 시간이 부족한 기업을 위해 설계했습니다.</h2>
          <p className="text-gray-600">
            AI 기술로 ESG 경영을 더 쉽고 효율적으로 만듭니다
          </p>
        </div>

        {/* Solutions Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {solutions.map((item, index) => (
            <div
              key={index}
              className={`group relative p-8 rounded-2xl bg-gradient-to-br ${item.cardBg} border-2 ${item.borderColor} hover:shadow-2xl transition-all duration-300`}
              style={{
                boxShadow: '0 4px 20px rgba(0,0,0,0.05)'
              }}
            >
              {/* Icon */}
              <div className={`w-16 h-16 rounded-xl ${item.iconColor} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform shadow-lg`}>
                <item.icon className="w-8 h-8 text-white" />
              </div>

              {/* Title */}
              <h3 className="mb-4 text-xl font-bold text-[#1a2332] leading-tight" style={{ fontFamily: 'Inter Tight, Arial, sans-serif' }}>
                {item.title}
              </h3>

              {/* Description - Benefit 중심 */}
              <p className="text-gray-600 leading-relaxed" style={{ fontSize: '16px' }}>
                {item.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

