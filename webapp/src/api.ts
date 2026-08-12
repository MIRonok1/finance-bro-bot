// Клиент JSON API бэкенда (app/webapp/api.py). Тот же origin, что и сам
// Mini App (сервер раздаёт и статику, и /api/*) — CORS не нужен.

import { getInitData } from "./telegram";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const initData = getInitData();
  const res = await fetch(path, {
    ...init,
    headers: {
      ...(initData ? { Authorization: `tma ${initData}` } : {}),
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.error ?? `HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

// Первый POST в этом клиенте (Фаза 4, интерактивные мини-игры) — до этого
// все запросы были read-only GET. Тело — всегда JSON или отсутствует.
function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined });
}

export interface MeResponse {
  telegram_id: number;
  first_name: string;
  last_name: string | null;
  username: string | null;
  photo_url: string | null;
  member_since: string | null;
  daily_streak: number;
  is_admin: boolean;
  subscription: { active: boolean; plan: string | null };
}

export interface QuizTopicStat {
  title: string;
  total: number;
  correct: number;
  pct: number;
  weak: boolean;
}

export interface QuizStatsResponse {
  topics: QuizTopicStat[];
  due_review: number;
}

export interface MentalMathDailyPoint {
  date: string;
  total: number;
  correct: number;
  pct: number;
}

export interface MentalMathStatsResponse {
  best_streak: number;
  total_attempts: number;
  total_correct: number;
  daily: MentalMathDailyPoint[];
}

export interface PortfolioHolding {
  ticker: string;
  quantity: number;
  avg_price_rub: string;
  price_rub: string;
  pnl_rub: string;
}

export interface PortfolioResponse {
  cash_rub: string;
  equity_rub: string;
  daily_pnl_rub: string;
  daily_pnl_pct: string;
  imoex_daily_pct: string | null;
  holdings: PortfolioHolding[];
}

export interface PortfolioHistoryPoint {
  date: string;
  equity_rub: number;
}

export interface PortfolioHistoryResponse {
  history: PortfolioHistoryPoint[];
}

export interface ActivityDay {
  date: string;
  active: boolean;
}

export interface ActivityResponse {
  streak: number;
  days: ActivityDay[];
}

// --- Квиз: интерактивная сессия (Фаза 4) ---

export interface QuizTopic {
  id: number;
  slug: string;
  title: string;
}

export interface QuizTopicsResponse {
  topics: QuizTopic[];
}

export interface QuizQuestionOption {
  key: string;
  text: string;
}

export interface QuizQuestion {
  id: number;
  topic_id: number;
  type: "mcq" | "numeric" | "open";
  difficulty: number;
  body: string;
  options?: QuizQuestionOption[];
}

export interface QuizSessionResponse {
  session_id: string;
  status: "in_progress" | "done";
  total: number;
  index?: number;
  correct_count: number;
  question: QuizQuestion | null;
}

export type QuizAnswerBody = { chosen_key: string } | { answer: string };

export interface QuizAnswerResult {
  is_correct?: boolean; // отсутствует для open-вопроса до /rate
  correct_key?: string;
  correct_answer?: string;
  explanation: string;
}

export interface QuizRateResult {
  is_correct: boolean;
}

// --- Устный счёт: интерактивная сессия (Фаза 4) ---

export interface MentalMathTask {
  kind: string;
  prompt: string;
}

export interface MentalMathStartResponse {
  session_id: string;
  difficulty: number;
  task: MentalMathTask;
  streak: number;
  total: number;
  correct: number;
}

export interface MentalMathSessionSummary {
  session_id: string;
  status: "in_progress" | "done";
  difficulty: number;
  streak: number;
  session_best_streak: number;
  total: number;
  correct: number;
  task: MentalMathTask | null;
}

export interface MentalMathAnswerResult {
  is_correct: boolean;
  correct_answer: string;
  explanation: string;
  elapsed_ms: number;
  streak: number;
  session_best_streak: number;
  total: number;
  correct: number;
  best_streak_alltime: number;
  checkpoint: boolean;
}

export interface MentalMathFinishResult {
  total: number;
  correct: number;
  pct: number;
  session_best_streak: number;
}

export const api = {
  me: () => request<MeResponse>("/api/me"),
  quizStats: () => request<QuizStatsResponse>("/api/quiz/stats"),
  mentalMathStats: () => request<MentalMathStatsResponse>("/api/mental_math/stats"),
  portfolio: () => request<PortfolioResponse>("/api/portfolio"),
  portfolioHistory: () => request<PortfolioHistoryResponse>("/api/portfolio/history"),
  activity: () => request<ActivityResponse>("/api/activity"),

  quizTopics: () => request<QuizTopicsResponse>("/api/quiz/topics"),
  startQuizSession: (body: { topic_id?: number; difficulty?: number | null; mode?: "review" }) =>
    post<QuizSessionResponse>("/api/quiz/sessions", body),
  getQuizSession: (id: string) => request<QuizSessionResponse>(`/api/quiz/sessions/${id}`),
  answerQuizQuestion: (id: string, body: QuizAnswerBody) =>
    post<QuizAnswerResult>(`/api/quiz/sessions/${id}/answer`, body),
  rateQuizOpenAnswer: (id: string, rating: "correct" | "partial" | "incorrect") =>
    post<QuizRateResult>(`/api/quiz/sessions/${id}/rate`, { rating }),
  nextQuizQuestion: (id: string) => post<QuizSessionResponse>(`/api/quiz/sessions/${id}/next`),

  startMentalMathSession: (difficulty: number) =>
    post<MentalMathStartResponse>("/api/mental_math/sessions", { difficulty }),
  getMentalMathSession: (id: string) =>
    request<MentalMathSessionSummary>(`/api/mental_math/sessions/${id}`),
  answerMentalMathTask: (id: string, answer: string) =>
    post<MentalMathAnswerResult>(`/api/mental_math/sessions/${id}/answer`, { answer }),
  nextMentalMathTask: (id: string) =>
    post<{ task: MentalMathTask }>(`/api/mental_math/sessions/${id}/next`),
  finishMentalMathSession: (id: string) =>
    post<MentalMathFinishResult>(`/api/mental_math/sessions/${id}/finish`),
};
