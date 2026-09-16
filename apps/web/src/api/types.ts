export interface GoalInput {
  title: string;
  description: string;
  starting_level: string;
  target_date: string;
  minutes_per_day: number;
  study_days: number[];
  preferred_formats: string[];
}
export interface Goal extends GoalInput {
  id: string;
  status?: string;
  plan_id?: string | null;
  active_plan_id?: string | null;
  job_id?: string | null;
}
export interface Concept {
  id: string;
  title: string;
  description?: string;
  prerequisite_ids: string[];
  estimated_minutes?: number;
  mastery_state?: string;
  external_key?: string;
  prerequisite_keys?: string[];
}
export interface LessonSummary {
  id: string;
  title: string;
  estimated_minutes?: number;
  scheduled_date?: string;
  completed_at?: string | null;
  status?: string;
  sequence_number?: number;
  concept_ids?: string[];
}
export interface Plan {
  id: string;
  lessons: LessonSummary[];
  warnings?: string[];
}
export interface Resource {
  title: string;
  url: string;
  type?: string;
}
export interface Lesson extends LessonSummary {
  goal_id?: string;
  objective?: string;
  explanation?: string;
  practice_task?: string;
  resources?: Resource[];
  resource?: Resource;
  citations?: Resource[];
  activities?: {
    activity_type: string;
    title: string;
    instructions: string;
    estimated_minutes?: number;
  }[];
}
export interface Question {
  id: string;
  prompt: string;
  question_type?: string;
  options_json?: (string | { id: string; text: string })[];
  options?: (string | { id: string; text: string })[];
}
export interface Assessment {
  passing_score?: number;
  id: string;
  questions: Question[];
  attempts?: Attempt[];
}
export interface Attempt {
  passed?: boolean;
  id: string;
  assessment_id?: string;
  title?: string;
  score?: number;
  created_at?: string;
  feedback?: string;
  explanations?: Record<string, string>;
  per_question?: Record<string, boolean>;
}
export interface MasteryRecord {
  concept_id: string;
  mastery_score?: number;
  mastery_state: string;
}
export interface Mastery {
  concepts: MasteryRecord[];
  assessment_history?: Attempt[];
}
export interface Analytics {
  score_trend: { date: string; score: number; concept_id?: string }[];
  mastery_progress: { date: string; mastered_count: number }[];
  time_spent_by_day: { date: string; minutes: number }[];
}
export interface Credential {
  id?: string;
  provider: string;
  masked_label: string;
  validated?: boolean;
  validation_status?: string;
  is_active_provider?: boolean;
  base_url?: string;
}
export interface Job {
  id?: string;
  job_id?: string;
  status: "queued" | "running" | "completed" | "failed";
  error?: string;
  plan_id?: string;
}
