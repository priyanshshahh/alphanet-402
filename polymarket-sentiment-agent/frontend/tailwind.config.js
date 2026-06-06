/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      colors: {
        ink: "#0b0e14",
        panel: "#11151c",
        edge: "#1c222d",
        accent: "#7cf6c4",
        warn: "#ffb454",
        danger: "#ff6b6b",
        muted: "#8693a8",
      },
    },
  },
  plugins: [],
};
