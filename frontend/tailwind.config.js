/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#111827',
        canvas: '#0b0f19',
        border: '#1f2937',
      },
    },
  },
  plugins: [],
};
