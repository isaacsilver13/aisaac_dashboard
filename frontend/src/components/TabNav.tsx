import { NavLink } from "react-router-dom";

interface TabNavProps {
  tabs: { to: string; label: string }[];
}

export function TabNav({ tabs }: TabNavProps) {
  return (
    <nav className="tab-nav" aria-label="Command Center sections">
      {tabs.map((tab) => (
        <NavLink
          key={tab.to}
          to={tab.to}
          end={tab.to === "/"}
          className={({ isActive }) => `tab-nav-link${isActive ? " tab-nav-link-active" : ""}`}
        >
          {tab.label}
        </NavLink>
      ))}
    </nav>
  );
}
