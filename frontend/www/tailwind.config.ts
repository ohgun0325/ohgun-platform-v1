import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // 브랜드 컬러 (기존)
        "integrity-blue": "#0D4ABB",
        "excellence-navy": "#1a2332",
        "courage-pink": "#E91E8C",
        "agility-cyan": "#00D4FF",
        "collaboration-purple": "#8B5CF6",

        // Material Design 스타일 시스템 컬러
        primary: "#0D4ABB",
        "primary-container": "#D3E3FD",
        secondary: "#5C6BC0",
        "secondary-container": "#E8EAF6",
        background: "#FDFBFF",
        surface: "#FFFFFF",
        "surface-variant": "#E7E0EC",
        "on-primary": "#FFFFFF",
        "on-secondary": "#FFFFFF",
        "on-background": "#1A1B1F",
        "on-surface": "#1A1B1F",
        "on-surface-variant": "#49454F",
        outline: "#79747E",
        error: "#B3261E",
        "on-error": "#FFFFFF",
      },
      backgroundImage: {
        "gradient-hero": "linear-gradient(135deg, #0D4ABB 0%, #1a2332 50%, #8B5CF6 100%)",
        "gradient-cyan": "linear-gradient(135deg, #00D4FF 0%, #0D4ABB 100%)",
        "gradient-pink": "linear-gradient(135deg, #E91E8C 0%, #8B5CF6 100%)",
      },
      boxShadow: {
        "md-elevation-1":
          "0px 1px 3px rgba(0,0,0,0.12), 0px 1px 2px rgba(0,0,0,0.24)",
        "md-elevation-2":
          "0px 3px 6px rgba(0,0,0,0.16), 0px 3px 6px rgba(0,0,0,0.23)",
        "md-elevation-3":
          "0px 10px 20px rgba(0,0,0,0.19), 0px 6px 6px rgba(0,0,0,0.23)",
      },
      borderRadius: {
        "md-full": "9999px",
        "md-lg": "16px",
      },
    },
  },
  plugins: [],
};

export default config;

