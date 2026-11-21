/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#006747", dark: "#004d38", soft: "#e9f5ef" },
        accent: "#e9a900",
        line: "#e4ebe6",
        ink: { DEFAULT: "#152b25", muted: "#60736c" },
      },
      boxShadow: { card: "0 5px 24px rgb(31 67 48 / 4%)" },
    },
  },
  plugins: [],
};
