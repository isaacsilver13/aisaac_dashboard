# AIsaac Dashboard — application stack flows and mobile shell

Status: complete
Scope: `aisaac_dashboard` frontend

## Goal

Add a per-application Stack tab that presents the known request, deployment,
data/provider, and AIsaac-monitoring flow. Repair the responsive shell so the
mobile top bar and page content stack vertically instead of becoming flex-row
siblings.

## Constraints and non-goals

- Keep the diagrams read-only and derived from the dashboard's documented
  topology; do not add browser-supplied endpoints, credentials, or API calls.
- Use only verified stack details. Where the dashboard cannot observe a private
  datastore, label the boundary generically instead of inventing one.
- Preserve the existing uncommitted GitHub/timestamp work.
- Do not deploy without separate approval.

## Approach

1. Add a data-driven React Stack tab and a responsive semantic flow diagram for
   each registered application.
2. Link the new tab into the application navigation and update the route
   documentation.
3. Fix the mobile shell's flex direction and make the app tabs horizontally
   scrollable rather than clipped at narrow widths.
4. Add focused component tests, run frontend type/build/lint checks, and have
   an independent agent review the resulting changes.

## Verification

- Automated: focused Stack tab tests; frontend lint and production build.
- Manual: inspect an application Stack tab at desktop and 320px widths; open
  and close the mobile drawer; verify the page body remains below the top bar
  and does not horizontally overflow.

## Risks / decisions needed

- The dashboard only observes public endpoints and selected metrics. The tab is
  an operational map, not a full data lineage or a source of infrastructure
  truth for private systems.

## Result

- Added the Stack tab, its tested six-application topology map, and route
  documentation.
- Fixed the mobile shell to stack the top bar and page content, allow content
  to grow the document vertically, and retain every application tab through a
  horizontally scrollable tab row.
- Verified with frontend lint, production build, and five focused Vitest cases.
  The local interactive browser-preview surface was unavailable in this
  session, so no device screenshot was captured.
