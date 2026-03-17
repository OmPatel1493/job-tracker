"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getApplications, deleteApplication, type Application } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import AddApplicationModal from "@/components/AddApplicationModal";
import EditApplicationModal from "@/components/EditApplicationModal";

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
    if (!localStorage.getItem("access_token")) {
      router.replace("/login");
      return;
    }

    getApplications()
      .then(setApplications)
      .catch((err) => {
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

  // Optimistic UI: add the new application to the top of the list instantly
  // without waiting for a full refetch.
  // WHY optimistic updates: the user sees immediate feedback; feels snappy.
  function handleCreated(app: Application) {
    setApplications((prev) => [app, ...prev]);
  }

  // Replace the old application object with the updated one in local state.
  function handleUpdated(updated: Application) {
    setApplications((prev) =>
      prev.map((a) => (a.id === updated.id ? updated : a))
    );
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this application?")) return;
    await deleteApplication(id);
    setApplications((prev) => prev.filter((a) => a.id !== id));
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
          {(["applied", "interviewing", "offer", "rejected"] as const).map((status) => (
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
          ))}
        </div>

        {/* Application list */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Applications ({applications.length})</CardTitle>
              <AddApplicationModal onCreated={handleCreated} />
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
                    <div className="min-w-0">
                      <p className="font-medium truncate">{app.company_name}</p>
                      <p className="text-sm text-muted-foreground truncate">{app.job_title}</p>
                      <div className="flex items-center gap-3 mt-0.5">
                        {app.location && (
                          <p className="text-xs text-muted-foreground">
                            {app.location} {app.is_remote && "(Remote)"}
                          </p>
                        )}
                        {(app.salary_min || app.salary_max) && (
                          <p className="text-xs text-muted-foreground">
                            ${app.salary_min?.toLocaleString() ?? "?"}
                            {app.salary_max ? ` – $${app.salary_max.toLocaleString()}` : "+"}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className={`text-xs font-medium px-2 py-0.5 rounded-full capitalize whitespace-nowrap ${STATUS_STYLES[app.status]}`}
                      >
                        {app.status}
                      </span>
                      <EditApplicationModal application={app} onUpdated={handleUpdated} />
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-xs text-destructive hover:text-destructive"
                        onClick={() => handleDelete(app.id)}
                      >
                        Delete
                      </Button>
                    </div>
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
