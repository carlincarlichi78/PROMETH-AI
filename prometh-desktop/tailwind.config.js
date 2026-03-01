/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './src/**/*.{js,ts,jsx,tsx}',
    '../web/src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        superficie: {
          50: '#fafafa',
          100: '#f4f4f5',
          200: '#e4e4e7',
          300: '#d4d4d8',
          400: '#a1a1aa',
          500: '#71717a',
          600: '#52525b',
          700: '#3f3f46',
          800: '#27272a',
          850: '#1e1e22',
          900: '#18181b',
          950: '#09090b',
        },
        acento: {
          50: 'rgb(var(--acento-50, 236 253 245) / <alpha-value>)',
          100: 'rgb(var(--acento-100, 209 250 229) / <alpha-value>)',
          200: 'rgb(var(--acento-200, 167 243 208) / <alpha-value>)',
          300: 'rgb(var(--acento-300, 110 231 183) / <alpha-value>)',
          400: 'rgb(var(--acento-400, 52 211 153) / <alpha-value>)',
          500: 'rgb(var(--acento-500, 16 185 129) / <alpha-value>)',
          600: 'rgb(var(--acento-600, 5 150 105) / <alpha-value>)',
          700: 'rgb(var(--acento-700, 4 120 87) / <alpha-value>)',
          800: 'rgb(var(--acento-800, 6 95 70) / <alpha-value>)',
          900: 'rgb(var(--acento-900, 6 78 59) / <alpha-value>)',
          950: 'rgb(var(--acento-950, 2 44 34) / <alpha-value>)',
        },
      },
      fontFamily: {
        sans: ['Outfit', 'system-ui', 'sans-serif'],
        display: ['Instrument Serif', 'Georgia', 'serif'],
      },
      animation: {
        'pulso-suave': 'pulsoSuave 4s ease-in-out infinite',
        'flotar': 'flotar 6s ease-in-out infinite',
        'deslizar-arriba': 'deslizarArriba 0.6s ease-out',
        'aparecer': 'aparecer 0.8s ease-out',
      },
      keyframes: {
        pulsoSuave: {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '0.8' },
        },
        flotar: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        deslizarArriba: {
          '0%': { opacity: '0', transform: 'translateY(20px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        aparecer: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
