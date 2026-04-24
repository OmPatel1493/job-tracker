"use client";

import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/applications": "Applications",
  "/resume": "Resume",
  "/analytics": "Analytics",
};

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

function getTitle(pathname: string): string {
  for (const [prefix, title] of Object.entries(PAGE_TITLES)) {
    if (pathname === prefix || pathname.startsWith(prefix + "/")) return title;
  }
  return "JobTracker AI";
}

interface TopBarProps {
  onMenuClick: () => void;
}

export default function TopBar({ onMenuClick }: TopBarProps) {
  const pathname = usePathname();
  const { user } = useAuth();

  return (
    <header className="flex h-14 items-center border-b border-slate-800 bg-slate-950 px-4 sm:px-6">
      <button
        onClick={onMenuClick}
        className="lg:hidden mr-3 text-slate-400 hover:text-white transition-colors"
        aria-label="Open sidebar"
      >
        <Menu className="h-5 w-5" />
      </button>
      <h1 className="flex-1 text-center text-sm font-semibold text-white lg:text-left">
        {getTitle(pathname)}
      </h1>
      {user && (
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white">
          {getInitials(user.full_name || user.email)}
        </div>
      )}
    </header>
  );
}
