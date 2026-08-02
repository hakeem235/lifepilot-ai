/**
 * Theme CSS variables consumed by tailwind.config.js semantic colors
 * (bg/card/text/text-dim/border). NativeWind's `vars()` sets these per theme;
 * ThemeProvider applies the active set to the tree root. Values are the RGB
 * channels of theme/tokens.ts palette (NativeWind needs `r g b` for <alpha-value>).
 */
import { vars } from "nativewind";

export const themes = {
  light: vars({
    "--color-bg": "248 250 252", // #F8FAFC
    "--color-card": "255 255 255", // #FFFFFF
    "--color-text": "15 23 42", // #0F172A
    "--color-text-dim": "100 116 139", // #64748B
    "--color-border": "15 23 42", // alpha applied via class
  }),
  dark: vars({
    "--color-bg": "15 23 42", // #0F172A
    "--color-card": "30 41 59", // #1E293B
    "--color-text": "241 245 249", // #F1F5F9
    "--color-text-dim": "148 163 184", // #94A3B8
    "--color-border": "255 255 255",
  }),
} as const;
