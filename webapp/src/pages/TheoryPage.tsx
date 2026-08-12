import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { useApiData } from "../useApiData";

export function TheoryPage() {
  const stats = useApiData(api.quizStats);
  const topics = useApiData(api.quizTopics);
  const navigate = useNavigate();

  return (
    <div className="page">
      <h1 className="page-title">Теория и кейсы</h1>

      {stats.status === "loading" && <LoadingState />}
      {stats.status === "error" && <ErrorState message={stats.message} />}

      {stats.status === "ok" && (
        <>
          {stats.data.due_review > 0 && (
            <button
              className="row"
              style={{ marginBottom: 20, width: "100%" }}
              onClick={() => navigate("/theory/play?mode=review")}
            >
              <div className="row-main">
                <div className="row-label">🔁 На повторение</div>
                <div className="row-sub">{stats.data.due_review} вопрос(ов) готовы — начать</div>
              </div>
            </button>
          )}

          <div className="section-title">Начать сессию</div>
          {topics.status === "ok" &&
            topics.data.topics.map((t) => (
              <button
                key={t.id}
                className="row"
                style={{ width: "100%" }}
                onClick={() => navigate(`/theory/play?topic=${t.id}`)}
              >
                <span className="row-label">{t.title}</span>
                <span className="row-chevron">›</span>
              </button>
            ))}

          <div className="section-title">Прогресс по темам</div>
          {stats.data.topics.length === 0 && (
            <div className="state-block">Пока нет попыток — начни сессию выше.</div>
          )}
          {stats.data.topics.map((t) => (
            <div className="row" key={t.title} style={{ cursor: "default" }}>
              <div className="row-main" style={{ width: "100%" }}>
                <div className="row-label">
                  {t.title}
                  {t.weak && " ⚠️"}
                </div>
                <div className="row-sub">
                  {t.correct}/{t.total} верно
                </div>
                <div className="progress">
                  <div className="progress-fill" style={{ width: `${t.pct}%` }} />
                </div>
              </div>
              <div className="row-value">{t.pct}%</div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
