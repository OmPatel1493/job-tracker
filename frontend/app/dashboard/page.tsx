"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getApplications, type Application } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

// Status badge colours
const STATUS_STYLES: Record<Application["status"], string> = {
  applied: "bg-blue-100 text-blue-700",
  screening: "bg-yellow-100 text-yellow-700",
  interviewing: "bg-purple-100 text-purple-700",
  offer: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
  withdrawn: "bg-gray-100 text-gray-600",
};

export default function DashboardPage() {
  const router = useRouter();
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // If no token exists, redirect to login immediately
    if (!localStorage.getItem("access_token")) {
      router.replace("/login");
      return;
    }

    getApplications()
      .then(setApplications)
      .catch((err) => {
        // 401 means the stored token has expired — force re-login
        if (err.message.includes("401") || err.message.toLowerCase().includes("unauthorized")) {
          localStorage.removeItem("access_token");
          router.replace("/login");
        } else {
          setError(err.message);
        }
      })
      .finally(() => setLoading(false));
  }, [router]);

  function handleLogout() {
    localStorage.removeItem("access_token");
    router.push("/login");
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Navbar */}
      <header className="border-b">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between">
          <h1 className="font-semibold text-lg">Job Tracker</h1>
          <Button variant="outline" size="sm" onClick={handleLogout}>
            Sign out
          </Button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8 space-y-6">
        {/* Stats row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {(["applied", "interviewing", "offer", "rejected"] as const).map(
            (status) => (
              <Card key={status}>
                <CardHeader className="pb-1">
                  <CardDescription className="capitalize">{status}</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-2xl font-bold">
                    {applications.filter((a) => a.status === status).length}
                  </p>
                </CardContent>
              </Card>
            )
          )}
        </div>

        {/* Application list */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Applications</CardTitle>
              {/* "Add" button — wired up in Day 7 */}
              <Button size="sm" disabled>
                + Add application
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {loading && (
              <p className="text-sm text-muted-foreground">Loading…</p>
            )}
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            {!loading && !error && applications.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No applications yet. Add your first one to get started.
              </p>
            )}
            {!loading && applications.length > 0 && (
              <ul className="divide-y">
                {applications.map((app) => (
                  <li key={app.id} className="py-3 flex items-start justify-between gap-4">
                    <div>
                      <p className="font-medium">{app.company_name}</p>
                      <p className="text-sm text-muted-foreground">{app.job_title}</p>
                      {app.location && (
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {app.location} {app.is_remote && "(Remote)"}
                        </p>
                      )}
                    </div>
                    <span
                      className={`text-xs font-medium px-2 py-0.5 rounded-full capitalize whitespace-nowrap ${STATUS_STYLES[app.status]}`}
                    >
                      {app.status}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
