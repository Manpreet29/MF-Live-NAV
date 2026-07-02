export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ['"DM Serif Display"', 'Georgia', 'serif'],
        body:    ['"DM Sans"', 'system-ui', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        ink:    '#0D0D0D',
        paper:  '#F7F4EF',
        cream:  '#EDE9E1',
        gold:   '#C8A84B',
        'gold-dark': '#9A7B2E',
        gain:   '#1A6B3C',
        'gain-bg': '#D1FAE5',
        loss:   '#9B1C1C',
        'loss-bg': '#FEE2E2',
        muted:  '#6B6560',
        border: '#D8D3CA',
      },
      animation: {
        'fade-in':  'fadeIn 0.35s ease-out both',
        'slide-up': 'slideUp 0.35s ease-out both',
        'spin-slow': 'spin 1.5s linear infinite',
      },
      keyframes: {
        fadeIn:  { from: { opacity: '0' },                         to: { opacity: '1' } },
        slideUp: { from: { opacity: '0', transform: 'translateY(10px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
      },
    },
  },
  plugins: [],
}
