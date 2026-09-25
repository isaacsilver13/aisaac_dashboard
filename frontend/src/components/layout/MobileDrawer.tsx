import { useEffect, useRef } from "react";
import { NavLink } from "react-router-dom";
import { X } from "lucide-react";

import { NAV_ITEMS } from "./navItems";

interface MobileDrawerProps {
  open: boolean;
  onClose: () => void;
}

export function MobileDrawer({ open, onClose }: MobileDrawerProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    closeButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="app-drawer-overlay" onClick={onClose}>
      <div
        className="app-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Navigation menu"
        onClick={(event) => event.stopPropagation()}
      >
        <button type="button" ref={closeButtonRef} className="app-drawer-close" onClick={onClose} aria-label="Close navigation menu">
          <X size={20} aria-hidden="true" />
        </button>
        <nav className="app-sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onClose}
              className={({ isActive }) => `app-sidebar-link${isActive ? " app-sidebar-link-active" : ""}`}
            >
              <item.icon size={17} strokeWidth={2.1} aria-hidden="true" />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  );
}
