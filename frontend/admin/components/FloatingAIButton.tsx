import { Sparkles } from 'lucide-react';
import { useState } from 'react';
import OHGUNPanel from './OHGUNPanel';

export default function FloatingAIButton() {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <>
      {/* Collapsed Button */}
      <div className="fixed top-24 right-8 z-50">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className={`relative px-6 py-3 rounded-full bg-gradient-to-r from-[#00D4FF] to-[#0D4ABB] flex items-center gap-2 shadow-2xl hover:scale-105 transition-all duration-300 ${
            isExpanded ? 'opacity-0 pointer-events-none' : 'opacity-100'
          }`}
          style={{
            boxShadow: '0 4px 20px rgba(0, 212, 255, 0.4)'
          }}
          aria-label="OHGUN Assistant"
        >
          <Sparkles className="w-5 h-5 text-white" />
          <span className="text-white font-semibold text-sm whitespace-nowrap">OHGUN Assistant</span>
        </button>
      </div>

      {/* Expanded Panel */}
      <OHGUNPanel isOpen={isExpanded} onClose={() => setIsExpanded(false)} />
    </>
  );
}