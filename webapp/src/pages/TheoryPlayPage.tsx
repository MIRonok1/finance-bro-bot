import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import {
  ApiError,
  api,
  type QuizAnswerResult,
  type QuizSessionResponse,
} from "../api";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { getTelegramWebApp, haptic } from "../telegram";

type LoadStatus = "loading" | "error" | "paywall" | "ready";
type Phase = "answering" | "rating" | "answered";

const RATE_OPTIONS: Array<{ value: "correct" | "partial" | "incorrect"; label: string }> = [
  { value: "correct", label: "✅ Верно" },
  { value: "partial", label: "🟡 Частично" },
  { value: "incorrect", label: "❌ Неверно" },
];

export function TheoryPlayPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();

  const [status, setStatus] = useState<LoadStatus>("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const [session, setSession] = useState<QuizSessionResponse | null>(null);

  const [phase, setPhase] = useState<Phase>("answering");
  const [feedback, setFeedback] = useState<QuizAnswerResult | null>(null);
  const [numericInput, setNumericInput] = useState("");
  const [openInput, setOpenInput] = useState("");

  // Кнопка "Назад" Telegram вместо своей — нативнее внутри клиента.
  useEffect(() => {
    const tg = getTelegramWebApp();
    const onBack = () => navigate("/theory");
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
        let data: QuizSessionResponse;
        if (sessionId) {
          data = await api.getQuizSession(sessionId);
        } else if (params.get("mode") === "review") {
          data = await api.startQuizSession({ mode: "review" });
        } else {
          const topicId = Number(params.get("topic"));
          const difficultyRaw = params.get("difficulty");
          data = await api.startQuizSession({
            topic_id: topicId,
            difficulty: difficultyRaw ? Number(difficultyRaw) : null,
          });
        }
        if (cancelled) return;

        setSession(data);
        setPhase("answering");
        setFeedback(null);
        setNumericInput("");
        setOpenInput("");
        setStatus("ready");

        if (!sessionId) {
          setParams(
            (prev) => {
              const next = new URLSearchParams(prev);
              next.set("session", data.session_id);
              return next;
            },
            { replace: true },
          );
        }
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 402) {
          setStatus("paywall");
        } else if (err instanceof ApiError && err.status === 404) {
          setErrorMessage(
            "По этой теме и сложности пока нет вопросов — попробуй другую комбинацию.",
          );
          setStatus("error");
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
    // Стартуем/резюмируем один раз при монтировании — реагировать на смену
    // query-параметров не нужно, мы сами их обновляем после старта.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submitMcq(chosenKey: string) {
    if (!session?.session_id) return;
    haptic("light");
    const result = await api.answerQuizQuestion(session.session_id, { chosen_key: chosenKey });
    setFeedback(result);
    setPhase("answered");
    haptic(result.is_correct ? "medium" : "heavy");
  }

  async function submitNumeric() {
    if (!session?.session_id || !numericInput.trim()) return;
    try {
      const result = await api.answerQuizQuestion(session.session_id, { answer: numericInput });
      setFeedback(result);
      setPhase("answered");
      haptic(result.is_correct ? "medium" : "heavy");
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setErrorMessage("Не смог распознать число — попробуй ещё раз.");
      } else {
        throw err;
      }
    }
  }

  async function submitOpen() {
    if (!session?.session_id || !openInput.trim()) return;
    const result = await api.answerQuizQuestion(session.session_id, { answer: openInput });
    setFeedback(result);
    setPhase("rating");
  }

  async function rateOpen(rating: "correct" | "partial" | "incorrect") {
    if (!session?.session_id) return;
    const result = await api.rateQuizOpenAnswer(session.session_id, rating);
    setFeedback((prev) => (prev ? { ...prev, is_correct: result.is_correct } : prev));
    setPhase("answered");
    haptic(result.is_correct ? "medium" : "heavy");
  }

  async function goNext() {
    if (!session?.session_id) return;
    const data = await api.nextQuizQuestion(session.session_id);
    setSession(data);
    setPhase("answering");
    setFeedback(null);
    setNumericInput("");
    setOpenInput("");
    setErrorMessage("");
  }

  return (
    <div className="page">
      <h1 className="page-title">Теория и кейсы</h1>

      {status === "loading" && <LoadingState />}

      {status === "paywall" && (
        <div className="state-block">
          Бесплатный лимит сессий на сегодня исчерпан. Оформи подписку: команда /subscribe в чате
          бота.
        </div>
      )}

      {status === "error" && <ErrorState message={errorMessage} />}

      {status === "ready" && session && session.status === "done" && (
        <div className="card">
          <div className="row-label" style={{ fontSize: 17, marginBottom: 4 }}>
            Сессия завершена
          </div>
          <div className="row-sub">
            Верно {session.correct_count}/{session.total}
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
            <button className="row" style={{ flex: 1 }} onClick={() => navigate("/theory")}>
              <span className="row-label">⬅️ К темам</span>
            </button>
          </div>
        </div>
      )}

      {status === "ready" && session?.question && (
        <>
          <div className="row-sub" style={{ marginBottom: 8 }}>
            Вопрос {(session.index ?? 0) + 1}/{session.total} · сложность{" "}
            {session.question.difficulty}
          </div>
          <div className="card" style={{ marginBottom: 16 }}>
            {session.question.body}
          </div>

          {phase === "answering" && session.question.type === "mcq" && (
            <>
              {session.question.options?.map((opt) => (
                <button
                  key={opt.key}
                  className="row"
                  style={{ textAlign: "left" }}
                  onClick={() => submitMcq(opt.key)}
                >
                  <span className="row-label">
                    {opt.key}. {opt.text}
                  </span>
                </button>
              ))}
            </>
          )}

          {phase === "answering" && session.question.type === "numeric" && (
            <div className="card">
              <input
                type="text"
                inputMode="decimal"
                value={numericInput}
                onChange={(e) => setNumericInput(e.target.value)}
                placeholder="Например: 1.5, 1 500 000, 1.5 млрд"
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
              <button className="row" onClick={submitNumeric}>
                <span className="row-label">Ответить</span>
              </button>
            </div>
          )}

          {phase === "answering" && session.question.type === "open" && (
            <div className="card">
              <textarea
                value={openInput}
                onChange={(e) => setOpenInput(e.target.value)}
                placeholder="Напиши свой ответ текстом"
                rows={4}
                style={{
                  width: "100%",
                  fontSize: 15,
                  padding: 10,
                  border: "1px solid var(--border)",
                  borderRadius: "var(--radius-sm)",
                  background: "var(--bg)",
                  color: "var(--fg)",
                  marginBottom: 10,
                  resize: "vertical",
                }}
              />
              <button className="row" onClick={submitOpen}>
                <span className="row-label">Показать разбор</span>
              </button>
            </div>
          )}

          {phase === "rating" && feedback && (
            <div className="card">
              <div className="section-title" style={{ marginTop: 0 }}>
                Разбор
              </div>
              <div style={{ marginBottom: 12 }}>{feedback.explanation}</div>
              <div className="row-sub" style={{ marginBottom: 8 }}>
                Как оцениваешь свой ответ?
              </div>
              {RATE_OPTIONS.map((opt) => (
                <button key={opt.value} className="row" onClick={() => rateOpen(opt.value)}>
                  <span className="row-label">{opt.label}</span>
                </button>
              ))}
            </div>
          )}

          {phase === "answered" && feedback && (
            <div className="card">
              <div className="row-label" style={{ marginBottom: 4 }}>
                {feedback.is_correct ? "✅ Верно!" : "❌ Неверно"}
              </div>
              {feedback.correct_key && (
                <div className="row-sub">Правильный вариант: {feedback.correct_key}</div>
              )}
              {feedback.correct_answer && (
                <div className="row-sub">Правильный ответ: {feedback.correct_answer}</div>
              )}
              <div style={{ margin: "10px 0" }}>{feedback.explanation}</div>
              <button className="row" onClick={goNext}>
                <span className="row-label">Далее ➡️</span>
              </button>
            </div>
          )}

          {errorMessage && phase === "answering" && (
            <div className="row-sub" style={{ marginTop: 8 }}>
              {errorMessage}
            </div>
          )}
        </>
      )}
    </div>
  );
}
