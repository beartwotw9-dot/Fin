import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        surface2: "var(--surface2)",
        border: "var(--border)",
        accent: "var(--accent)",
        accent2: "var(--accent2)",
        up: "var(--up)",
        down: "var(--down)",
        text: "var(--text)",
        muted: "var(--muted)"
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        sans: ["ui-sans-serif", "system-ui", "Inter", "sans-serif"]
      }
    }
  },
  plugins: [require("tailwindcss-animate")]
};

export default config;
