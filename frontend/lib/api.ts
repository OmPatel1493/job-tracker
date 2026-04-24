import axios from "axios";
import type {
  AnalyticsSummary,
  Application,
  ApplicationDetail,
  Resume,
  SuggestionItem,
  User,
} from "@/lib/types";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

// Attach token from localStorage on every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// On 401: clear storage and redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && typeof window !== "undefined") {
      localStorage.clear();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ---------- Auth ----------

export const login = (email: string, password: string) =>
  api.post<{ access_token: string; token_type: string }>("/auth/login", {
    email,
    password,
  });

export const register = (email: string, password: string, full_name: string) =>
  api.post<User>("/auth/register", { email, password, full_name });

export const getMe = () => api.get<User>("/auth/me");

// ---------- Resume ----------

export const uploadResume = (formData: FormData) =>
  api.post<Resume>("/resume/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

export const getResume = () => api.get<Resume>("/resume/me");

export const deleteResume = () => api.delete("/resume/me");

// ---------- Applications ----------

export const getApplications = (params?: {
  status?: string;
  search?: string;
  sort_by?: string;
  order?: string;
  limit?: number;
  offset?: number;
}) =>
  api.get<{ items: Application[]; total: number; limit: number; offset: number }>(
    "/applications",
    { params }
  );

export const getApplication = (id: number) =>
  api.get<ApplicationDetail>(`/applications/${id}`);

export const createApplication = (data: {
  company_name: string;
  job_title: string;
  job_description: string;
  notes?: string;
  applied_date?: string;
  job_url?: string;
  status?: string;
}) => api.post<Application>("/applications", data);

export const updateStatus = (id: number, status: string, notes?: string) =>
  api.patch<Application>(`/applications/${id}/status`, { status, notes });

export const updateNotes = (id: number, notes: string) =>
  api.patch<ApplicationDetail>(`/applications/${id}/notes`, { notes });

export const deleteApplication = (id: number) =>
  api.delete(`/applications/${id}`);

export const reanalyzeApplication = (id: number) =>
  api.post(`/applications/${id}/reanalyze`);

// ---------- Suggestions ----------

export const generateSuggestions = (application_id: number) =>
  api.post<{ id: number; application_id: number; suggestions: SuggestionItem[]; generated_at: string }>(
    `/suggestions/${application_id}/generate`
  );

export const getSuggestions = (application_id: number) =>
  api.get<{ id: number; application_id: number; suggestions: SuggestionItem[]; generated_at: string }>(
    `/suggestions/${application_id}`
  );

// ---------- Analytics ----------

export const getAnalyticsSummary = () =>
  api.get<AnalyticsSummary>("/analytics/summary");

export default api;
