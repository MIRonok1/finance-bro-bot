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

async function request<T>(path: string): Promise<T> {
  const initData = getInitData();
  const res = await fetch(path, {
    headers: initData ? { Authorization: `tma ${initData}` } : {},
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.error ?? `HTTP ${res.status}`);
  }
  return (await res.json()) as T;
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

export const api = {
  me: () => request<MeResponse>("/api/me"),
  quizStats: () => request<QuizStatsResponse>("/api/quiz/stats"),
  mentalMathStats: () => request<MentalMathStatsResponse>("/api/mental_math/stats"),
  portfolio: () => request<PortfolioResponse>("/api/portfolio"),
  portfolioHistory: () => request<PortfolioHistoryResponse>("/api/portfolio/history"),
};
