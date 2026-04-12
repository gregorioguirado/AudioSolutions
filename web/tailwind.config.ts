import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0a0a",
        surface: "#111111",
        border: "#2a2a2a",
        accent: "#ffde00",
        success: "#34c759",
        warning: "#ffcc00",
        error: "#ff6b6b",
        muted: "#888888",
      },
      fontFamily: {
        mono: [
          "var(--font-jetbrains)",
          "JetBrains Mono",
          "SF Mono",
          "Menlo",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
