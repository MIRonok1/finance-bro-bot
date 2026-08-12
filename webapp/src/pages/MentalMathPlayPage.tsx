import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import {
  ApiError,
  api,
  type MentalMathAnswerResult,
  type MentalMathTask,
} from "../api";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { getTelegramWebApp, haptic } from "../telegram";

type LoadStatus = "loading" | "error" | "paywall" | "ready";
type Phase = "answering" | "answered" | "checkpoint" | "finished";

// Те же пороги, что были в удалённом чат-хендлере устного счёта —
// сохраняем узнаваемость фидбека по скорости.
const FAST_THRESHOLD_S = 5;
const NORMAL_THRESHOLD_S = 15;

function speedLabel(elapsedMs: number): string {
  const s = elapsedMs / 1000;
  if (s < FAST_THRESHOLD_S) return `⚡ ${s.toFixed(1)} сек`;
  if (s < NORMAL_THRESHOLD_S) return `🙂 ${s.toFixed(1)} сек`;
  return `🐢 ${s.toFixed(1)} сек`;
}

interface LocalSession {
  sessionId: string;
  difficulty: number;
  task: MentalMathTask | null;
  streak: number;
  sessionBestStreak: number;
  total: number;
  correct: number;
}

export function MentalMathPlayPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();

  const [status, setStatus] = useState<LoadStatus>("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [session, setSession] = useState<LocalSession | null>(null);

  const [phase, setPhase] = useState<Phase>("answering");
  const [feedback, setFeedback] = useState<MentalMathAnswerResult | null>(null);
  const [answerInput, setAnswerInput] = useState("");
  const [finalSummary, setFinalSummary] = useState<{ total: number; correct: number; pct: number } | null>(
    null,
  );

  useEffect(() => {
    const tg = getTelegramWebApp();
    const onBack = () => navigate("/mental-math");
    tg?.BackButton.show();
    tg?.BackButton.onClick(onBack);
    return () => {
      tg?.BackButton.hide();
      tg?.BackButton.offClick(onBack);
    };
  }, [navigate]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setStatus("loading");
      try {
        const sessionId = params.get("session");
        if (sessionId) {
          const data = await api.getMentalMathSession(sessionId);
          if (cancelled) return;
          if (data.status === "done") {
            setFinalSummary({
              total: data.total,
              correct: data.correct,
              pct: data.total ? Math.round((data.correct / data.total) * 100) : 0,
            });
            setPhase("finished");
            setStatus("ready");
            return;
          }
          setSession({
            sessionId: data.session_id,
            difficulty: data.difficulty,
            task: data.task,
            streak: data.streak,
            sessionBestStreak: data.session_best_streak,
            total: data.total,
            correct: data.correct,
          });
        } else {
          const difficulty = Number(params.get("difficulty")) || 1;
          const data = await api.startMentalMathSession(difficulty);
          if (cancelled) return;
          setSession({
            sessionId: data.session_id,
            difficulty: data.difficulty,
            task: data.task,
            streak: data.streak,
            sessionBestStreak: data.streak,
            total: data.total,
            correct: data.correct,
          });
          setParams(
            (prev) => {
              const next = new URLSearchParams(prev);
              next.set("session", data.session_id);
              return next;
            },
            { replace: true },
          );
        }
        setPhase("answering");
        setFeedback(null);
        setAnswerInput("");
        setStatus("ready");
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 402) {
          setStatus("paywall");
        } else {
          setErrorMessage(err instanceof Error ? err.message : "Неизвестная ошибка");
          setStatus("error");
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submitAnswer() {
    if (!session || !answerInput.trim()) return;
    try {
      const result = await api.answerMentalMathTask(session.sessionId, answerInput);
      setFeedback(result);
      setSession((prev) =>
        prev
          ? {
              ...prev,
              streak: result.streak,
              sessionBestStreak: result.session_best_streak,
              total: result.total,
              correct: result.correct,
            }
          : prev,
      );
      setPhase(result.checkpoint ? "checkpoint" : "answered");
      haptic(result.is_correct ? "medium" : "heavy");
      setErrorMessage("");
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setErrorMessage("Не смог распознать число — попробуй ещё раз.");
      } else {
        throw err;
      }
    }
  }

  async function goNext() {
    if (!session) return;
    const { task } = await api.nextMentalMathTask(session.sessionId);
    setSession((prev) => (prev ? { ...prev, task } : prev));
    setPhase("answering");
    setFeedback(null);
    setAnswerInput("");
  }

  async function finish() {
    if (!session) return;
    const summary = await api.finishMentalMathSession(session.sessionId);
    setFinalSummary(summary);
    setPhase("finished");
  }

  return (
    <div className="page">
      <h1 className="page-title">Быстрый счёт</h1>

      {status === "loading" && <LoadingState />}

      {status === "paywall" && (
        <div className="state-block">
          Бесплатный лимит сессий на сегодня исчерпан. Оформи подписку: команда /subscribe в чате
          бота.
        </div>
      )}

      {status === "error" && <ErrorState message={errorMessage} />}

      {status === "ready" && phase === "finished" && finalSummary && (
        <div className="card">
          <div className="row-label" style={{ fontSize: 17, marginBottom: 4 }}>
            Готово!
          </div>
          <div className="row-sub">
            Всего {finalSummary.total}, верно {finalSummary.correct} ({finalSummary.pct}%)
          </div>
          <button
            className="row"
            style={{ marginTop: 16 }}
            onClick={() => navigate("/mental-math")}
          >
            <span className="row-label">⬅️ В меню</span>
          </button>
        </div>
      )}

      {status === "ready" && session && phase !== "finished" && (
        <>
          <div className="stat-grid" style={{ marginBottom: 16 }}>
            <div className="stat-tile">
              <div className="stat-tile-value">🔥 {session.streak}</div>
              <div className="stat-tile-label">серия</div>
            </div>
            <div className="stat-tile">
              <div className="stat-tile-value">{session.correct}</div>
              <div className="stat-tile-label">верно из {session.total}</div>
            </div>
          </div>

          {phase === "answering" && session.task && (
            <div className="card">
              <div style={{ marginBottom: 12, fontSize: 16 }}>{session.task.prompt}</div>
              <input
                type="text"
                inputMode="decimal"
                autoFocus
                value={answerInput}
                onChange={(e) => setAnswerInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submitAnswer()}
                placeholder="Твой ответ"
                style={{
                  width: "100%",
                  fontSize: 16,
                  padding: 10,
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--bg)",
                  color: "var(--fg)",
                  marginBottom: 10,
                }}
              />
              <button className="row" onClick={submitAnswer}>
                <span className="row-label">Ответить</span>
              </button>
              {errorMessage && (
                <div className="row-sub" style={{ marginTop: 8 }}>
                  {errorMessage}
                </div>
              )}
              <button
                className="row"
                style={{ marginTop: 8, background: "transparent" }}
                onClick={finish}
              >
                <span className="row-label">🛑 Завершить</span>
              </button>
            </div>
          )}

          {phase === "answered" && feedback && (
            <div className="card">
              <div className="row-label" style={{ marginBottom: 4 }}>
                {feedback.is_correct ? "✅ Верно!" : "❌ Неверно."}
              </div>
              {!feedback.is_correct && (
                <div className="row-sub">Правильный ответ: {feedback.correct_answer}</div>
              )}
              <div style={{ margin: "10px 0" }}>{feedback.explanation}</div>
              <div className="row-sub">{speedLabel(feedback.elapsed_ms)}</div>
              <button className="row" style={{ marginTop: 10 }} onClick={goNext}>
                <span className="row-label">Далее ➡️</span>
              </button>
            </div>
          )}

          {phase === "checkpoint" && feedback && (
            <div className="card">
              <div className="row-label" style={{ marginBottom: 4 }}>
                Пройдено {session.total}, верно {session.correct}
              </div>
              <div className="row-sub">Лучшая серия за всё время: {feedback.best_streak_alltime}</div>
              <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                <button className="row" style={{ flex: 1 }} onClick={goNext}>
                  <span className="row-label">▶️ Продолжить</span>
                </button>
                <button className="row" style={{ flex: 1 }} onClick={finish}>
                  <span className="row-label">🏁 Закончить</span>
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
