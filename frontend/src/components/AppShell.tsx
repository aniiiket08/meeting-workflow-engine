import React, { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Activity,
  BarChart3,
  Building2,
  Calendar,
  CheckSquare,
  ChevronLeft,
  ChevronRight,
  Clock,
  Home,
  LogOut,
  Menu,
  MessageSquare,
  Search,
  User as UserIcon,
  X,
} from "lucide-react";
import { useAuth } from "../lib/auth";
import { CommandPalette } from "./CommandPalette";
import { ThemeToggle } from "./ThemeToggle";

interface AppShellProps {
  children: React.ReactNode;
  activePath?: string;
  pageTitle?: string;
  pageSubtitle?: string;
  actionButton?: React.ReactNode;
}

const ROLE_LABEL: Record<string, string> = {
  chairman: "Chairman",
  principal: "Principal",
  hod: "HOD",
  teacher: "Teacher",
  student: "Student",
};

function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

export const AppShell: React.FC<AppShellProps> = ({
  children,
  pageTitle,
  pageSubtitle,
  actionButton,
}) => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  // Collapsible sidebar state (persisted in localStorage)
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem("mo_sidebar_collapsed") === "true";
    } catch {
      return false;
    }
  });

  // Mobile drawer state
  const [mobileOpen, setMobileOpen] = useState(false);

  // Command palette state
  const [cmdOpen, setCmdOpen] = useState(false);

  // Keyboard shortcut listener: Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCmdOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const toggleCollapse = () => {
    setCollapsed((prev) => {
      const next = !prev;
      try {
        localStorage.setItem("mo_sidebar_collapsed", String(next));
      } catch {}
      return next;
    });
  };

  const handleSignOut = () => {
    logout();
    navigate("/login", { replace: true });
  };

  // Role permissions
  const canSchedule = user && ["chairman", "principal", "hod", "teacher"].includes(user.role);
  const canObserve = user && ["chairman", "principal", "hod"].includes(user.role);
  const canAdmin = user && ["chairman", "principal"].includes(user.role);

  // Format today's editorial date
  const todayStr = new Date().toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const navLinks = [
    { label: "Overview", path: "/", icon: Home, group: "Core" },
    { label: "Meetings", path: "/meetings", icon: Calendar, group: "Core" },
    ...(canSchedule
      ? [{ label: "Schedule", path: "/schedule", icon: Clock, group: "Core" }]
      : []),
    { label: "Action Tasks", path: "/actions", icon: CheckSquare, group: "Core" },

    { label: "Memory Chat", path: "/memory", icon: MessageSquare, group: "Intelligence" },
    ...(canObserve
      ? [{ label: "Agent Traces", path: "/traces", icon: Activity, group: "Intelligence" }]
      : []),
    { label: "Evaluations", path: "/evaluations", icon: BarChart3, group: "Intelligence" },

    ...(canAdmin
      ? [{ label: "Admin & Rooms", path: "/admin", icon: Building2, group: "Management" }]
      : []),
    { label: "My Profile", path: "/profile", icon: UserIcon, group: "Management" },
  ];

  return (
    <div className="app-shell">
      {/* ── Mobile Drawer Backdrop ───────────────────────────── */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-ink/40 z-50 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ── Collapsible Sidebar ──────────────────────────────── */}
      <aside
        className={`app-sidebar ${collapsed ? "collapsed" : ""} ${
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        } fixed lg:sticky inset-y-0 left-0`}
      >
        {/* Brand header */}
        <div className="app-sidebar-header">
          {!collapsed ? (
            <Link to="/" className="sidebar-brand">
              <span className="font-serif text-18 font-normal tracking-tight text-ink">
                Meeting Organizer
              </span>
              <sup className="font-sans text-9 text-accent font-semibold ml-0.5">™</sup>
            </Link>
          ) : (
            <Link to="/" className="mx-auto font-serif text-18 text-accent font-bold">
              MO
            </Link>
          )}

          <button
            type="button"
            onClick={toggleCollapse}
            className="hidden lg:flex items-center justify-center w-7 h-7 rounded-sm text-ink-soft hover:text-ink hover:bg-tint transition-colors"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>

          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            className="flex lg:hidden items-center justify-center w-7 h-7 rounded-sm text-ink-soft hover:text-ink"
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation list */}
        <nav className="sidebar-nav" aria-label="Main navigation">
          {["Core", "Intelligence", "Management"].map((groupName) => {
            const items = navLinks.filter((link) => link.group === groupName);
            if (items.length === 0) return null;

            return (
              <div key={groupName} className="mb-3">
                {!collapsed && (
                  <div className="sidebar-group-title">{groupName}</div>
                )}
                <div className="space-y-1">
                  {items.map((item) => {
                    const isActive =
                      item.path === "/"
                        ? location.pathname === "/"
                        : location.pathname === item.path ||
                          location.pathname.startsWith(item.path + "/");
                    const Icon = item.icon;

                    return (
                      <Link
                        key={item.path}
                        to={item.path}
                        onClick={() => setMobileOpen(false)}
                        className={`sidebar-item ${isActive ? "active" : ""}`}
                        title={collapsed ? item.label : undefined}
                      >
                        <div className="sidebar-item-icon">
                          <Icon size={16} strokeWidth={1.5} />
                        </div>
                        {!collapsed && <span>{item.label}</span>}
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </nav>

        {/* User Monogram Footer */}
        {user && (
          <div className="sidebar-footer">
            <div className={`flex items-center ${collapsed ? "justify-center" : "gap-3"}`}>
              <div
                className="monogram w-8 h-8 rounded-sm bg-tint text-ink border border-rule font-serif text-12 font-medium"
                title={`${user.name} (${ROLE_LABEL[user.role] || user.role})`}
              >
                {initials(user.name)}
              </div>

              {!collapsed && (
                <div className="min-w-0 flex-1 leading-tight">
                  <div className="font-serif text-13 text-ink truncate">{user.name}</div>
                  <div className="editorial-tag editorial-tag-default text-9 mt-0.5">
                    {ROLE_LABEL[user.role] || user.role}
                  </div>
                </div>
              )}

              {!collapsed && (
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="p-1.5 text-ink-faint hover:text-accent rounded-sm hover:bg-tint transition-colors"
                  title="Sign Out"
                  aria-label="Sign Out"
                >
                  <LogOut size={16} />
                </button>
              )}
            </div>
          </div>
        )}
      </aside>

      {/* ── Main Content Area ────────────────────────────────── */}
      <div className="app-main">
        {/* Top bar */}
        <header className="app-topbar no-print">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="lg:hidden p-1.5 text-ink hover:bg-tint rounded-sm"
              aria-label="Open navigation menu"
            >
              <Menu size={20} />
            </button>

            {/* Omnisearch command palette button */}
            <button
              type="button"
              onClick={() => setCmdOpen(true)}
              className="flex items-center gap-3 px-3 py-1.5 bg-surface border border-rule rounded-sm text-ink-soft hover:border-ink hover:text-ink transition-colors text-12 font-sans"
              title="Global Search & Quick Actions (Ctrl+K or ⌘K)"
            >
              <Search size={14} className="text-ink-faint" />
              <span className="hidden sm:inline">Search meetings, memory, or run command…</span>
              <span className="sm:hidden">Search…</span>
              <span className="font-mono text-10 text-ink-faint bg-paper px-1.5 py-0.5 border border-rule rounded-sm">
                ⌘K
              </span>
            </button>
          </div>

          <div className="flex items-center gap-3 sm:gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-surface border border-rule rounded-sm shadow-subtle">
              <Calendar size={13} className="text-accent flex-shrink-0" />
              <span className="hidden sm:inline font-serif italic text-14 text-ink tracking-tight">
                {todayStr}
              </span>
              <span className="sm:hidden font-serif italic text-13 text-ink tracking-tight">
                {new Date().toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
              </span>
            </div>

            <div className="border-l border-rule pl-3">
              <ThemeToggle />
            </div>
          </div>
        </header>

        {/* Page Header (if provided) */}
        {(pageTitle || actionButton) && (
          <div className="border-b border-rule bg-surface/60 px-6 py-5 sm:px-10 backdrop-blur-sm">
            <div className="max-w-content mx-auto flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-4">
              <div>
                {pageTitle && (
                  <h1 className="h1-display text-ink tracking-tight font-normal text-24 sm:text-30">{pageTitle}</h1>
                )}
                {pageSubtitle && <p className="lead-italic mt-1 text-13 text-ink-soft max-w-reading">{pageSubtitle}</p>}
              </div>
              {actionButton && <div className="shrink-0">{actionButton}</div>}
            </div>
          </div>
        )}

        {/* Page Content Body */}
        <main className="flex-1 w-full max-w-content mx-auto px-6 py-7 sm:px-10">
          {children}
        </main>
      </div>

      {/* Global Command Palette modal */}
      <CommandPalette open={cmdOpen} onClose={() => setCmdOpen(false)} />
    </div>
  );
};
