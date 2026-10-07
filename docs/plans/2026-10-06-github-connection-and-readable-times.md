# GitHub connection and readable timestamps

Date: 2026-10-06
Repository: `aisaac_dashboard`

1. Keep GitHub access server-side and read-only: use the existing `GITHUB_TOKEN` setting, supplied as a fine-grained token scoped only to the monitored repositories.
2. Make the connection procedure and its non-secret status easy to find from Settings and the README.
3. Replace terse time-only freshness and activity labels with relative, human-readable times while retaining the exact local timestamp in the native hover tooltip.
4. Verify the formatter, relevant UI behavior, linting, and the production build.

The dashboard must never accept, persist, or display a GitHub token in the browser.
