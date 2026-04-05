"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Briefcase,
  FileText,
  LayoutDashboard,
  LogOut,
} from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

const navLinks = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/applications", label: "Applications", icon: Briefcase },
  { href: "/resume", label: "Resume", icon: FileText },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
];

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="fixed inset-y-0 left-0 flex w-64 flex-col border-r border-slate-700/50 bg-slate-900">
      {/* Logo */}
      <div className="flex items-center gap-2 border-b border-slate-700/50 px-5 py-4">
        <Briefcase className="h-6 w-6 text-blue-500" />
        <span className="font-semibold text-white">JobTracker AI</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navLinks.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors ${
                active
                  ? "bg-blue-600/20 text-blue-400"
                  : "text-slate-400 hover:bg-slate-800 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User + Logout */}
      <div className="border-t border-slate-700/50 px-3 py-4 space-y-3">
        {user && (
          <div className="flex items-center gap-3 px-2">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white">
              {getInitials(user.full_name || user.email)}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm text-white">{user.full_name}</p>
              <p className="truncate text-xs text-slate-400">{user.email}</p>
            </div>
          </div>
        )}
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm text-slate-400 transition-colors hover:text-red-400"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          Logout
        </button>
      </div>
    </aside>
  );
}
