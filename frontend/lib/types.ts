export interface User {
  id: number;
  email: string;
  full_name: string;
  created_at: string;
}

export interface SkillsDict {
  languages: string[];
  frameworks: string[];
  tools: string[];
  concepts: string[];
  other: string[];
}

export interface Resume {
  id: number;
  user_id: number;
  parsed_skills: SkillsDict;
  word_count: number;
  skill_count: number;
  uploaded_at: string;
}

export type ApplicationStatus =
  | "saved"
  | "applied"
  | "phone_screen"
  | "interview"
  | "offer"
  | "rejected"
  | "withdrawn";

export interface Application {
  id: number;
  user_id: number;
  company_name: string;
  job_title: string;
  status: ApplicationStatus;
  fit_score_pct: number | null;
  fit_label: string | null;
  applied_date: string | null;
  job_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationDetail extends Application {
  job_description: string;
  jd_skills: SkillsDict | null;
  matched_skills: string[] | null;
  missing_skills: string[] | null;
  semantic_score: number | null;
  skill_overlap_score: number | null;
  notes: string | null;
  analysis_status: "pending" | "complete";
}

export interface SuggestionItem {
  category: string;
  priority: string;
  suggestion: string;
  example: string;
}

export interface AnalyticsSummary {
  total_applications: number;
  by_status: Record<string, number>;
  avg_fit_score_pct: number | null;
  highest_fit_score_pct: number | null;
  analyzed_count: number;
  pending_count: number;
  weekly_applications: { week: string; count: number }[];
  top_missing_skills: { skill: string; count: number }[];
  interview_rate: number;
  offer_rate: number;
}
