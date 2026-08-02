/**
 * LifePilot AI design tokens — sourced from the prototype
 * (design/LifePilot AI - Standalone.html). Semantic colors are driven by CSS
 * variables so light/dark themes swap at runtime (see theme/vars.ts). Screens
 * compose from these tokens — never hardcode hex values in components.
 */
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        // Brand — fixed across themes (prototype --primary / --secondary / --accent).
        primary: {
          DEFAULT: "#4F46E5",
          600: "#4F46E5",
          700: "#4338CA",
        },
        secondary: "#7C3AED",
        accent: "#06B6D4",
        danger: "#EF4444",
        warning: "#F59E0B",
        success: "#10B981",
        // Semantic surface/text — theme-driven via CSS variables.
        bg: "rgb(var(--color-bg) / <alpha-value>)",
        card: "rgb(var(--color-card) / <alpha-value>)",
        text: "rgb(var(--color-text) / <alpha-value>)",
        "text-dim": "rgb(var(--color-text-dim) / <alpha-value>)",
        border: "rgb(var(--color-border) / <alpha-value>)",
      },
      borderRadius: {
        card: "20px",
        chip: "9999px",
      },
      fontSize: {
        // iOS-scaled type ramp from the prototype.
        display: ["28px", { lineHeight: "34px", fontWeight: "700" }],
        title: ["20px", { lineHeight: "26px", fontWeight: "700" }],
        body: ["15px", { lineHeight: "22px" }],
        caption: ["12px", { lineHeight: "16px" }],
      },
    },
  },
  plugins: [],
};
