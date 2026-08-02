/**
 * LifePilot AI design tokens (TypeScript mirror of tailwind.config.js).
 *
 * Source of truth: design/LifePilot AI - Standalone.html CSS custom properties.
 * Use these for values NativeWind classes can't express directly — gradients,
 * chart colors, and imperative APIs (StatusBar, native pickers). For layout and
 * color prefer NativeWind classes so screens compose from tokens.
 */

// Brand palette — identical in light and dark (prototype --primary/--secondary/…).
export const brand = {
  primary: "#4F46E5",
  primaryDark: "#4338CA",
  secondary: "#7C3AED",
  accent: "#06B6D4",
  danger: "#EF4444",
  warning: "#F59E0B",
  success: "#10B981",
} as const;

// Hero gradient (prototype --grad).
export const heroGradient = ["#4F46E5", "#7C3AED"] as const;

// Semantic surface/text colors per theme (prototype :root and [data-theme=dark]).
export const palette = {
  light: {
    bg: "#F8FAFC",
    card: "#FFFFFF",
    text: "#0F172A",
    textDim: "#64748B",
    border: "rgba(15,23,42,0.08)",
  },
  dark: {
    bg: "#0F172A",
    card: "#1E293B",
    text: "#F1F5F9",
    textDim: "#94A3B8",
    border: "rgba(255,255,255,0.08)",
  },
} as const;

export type ThemeName = keyof typeof palette;
export type Palette = (typeof palette)[ThemeName];
