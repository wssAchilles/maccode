import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0b1020',
        panel: '#121a30',
        accent: '#00d4ff',
        gain: '#34d399',
        loss: '#f87171',
      },
    },
  },
  plugins: [],
} satisfies Config
