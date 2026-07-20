/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        serif: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
        merriweather: ['Merriweather', 'Georgia', 'serif'],
      },
      borderRadius: {
        // Full scale wired to the shared token registry (index.css) so
        // `rounded-xl`/`rounded-2xl`/etc. never silently fall back to
        // Tailwind's own stock scale — one radius system, no exceptions.
        none:  'var(--sq-radius-none)',
        xs:    'var(--sq-radius-xs)',
        sm:    'var(--sq-radius-sm)',
        md:    'var(--sq-radius-md)',
        lg:    'var(--sq-radius-lg)',
        xl:    'var(--sq-radius-xl)',
        '2xl': 'var(--sq-radius-2xl)',
        '3xl': 'var(--sq-radius-3xl)',
        full:  'var(--sq-radius-full)',
        card:  'var(--sq-radius-card)',
        btn:   'var(--sq-radius-btn)',
        input: 'var(--sq-radius-input)',
        badge: 'var(--sq-radius-badge)',
        modal: 'var(--sq-radius-modal)',
      },
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        border: 'hsl(var(--border))',
        input:  'hsl(var(--input))',
        ring:   'hsl(var(--ring))',
        // Default hairline border used by ds/ cards, tables, dividers —
        // distinct from the shadcn `border-border` slot above (that one
        // backs the global `* { @apply border-border }` reset only).
        // Mirrors lib/tokens.js's BRD/BRDH exactly.
        hairline: {
          DEFAULT: 'var(--sq-border)',
          strong:  'var(--sq-border-strong)',
          soft:    'var(--sq-border-soft)',
        },
        chart: {
          '1': 'hsl(var(--chart-1))',
          '2': 'hsl(var(--chart-2))',
          '3': 'hsl(var(--chart-3))',
          '4': 'hsl(var(--chart-4))',
          '5': 'hsl(var(--chart-5))',
        },
        // Synaptiq brand tokens — usable as bg-navy, text-navy-600, etc.
        navy: {
          50:  'var(--sq-navy-50)',
          100: 'var(--sq-navy-100)',
          200: 'var(--sq-navy-200)',
          300: 'var(--sq-navy-300)',
          400: 'var(--sq-navy-400)',
          500: 'var(--sq-navy-500)',
          600: 'var(--sq-navy-600)',
          700: 'var(--sq-navy-700)',
          800: 'var(--sq-navy-800)',
          900: 'var(--sq-navy-900)',
          DEFAULT: 'var(--sq-navy-700)',
          // Pre-blended tints — do NOT use `navy-700/[n]` opacity-modifier
          // syntax, it silently renders transparent (var()-backed colors
          // can't be alpha-blended by Tailwind's JIT). Use these instead.
          wash:        'var(--sq-navy-wash)',
          'wash-border': 'var(--sq-navy-wash-border)',
        },
        crimson: {
          50:  'var(--sq-crimson-50)',
          100: 'var(--sq-crimson-100)',
          200: 'var(--sq-crimson-200)',
          300: 'var(--sq-crimson-300)',
          400: 'var(--sq-crimson-400)',
          500: 'var(--sq-crimson-500)',
          600: 'var(--sq-crimson-600)',
          700: 'var(--sq-crimson-700)',
          DEFAULT: 'var(--sq-crimson-600)',
        },
        // Secondary accents — charts, AI surfaces (mirrors lib/tokens.js VIOLET/TEAL)
        violet: {
          DEFAULT: 'var(--sq-violet)',
          bg:      'var(--sq-violet-bg)',
          text:    'var(--sq-violet-text)',
        },
        teal: {
          DEFAULT: 'var(--sq-teal)',
          bg:      'var(--sq-teal-bg)',
          text:    'var(--sq-teal-text)',
        },
        // Semantic state colors — the ONE success/warning/danger/info palette.
        // Mirrors lib/tokens.js's SUCCESS_BG/TEXT etc. exactly.
        success: {
          bg:     'var(--sq-success-bg)',
          text:   'var(--sq-success-text)',
          border: 'var(--sq-success-border)',
        },
        warning: {
          bg:     'var(--sq-warning-bg)',
          text:   'var(--sq-warning-text)',
          border: 'var(--sq-warning-border)',
        },
        danger: {
          bg:     'var(--sq-danger-bg)',
          text:   'var(--sq-danger-text)',
          border: 'var(--sq-danger-border)',
        },
        info: {
          bg:     'var(--sq-info-bg)',
          text:   'var(--sq-info-text)',
          border: 'var(--sq-info-border)',
        },
      },
      boxShadow: {
        'sq-xs':         'var(--sq-shadow-xs)',
        'sq-sm':         'var(--sq-shadow-sm)',
        'sq-md':         'var(--sq-shadow-md)',
        'sq-lg':         'var(--sq-shadow-lg)',
        'sq-xl':         'var(--sq-shadow-xl)',
        'sq-2xl':        'var(--sq-shadow-2xl)',
        'sq-card':       'var(--sq-shadow-card)',
        'sq-card-hover': 'var(--sq-shadow-card-hover)',
        'sq-modal':      'var(--sq-shadow-modal)',
        'sq-dropdown':   'var(--sq-shadow-dropdown)',
        'sq-focus':      '0 0 0 3px rgba(15,40,71,0.15)',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to:   { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to:   { height: '0' },
        },
        'sq-shimmer': {
          '0%':   { backgroundPosition: '-600px 0' },
          '100%': { backgroundPosition:  '600px 0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up':   'accordion-up 0.2s ease-out',
        'sq-shimmer':     'sq-shimmer 1.6s ease-in-out infinite',
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
