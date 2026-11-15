/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 950: "#0A1F23", 900: "#0E2A2F", 800: "#173B41", 700: "#245058" },
        paper: { DEFAULT: "#EDF1F2", card: "#FFFFFF", line: "#D8E0E2" },
        solar: { DEFAULT: "#F2A71B", deep: "#B97800", soft: "#FDF1D6" },
        ok: "#1F8A5B", bad: "#C2412D", muted: "#5D7176",
      },
      fontFamily: {
        display: ['"Bricolage Grotesque"', "system-ui", "sans-serif"],
        sans: ['"IBM Plex Sans"', "system-ui", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
