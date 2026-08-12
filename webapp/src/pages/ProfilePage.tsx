import { api, type MeResponse } from "../api";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { useApiData } from "../useApiData";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  // Бэкенд отдаёт SQLite-datetime вида "2026-08-01 12:00:00" (UTC).
  const d = new Date(iso.replace(" ", "T") + "Z");
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
}

function initials(me: MeResponse): string {
  const source = me.first_name || me.username || "?";
  return source.slice(0, 1).toUpperCase();
}

export function ProfilePage() {
  const state = useApiData(api.me);

  return (
    <div className="page">
      <h1 className="page-title">Профиль</h1>

      {state.status === "loading" && <LoadingState />}
      {state.status === "error" && <ErrorState message={state.message} />}

      {state.status === "ok" && (
        <>
          <div className="card" style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div className="avatar">
              {state.data.photo_url ? (
                <img src={state.data.photo_url} alt="" />
              ) : (
                initials(state.data)
              )}
            </div>
            <div style={{ minWidth: 0 }}>
              <div className="row-label" style={{ fontSize: 17 }}>
                {state.data.first_name} {state.data.last_name ?? ""}
              </div>
              {state.data.username && (
                <div className="row-sub">@{state.data.username}</div>
              )}
              <div className="row-sub">С нами с {formatDate(state.data.member_since)}</div>
            </div>
          </div>

          <div className="section-title">Активность</div>
          <div className="stat-grid">
            <div className="stat-tile">
              <div className="stat-tile-value">🔥 {state.data.daily_streak}</div>
              <div className="stat-tile-label">дней подряд</div>
            </div>
            <div className="stat-tile">
              <div className="stat-tile-value">
                {state.data.subscription.active ? "Pro" : "Free"}
              </div>
              <div className="stat-tile-label">
                {state.data.subscription.active
                  ? `план ${state.data.subscription.plan ?? ""}`
                  : "тариф"}
              </div>
            </div>
          </div>

          <div className="section-title">Статус</div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <span className={state.data.subscription.active ? "badge" : "badge badge-muted"}>
              {state.data.subscription.active ? "Подписка активна" : "Без подписки"}
            </span>
            {state.data.is_admin && <span className="badge">Админ</span>}
          </div>
        </>
      )}
    </div>
  );
}
