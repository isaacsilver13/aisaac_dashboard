import { NavLink, Navigate, useLocation, useParams } from "react-router-dom";

import { HealthTab } from "../components/application/HealthTab";
import { EmptyState } from "../components/primitives/EmptyState";
import { PageHeader } from "../components/primitives/PageHeader";

/** Placeholder for sections the redesign hasn't built yet. */
export function ComingSoon({ title }: { title: string }) {
  return (
    <>
      <PageHeader title={title} />
      <EmptyState message="Not built yet." />
    </>
  );
}

const APP_TABS = ["overview", "health", "deployments", "data", "logs"] as const;
const capitalize = (text: string) => text.replace(/^\w/, (c) => c.toUpperCase());

export function ApplicationPage() {
  const { appId, tab } = useParams();
  return (
    <>
      <PageHeader title={appId ?? "Application"} />
      <nav className="tab-row" aria-label="Application sections">
        {APP_TABS.map((t) => (
          <NavLink key={t} to={`/applications/${appId}/${t}`} className={({ isActive }) => `tab-link${isActive ? " tab-link-active" : ""}`}>
            {capitalize(t)}
          </NavLink>
        ))}
      </nav>
      {tab === "health" && appId ? (
        <HealthTab appId={appId} />
      ) : (
        <EmptyState message={`${capitalize(tab ?? "overview")} is not built yet.`} />
      )}
    </>
  );
}

export function NotFound() {
  return (
    <>
      <PageHeader title="Not found" />
      <EmptyState message="That page does not exist." />
    </>
  );
}

/** Keeps old links (including ?note=) working after a route rename. */
export function RedirectKeepSearch({ to }: { to: string }) {
  const { search } = useLocation();
  return <Navigate to={{ pathname: to, search }} replace />;
}
