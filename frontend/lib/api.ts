// Central API client — all backend calls go through here.
// WHY: keeps the backend URL in one place; every fetch automatically
//      attaches the Authorization header when a token is stored.

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    if (res.status === 401) {
      localStorage.removeItem("access_token");
      window.location.href = "/login";
      throw new Error("Session expired");
    }
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `HTTP ${res.status}`);
  }

  // 204 No Content has no body
  if (res.status === 204) return undefined as T;

  return res.json();
}

// ---------- Auth ----------

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
}

export async function register(
  email: string,
  password: string,
  full_name?: string
): Promise<UserResponse> {
  return request<UserResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name }),
  });
}

export async function login(
  email: string,
  password: string
): Promise<TokenResponse> {
  return request<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

// ---------- Applications ----------

export type ApplicationStatus =
  | "applied"
  | "screening"
  | "interviewing"
  | "offer"
  | "rejected"
  | "withdrawn";

export interface Application {
  id: number;
  user_id: number;
  company_name: string;
  job_title: string;
  job_description: string | null;
  job_url: string | null;
  location: string | null;
  is_remote: boolean;
  status: ApplicationStatus;
  application_date: string | null;
  salary_min: number | null;
  salary_max: number | null;
}

export async function getApplications(): Promise<Application[]> {
  return request<Application[]>("/applications");
}

export async function createApplication(
  data: Omit<Application, "id" | "user_id">
): Promise<Application> {
  return request<Application>("/applications", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateApplication(
  id: number,
  data: Partial<Omit<Application, "id" | "user_id">>
): Promise<Application> {
  return request<Application>(`/applications/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteApplication(id: number): Promise<void> {
  return request<void>(`/applications/${id}`, { method: "DELETE" });
}
