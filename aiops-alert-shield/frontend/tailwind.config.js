/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        obsidian: "#09090B",
        charcoal: "#141418",
        elevated: "#1C1C22",
        primaryText: "#FAFAFA",
        mutedLabel: "#A1A1AA",
        borderStructural: "#3F3F46",
        borderActive: "#F4F4F5",
        signal: {
          crimson: "#FF2E4C", // Verified Incident / Critical
          amber: "#FFB800",   // Context Divergence / Human Review
          lime: "#CCFF00",    // Suppressed Noise / Healthy
          cyan: "#00E5FF",    // Evidence Trace / Links
        }
      },
      boxShadow: {
        'neo': '4px 4px 0px #000000',
        'neo-sm': '2px 2px 0px #000000',
        'neo-crimson': '4px 4px 0px #FF2E4C',
        'neo-lime': '4px 4px 0px #CCFF00',
        'neo-amber': '4px 4px 0px #FFB800',
        'neo-cyan': '4px 4px 0px #00E5FF',
      },
      fontFamily: {
        sans: ['Space Grotesk', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      }
    },
  },
  plugins: [],
};
