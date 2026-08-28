/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Industrial control-room palette. Status colors are the subject's own
        // vernacular (nominal / caution / trip); accent is a deliberate non-purple.
        bg: '#0E1219',
        panel: '#151B24',
        panel2: '#1B222D',
        border: '#273041',
        text: '#DCE3ED',
        muted: '#7E8A9C',
        accent: '#37C2C9', // instrument cyan — brand / interactive
        nominal: '#45B36B',
        caution: '#E0A63C',
        trip: '#E5484D',
        steel: '#5B7089',
      },
      fontFamily: {
        // Self-hosted / system stacks only — no CDN font requests (sovereignty).
        sans: ['"Segoe UI"', 'system-ui', '-apple-system', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Cascadia Code"', '"SF Mono"', 'Consolas', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}
