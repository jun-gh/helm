/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{html,ts}"],
  theme: {
    extend: {
      colors: {
        helm: {
          canvas: "#F5F5F5",   // 1. Leftmost / Most used: Canvas base
          teal: "#76ABAE",     // 2. Second: Structural cards, panels, borders, accents
          slate: "#303841",    // 3. Third: High-contrast typography & dark code blocks
          coral: "#FF5722",    // 4. Fourth / Rightmost: Action buttons & focal highlights
        },
      },
    },
  },
  plugins: [],
};
