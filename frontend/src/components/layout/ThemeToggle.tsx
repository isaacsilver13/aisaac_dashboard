import { MoonSat, SunLight } from "iconoir-react";

import { useTheme } from "../../theme/useTheme";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const Icon = theme === "dark" ? SunLight : MoonSat;
  return (
    <button type="button" className="theme-toggle" onClick={toggle} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>
      <Icon width={16} height={16} aria-hidden="true" />
    </button>
  );
}
