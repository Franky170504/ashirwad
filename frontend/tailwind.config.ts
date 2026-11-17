import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          light: "#e6ff9f", // left panel
          dark: "#0b472b",  // right panel
          button: "#0e5a32",
          buttonHover: "#0a4727",
        },
      },
      fontFamily: {
        script: ["var(--font-script)", "cursive"],
        body: ["var(--font-body)", "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};
export default config;
