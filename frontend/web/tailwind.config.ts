import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        "console-accent": "#22d3ee",
        "console-violet": "#a78bfa",
        "console-emerald": "#34d399",
        "console-red": "#f87171",
        "console-amber": "#fbbf24",
      },
      boxShadow: {
        panel: "0 0 0 1px rgb(39 39 42 / 0.6), 0 4px 24px rgb(0 0 0 / 0.3)",
        "glow-cyan": "0 0 20px rgba(34, 211, 238, 0.25), 0 0 40px rgba(34, 211, 238, 0.1)",
        "glow-emerald": "0 0 20px rgba(52, 211, 153, 0.25), 0 0 40px rgba(52, 211, 153, 0.1)",
        "glow-red": "0 0 20px rgba(248, 113, 113, 0.25), 0 0 40px rgba(248, 113, 113, 0.1)",
        "glow-violet": "0 0 20px rgba(167, 139, 250, 0.25), 0 0 40px rgba(167, 139, 250, 0.1)",
        "glow-amber": "0 0 20px rgba(251, 191, 36, 0.25), 0 0 40px rgba(251, 191, 36, 0.1)",
        "inner-glow": "inset 0 1px 0 rgba(255,255,255,0.05)",
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-panel": "linear-gradient(135deg, rgba(39,39,42,0.8) 0%, rgba(24,24,27,0.95) 100%)",
        "gradient-cyan": "linear-gradient(135deg, #22d3ee 0%, #0891b2 100%)",
        "gradient-violet": "linear-gradient(135deg, #a78bfa 0%, #7c3aed 100%)",
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "glow-pulse": "glow-pulse 2s ease-in-out infinite",
        "fade-in": "fade-in 0.3s ease-out",
        "slide-up": "slide-up 0.3s ease-out",
      },
      keyframes: {
        "glow-pulse": {
          "0%, 100%": { opacity: "1", boxShadow: "0 0 8px rgba(34,211,238,0.6)" },
          "50%": { opacity: "0.7", boxShadow: "0 0 16px rgba(34,211,238,0.9)" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
