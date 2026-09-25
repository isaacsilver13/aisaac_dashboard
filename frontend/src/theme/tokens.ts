/**
 * Single source of truth for the dashboard's design tokens.
 * Anything visual (color, spacing, radius, type scale) should be read from
 * here rather than hardcoded in components or duplicated in CSS.
 */

export const color = {
  background: "#0b1120",
  surface: "#111827",
  surfaceElevated: "#172033",
  border: "rgba(255, 255, 255, 0.08)",
  borderStrong: "rgba(255, 255, 255, 0.14)",

  textPrimary: "#f8fafc",
  textSecondary: "#cbd5e1",
  textMuted: "#94a3b8",
  textDisabled: "#64748b",

  brand: "#818cf8",
  brandHover: "#6366f1",

  success: "#34d399",
  warning: "#fbbf24",
  error: "#fb7185",
  info: "#38bdf8",
} as const;

/**
 * Semantic aliases so status-bearing components (badges, dots, banners)
 * consume meaning ("success", "error") rather than raw hex values.
 */
export const semantic = {
  success: color.success,
  successSubtle: "rgba(52, 211, 153, 0.12)",
  warning: color.warning,
  warningSubtle: "rgba(251, 191, 36, 0.12)",
  error: color.error,
  errorSubtle: "rgba(251, 113, 133, 0.12)",
  info: color.info,
  infoSubtle: "rgba(56, 189, 248, 0.12)",
  neutral: color.textMuted,
  neutralSubtle: "rgba(148, 163, 184, 0.12)",
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
  huge: 40,
  massive: 48,
} as const;

export const radius = {
  sm: "6px",
  md: "10px",
  lg: "14px",
  xl: "20px",
} as const;

export const typography = {
  fontSans: '"Manrope", sans-serif',
  fontMono: '"DM Mono", monospace',
  pageTitle: { size: "32px", weight: 700 },
  sectionTitle: { size: "20px", weight: 600 },
  cardTitle: { size: "16px", weight: 600 },
  body: { size: "14px", weight: 400 },
  metadata: { size: "11px", weight: 500 },
} as const;
