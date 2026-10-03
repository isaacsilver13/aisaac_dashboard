import { Moon, Sun } from "lucide-react";

import { useTheme } from "../../theme/useTheme";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const Icon = theme === "dark" ? Sun : Moon;
  return (
    <button type="button" className="theme-toggle" onClick={toggle} aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}>
      <Icon size={16} aria-hidden="true" />
    </button>
  );
}
