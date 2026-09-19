import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        paper: "#F5F4F0",
        "paper-alt": "#EDEAE0",
        "paper-deep": "#E4E0D2",
        ink: "#1E2321",
        "ink-soft": "#565F58",
        "ink-faint": "#666B63",
        line: "#D8D3C4",
        "line-strong": "#BFB9A6",
        highlight: "#E4A93A",
        "highlight-ink": "#5C3E0C",
        "highlight-soft": "#F6E1B4",
        "risk-high": "#AE3A2C",
        "risk-high-bg": "#F3DAD4",
        "risk-med": "#8D5B15",
        "risk-med-bg": "#F3E4C7",
        "risk-low": "#3E6E52",
        "risk-low-bg": "#DCE7DE",
      },
      fontFamily: {
        serif: ["var(--font-fraunces)", "serif"],
        sans: ["var(--font-plex-sans)", "sans-serif"],
        mono: ["var(--font-plex-mono)", "monospace"],
      },
      boxShadow: {
        paper: "0 8px 24px rgba(30,35,33,0.10)",
      },
    },
  },
  plugins: [],
};
export default config;
