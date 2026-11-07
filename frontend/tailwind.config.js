/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/js/**/*.js"],
  theme: {
    extend: {
      colors: { ink: "#07111f", panel: "#0d1b2d", line: "#21324a", cyan: "#55d6be" },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"] },
      boxShadow: { glow: "0 0 40px rgba(85,214,190,.08)" }
    }
  },
  plugins: []
};

