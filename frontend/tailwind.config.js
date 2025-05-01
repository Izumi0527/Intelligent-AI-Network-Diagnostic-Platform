import animate from "tailwindcss-animate";
import { setupInspiraUI } from "@inspira-ui/plugins";

export default {
  darkMode: "selector",
  safelist: ["dark"],
  prefix: "",
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",

        // 新的主题配色
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
          focus: "hsl(var(--primary-focus))",
          glow: "hsl(var(--primary-glow))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        terminal: {
          DEFAULT: "hsl(var(--terminal-background))",
          foreground: "hsl(var(--terminal-foreground))",
          success: "hsl(var(--terminal-success))",
          error: "hsl(var(--terminal-error))",
          command: "hsl(var(--terminal-command))",
          prompt: "hsl(var(--terminal-prompt))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
          cyan: "hsl(var(--accent-cyan))",
          purple: "hsl(var(--accent-purple))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
          hovered: "hsl(var(--card-hovered))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--foreground))",
        },
      },
      borderRadius: {
        xl: "calc(var(--radius) + 4px)",
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      // 添加网格背景图案
      backgroundImage: {
        'grid-pattern': 'linear-gradient(to right, rgba(60, 60, 80, 0.1) 1px, transparent 1px), linear-gradient(to bottom, rgba(60, 60, 80, 0.1) 1px, transparent 1px)',
        'radial-gradient': 'radial-gradient(circle at center, rgba(30, 41, 59, 0), rgba(15, 23, 42, 0.6))',
      },
      backgroundSize: {
        'grid': '20px 20px',
      },
      boxShadow: {
        'glow-sm': '0 0 5px rgba(66, 153, 225, 0.5)',
        'glow': '0 0 10px rgba(66, 153, 225, 0.5)',
        'glow-lg': '0 0 15px rgba(66, 153, 225, 0.5)',
        'glow-purple': '0 0 10px rgba(139, 92, 246, 0.5)',
        'glow-cyan': '0 0 10px rgba(14, 165, 233, 0.5)',
        'terminal': 'inset 0 0 10px rgba(0, 0, 0, 0.5)',
      },
      keyframes: {
        blink: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0 },
        },
        dataflow: {
          '0%': { backgroundPosition: '0% 0%' },
          '100%': { backgroundPosition: '100% 100%' },
        },
        fadeIn: {
          '0%': { opacity: 0 },
          '100%': { opacity: 1 },
        },
        slideUp: {
          '0%': { transform: 'translateY(5px)', opacity: 0 },
          '100%': { transform: 'translateY(0)', opacity: 1 },
        },
        pulse: {
          '0%, 100%': { opacity: 1 },
          '50%': { opacity: 0.7 },
        },
      },
      animation: {
        blink: 'blink 1s step-end infinite',
        dataflow: 'dataflow 10s linear infinite',
        fadeIn: 'fadeIn 0.3s ease-in-out',
        slideUp: 'slideUp 0.3s ease-out',
        pulse: 'pulse 2s ease-in-out infinite',
      },
    },
  },

  plugins: [animate, setupInspiraUI],
};
