import { api } from "../api";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { useApiData } from "../useApiData";

export function TheoryPage() {
  const state = useApiData(api.quizStats);

  return (
    <div className="page">
      <h1 className="page-title">Теория и кейсы</h1>

      {state.status === "loading" && <LoadingState />}
      {state.status === "error" && <ErrorState message={state.message} />}

      {state.status === "ok" && (
        <>
          {state.data.due_review > 0 && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div className="row-label">🔁 На повторение</div>
              <div className="row-sub">
                {state.data.due_review} вопрос(ов) готовы к повторению — открой бота и нажми
                «Начать повторение» в /stats.
              </div>
            </div>
          )}

          <div className="section-title">Темы</div>
          {state.data.topics.length === 0 && (
            <div className="state-block">
              Пока нет попыток — начни сессию в чате бота, чтобы увидеть статистику здесь.
            </div>
          )}
          {state.data.topics.map((t) => (
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
