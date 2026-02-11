/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        // Aquí definimos las fuentes para poder usar 'font-kanit' y 'font-raleway'
        kanit: ["var(--font-kanit)", "sans-serif"],
        raleway: ["var(--font-raleway)", "sans-serif"],
      },
      // Si quieres añadir tus colores personalizados también (opcional)
      colors: {
        aquamarine: "#42E2B8", // Para usar bg-aquamarine
      }
    },
  },
  plugins: [],
};