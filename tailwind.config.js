/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        pn: {
          bg:      '#191D32',
          surface: '#292F44',
          border:  '#453A49',
          dim:     '#6D3B47',
          accent:  '#BA2C73',
          txt:     '#F0EEF8',
          sub:     '#9097B8',
          muted:   '#5A6080',
        },
      },
      borderRadius: {
        pill: '9999px',
      },
      boxShadow: {
        card:       '0 4px 28px rgba(0,0,0,0.45)',
        'card-hover': '0 10px 40px rgba(0,0,0,0.55)',
      },
    },
  },
  plugins: [],
}
