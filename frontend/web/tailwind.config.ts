import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        "console-accent": "#22d3ee",
      },
      boxShadow: {
        panel: "0 0 0 1px rgb(39 39 42 / 0.5)",
      },
    },
  },
  plugins: [],
};

export default config;
