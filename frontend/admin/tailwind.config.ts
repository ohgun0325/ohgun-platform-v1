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
        "integrity-blue": "#0D4ABB",
        "excellence-navy": "#1a2332",
        "courage-pink": "#E91E8C",
        "agility-cyan": "#00D4FF",
        "collaboration-purple": "#8B5CF6",
      },
      backgroundImage: {
        "gradient-hero": "linear-gradient(135deg, #0D4ABB 0%, #1a2332 50%, #8B5CF6 100%)",
        "gradient-cyan": "linear-gradient(135deg, #00D4FF 0%, #0D4ABB 100%)",
        "gradient-pink": "linear-gradient(135deg, #E91E8C 0%, #8B5CF6 100%)",
      },
    },
  },
  plugins: [],
};

export default config;

