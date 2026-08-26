/**
 * Admin Dark Mode Theme Tokens
 *
 * Provides dark-mode-aware colors for admin pages.
 * Uses the existing ThemeProvider's colorScheme.
 */
import { useColorScheme } from "@/hooks/use-color-scheme";
import { Colors as LightColors } from "./tokens";

const DarkColors = {
  bg: "#0D0D0F",
  surface: "#1C1C1E",
  surfaceAlt: "#2C2C2E",
  surfaceSunken: "#1C1C1E",

  primary: "#FF4D68",
  primaryLight: "#2D1520",
  primaryDark: "#FF6B82",

  success: "#4DB982",
  successLight: "#0D2818",

  warning: "#F3A54F",
  warningLight: "#2D1F0D",

  danger: "#FF4D68",
  dangerLight: "#2D1520",

  info: "#4DA6FF",
  infoLight: "#0D1F2D",

  text: "#F5F5F7",
  textSecondary: "#8E8E93",
  textMuted: "#636366",
  textInverse: "#1C1C1E",

  border: "#38383A",
  divider: "#2C2C2E",

  black: "#1C1C1E",
  white: "#F5F5F7",
} as const;

type ColorTokens = typeof LightColors;

function resolveColors(scheme: "light" | "dark"): ColorTokens {
  return (scheme === "dark" ? DarkColors : LightColors) as ColorTokens;
}

/**
 * useAdminColors – Returns the current color palette based on system/app scheme.
 * Drop-in replacement for `Colors` in admin components.
 *
 *   const colors = useAdminColors();
 *   <View style={{ backgroundColor: colors.surface }}>
 */
export function useAdminColors(): ColorTokens {
  const scheme = useColorScheme();
  return resolveColors(scheme ?? "light");
}

export { DarkColors };
