import { useNavigate } from "react-router-dom";

import { api } from "../api";
import { ErrorState } from "../components/ErrorState";
import { LineChart } from "../components/LineChart";
import { LoadingState } from "../components/LoadingState";
import { useApiData } from "../useApiData";

const DIFFICULTIES = [1, 2, 3, 4, 5];

export function MentalMathPage() {
  const state = useApiData(api.mentalMathStats);
  const navigate = useNavigate();

  return (
    <div className="page">
      <h1 className="page-title">Быстрый счёт</h1>

      {state.status === "loading" && <LoadingState />}
      {state.status === "error" && <ErrorState message={state.message} />}

      {state.status === "ok" && (
        <>
          <div className="section-title">Начать</div>
          <div className="card" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {DIFFICULTIES.map((d) => (
              <button
                key={d}
                className="row"
                style={{ flex: "1 0 30%", justifyContent: "center" }}
                onClick={() => navigate(`/mental-math/play?difficulty=${d}`)}
              >
                <span className="row-label">{d}</span>
              </button>
            ))}
          </div>

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
