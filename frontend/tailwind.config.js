/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#07090e',
        command: {
          950: '#06080d',
          900: '#0a0d14',
          850: '#0e121b',
          800: '#121722',
          750: '#161d2a',
          700: '#1a2232',
          600: '#232e42',
        },
        surface: {
          900: '#0a0d14',
          800: '#0e121b',
          700: '#121722',
          600: '#161d2a',
          500: '#1f293d',
        },
        cyan: {
          accent: '#00f0ff',
          glow: 'rgba(0, 240, 255, 0.4)',
        },
        accent: {
          blue: '#0ea5e9',
          cyan: '#06b6d4',
          purple: '#8b5cf6',
          green: '#10b981',
          red: '#f43f5e',
          amber: '#f59e0b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
      },
      boxShadow: {
        glass: '0 4px 24px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)',
        'glass-hover': '0 8px 32px rgba(6,182,212,0.15), inset 0 1px 0 rgba(255,255,255,0.08)',
        glow: '0 0 20px rgba(6,182,212,0.3)',
        'glow-cyan': '0 0 25px rgba(0, 240, 255, 0.25)',
        'glow-match': '0 0 30px rgba(16, 185, 129, 0.3)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
