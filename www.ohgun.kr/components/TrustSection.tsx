import { CheckCircle2, Shield, Users, TrendingUp } from 'lucide-react';

export default function TrustSection() {
  const trustPoints = [
    {
      icon: TrendingUp,
      title: 'ESG 규제 최신 기준 자동 업데이트',
      description: '국내외 ESG 규제 변화를 실시간으로 반영하여 항상 최신 기준으로 대응할 수 있습니다',
      color: 'from-[#0D4ABB] to-[#00D4FF]',
      bgColor: 'bg-[#0D4ABB]/5'
    },
    {
      icon: Shield,
      title: '데이터 수정 권한 분리',
      description: '데이터 입력과 수정 권한을 분리하여 신뢰성과 투명성을 확보합니다',
      color: 'from-[#E91E8C] to-[#8B5CF6]',
      bgColor: 'bg-[#E91E8C]/5'
    },
    {
      icon: Users,
      title: '국내 SME·기관 베타 테스트 진행',
      description: '실제 기업과 기관에서 검증된 솔루션으로 안정성과 효과를 입증했습니다',
      color: 'from-[#00D4FF] to-[#0D4ABB]',
      bgColor: 'bg-[#00D4FF]/5'
    }
  ];

  return (
    <section className="py-24 bg-gradient-to-b from-white to-gray-50">
      <div className="max-w-[1440px] mx-auto px-8">
        {/* Section Title */}
        <div className="text-center mb-16">
          <h2 className="mb-4 text-3xl lg:text-4xl font-bold text-[#1a2332]" style={{ fontFamily: 'Inter Tight, Arial, sans-serif' }}>
            신뢰할 수 있는 AIFix
          </h2>
          <p className="text-gray-600 text-lg">
            검증된 기술과 투명한 프로세스로 신뢰를 구축합니다
          </p>
        </div>

        {/* Trust Points Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {trustPoints.map((point, index) => (
            <div
              key={index}
              className="group relative p-8 rounded-2xl bg-white border border-gray-200 hover:border-transparent hover:shadow-2xl transition-all duration-300"
              style={{
                boxShadow: '0 4px 20px rgba(0,0,0,0.03)'
              }}
            >
              {/* Icon */}
              <div className={`w-16 h-16 rounded-xl bg-gradient-to-br ${point.color} flex items-center justify-center mb-6 group-hover:scale-110 transition-transform`}>
                <point.icon className="w-8 h-8 text-white" />
              </div>

              {/* Title */}
              <h3 className="mb-4 text-xl font-bold text-[#1a2332]">
                {point.title}
              </h3>

              {/* Description */}
              <p className="text-gray-600" style={{ fontSize: '16px' }}>
                {point.description}
              </p>

              {/* Check Icon */}
              <div className="mt-6 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                <span className="text-sm text-gray-500 font-medium">검증 완료</span>
              </div>

              {/* Hover Effect Background */}
              <div className={`absolute inset-0 rounded-2xl ${point.bgColor} opacity-0 group-hover:opacity-100 transition-opacity -z-10`} />
            </div>
          ))}
        </div>

        {/* Verification Badge */}
        <div className="mt-16 text-center">
          <div className="inline-flex items-center gap-3 px-6 py-4 rounded-2xl bg-gradient-to-r from-[#0D4ABB]/10 to-[#00D4FF]/10 border border-[#0D4ABB]/20">
            <Shield className="w-6 h-6 text-[#0D4ABB]" />
            <span className="text-[#1a2332] font-semibold">
              국내 ESG 솔루션 검증 기업
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

