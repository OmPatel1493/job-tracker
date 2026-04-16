"use client";

import { usePathname } from "next/navigation";
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

export default function TopBar() {
  const pathname = usePathname();
  const { user } = useAuth();

  return (
    <header className="flex h-14 items-center justify-between border-b border-slate-800 bg-slate-950 px-6">
      <h1 className="text-sm font-semibold text-white">{getTitle(pathname)}</h1>
      {user && (
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-600 text-xs font-semibold text-white">
          {getInitials(user.full_name || user.email)}
        </div>
      )}
    </header>
  );
}
