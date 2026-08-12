import { api } from "../api";
import { ErrorState } from "../components/ErrorState";
import { LineChart } from "../components/LineChart";
import { LoadingState } from "../components/LoadingState";
import { useApiData } from "../useApiData";

export function MentalMathPage() {
  const state = useApiData(api.mentalMathStats);

  return (
    <div className="page">
      <h1 className="page-title">Быстрый счёт</h1>

      {state.status === "loading" && <LoadingState />}
      {state.status === "error" && <ErrorState message={state.message} />}

      {state.status === "ok" && (
        <>
          <div className="stat-grid">
            <div className="stat-tile">
              <div className="stat-tile-value">🔥 {state.data.best_streak}</div>
              <div className="stat-tile-label">лучшая серия</div>
            </div>
            <div className="stat-tile">
              <div className="stat-tile-value">
                {state.data.total_attempts
                  ? Math.round((state.data.total_correct / state.data.total_attempts) * 100)
                  : 0}
                %
              </div>
              <div className="stat-tile-label">
                точность ({state.data.total_correct}/{state.data.total_attempts})
              </div>
            </div>
          </div>

          <div className="section-title">Точность за 14 дней</div>
          <div className="card">
            <LineChart
              points={state.data.daily.map((d) => ({
                label: d.date.slice(5),
                value: d.pct,
              }))}
              formatValue={(v) => `${Math.round(v)}%`}
            />
          </div>
        </>
      )}
    </div>
  );
}
