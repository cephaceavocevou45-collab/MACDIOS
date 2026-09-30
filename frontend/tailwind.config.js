/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#0c765c", dark: "#075b47", soft: "#e9f5ef" },
        accent: "#f3a94c",
        line: "#e4ebe6",
        ink: { DEFAULT: "#152b25", muted: "#60736c" },
      },
      boxShadow: { card: "0 5px 24px rgb(31 67 48 / 4%)" },
    },
  },
  plugins: [],
};
