"use client";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";

const navItems = [
  { href: "/chat", label: "AI Chat", icon: "M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" },
  { href: "/generate", label: "Generator", icon: "M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" },
  { href: "/documents", label: "Documents", icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" },
  { href: "/type-tree", label: "Type Tree", icon: "M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" },
  { href: "/mapping", label: "Mapping", icon: "M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" },
  { href: "/debugging", label: "Debugging", icon: "M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" },
];

const adminItems = [];

export default function Sidebar({ currentPath }: { currentPath: string }) {
  const { user } = useAuth();

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 glass-card rounded-none border-r border-surface-200 dark:border-surface-800 flex flex-col z-30">
      {/* Logo */}
      <div className="p-5 border-b border-surface-200 dark:border-surface-800">
        <Link href="/chat" className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-brand-600 to-accent-600 flex items-center justify-center shadow-glow">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <div>
            <div className="font-bold text-sm gradient-text">AIEP</div>
            <div className="text-[10px] text-surface-500 dark:text-surface-400 font-medium tracking-wide">INTEGRATION PLATFORM</div>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        <div className="text-[10px] font-semibold text-surface-400 dark:text-surface-500 uppercase tracking-wider px-3 py-2">
          Modules
        </div>
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`sidebar-link ${currentPath === item.href ? "active" : ""}`}
          >
            <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
            </svg>
            <span>{item.label}</span>
          </Link>
        ))}

        {user?.role === "admin" && (
          <>
            <div className="text-[10px] font-semibold text-surface-400 dark:text-surface-500 uppercase tracking-wider px-3 pt-4 pb-2">
              Administration
            </div>
            {adminItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`sidebar-link ${currentPath.startsWith(item.href) ? "active" : ""}`}
              >
                <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
                </svg>
                <span>{item.label}</span>
              </Link>
            ))}
          </>
        )}
      </nav>

      {/* Plugin indicator */}
      <div className="p-4 border-t border-surface-200 dark:border-surface-800">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs text-surface-500 dark:text-surface-400">IBM ITX Plugin Active</span>
        </div>
      </div>
    </aside>
  );
}
