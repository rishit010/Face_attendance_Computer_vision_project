/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#0D1B2A',
          light: '#1B2838',
          lighter: '#243447',
        },
        cream: {
          DEFAULT: '#F5F0E8',
          dark: '#E8E0D0',
        },
        bauhaus: {
          red: '#C1392B',
          gold: '#D4A843',
          blue: '#2C5F8A',
        },
        slate: {
          DEFAULT: '#4A5568',
        },
      },
      fontFamily: {
        display: ['"Playfair Display"', 'serif'],
        sans: ['"Space Grotesk"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        'bauhaus': '8px 8px 0px #0D1B2A',
        'bauhaus-sm': '4px 4px 0px #0D1B2A',
        'bauhaus-hover': '12px 12px 0px #0D1B2A',
        'depth': '0 20px 60px rgba(13, 27, 42, 0.3), 0 8px 20px rgba(13, 27, 42, 0.2)',
        'depth-lg': '0 30px 80px rgba(13, 27, 42, 0.4), 0 12px 30px rgba(13, 27, 42, 0.25)',
      },
      perspective: {
        '1000': '1000px',
      },
    },
  },
  plugins: [],
}
