/**
 * ThemeProvider — applies the active theme's CSS variables to the tree and
 * exposes a light/dark toggle (wired to the Profile screen in Issue 8.4).
 * Defaults to the OS color scheme; the Profile toggle overrides it.
 */
import { createContext, useContext, useMemo, useState } from "react";
import { useColorScheme, View } from "react-native";

import { palette, type Palette, type ThemeName } from "./tokens";
import { themes } from "./vars";

type ThemeContextValue = {
  name: ThemeName;
  colors: Palette;
  toggle: () => void;
  setTheme: (name: ThemeName) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const system = useColorScheme();
  const [override, setOverride] = useState<ThemeName | null>(null);
  const name: ThemeName = override ?? (system === "dark" ? "dark" : "light");

  const value = useMemo<ThemeContextValue>(
    () => ({
      name,
      colors: palette[name],
      toggle: () => setOverride(name === "dark" ? "light" : "dark"),
      setTheme: setOverride,
    }),
    [name],
  );

  return (
    <ThemeContext.Provider value={value}>
      <View style={themes[name]} className="flex-1 bg-bg">
        {children}
      </View>
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within ThemeProvider");
  return ctx;
}
