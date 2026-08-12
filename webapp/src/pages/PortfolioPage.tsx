import { api } from "../api";
import { Direction } from "../components/Direction";
import { ErrorState } from "../components/ErrorState";
import { LineChart } from "../components/LineChart";
import { LoadingState } from "../components/LoadingState";
import { useApiData } from "../useApiData";

export function PortfolioPage() {
  const dashboard = useApiData(api.portfolio);
  const history = useApiData(api.portfolioHistory);

  return (
    <div className="page">
      <h1 className="page-title">Портфель</h1>

      {dashboard.status === "loading" && <LoadingState />}
      {dashboard.status === "error" && <ErrorState message={dashboard.message} />}

      {dashboard.status === "ok" && (
        <>
          <div className="stat-grid">
            <div className="stat-tile">
              <div className="stat-tile-value">{dashboard.data.equity_rub} ₽</div>
              <div className="stat-tile-label">стоимость портфеля</div>
            </div>
            <div className="stat-tile">
              <div className="stat-tile-value">{dashboard.data.cash_rub} ₽</div>
              <div className="stat-tile-label">свободные деньги</div>
            </div>
            <div className="stat-tile">
              <Direction value={Number(dashboard.data.daily_pnl_pct)}>
                <span className="stat-tile-value">{dashboard.data.daily_pnl_pct}%</span>
              </Direction>
              <div className="stat-tile-label">P&amp;L за день ({dashboard.data.daily_pnl_rub} ₽)</div>
            </div>
            <div className="stat-tile">
              {dashboard.data.imoex_daily_pct !== null ? (
                <Direction value={Number(dashboard.data.imoex_daily_pct)}>
                  <span className="stat-tile-value">{dashboard.data.imoex_daily_pct}%</span>
                </Direction>
              ) : (
                <span className="stat-tile-value">—</span>
              )}
              <div className="stat-tile-label">IMOEX за день</div>
            </div>
          </div>

          <div className="section-title">Equity, 30 дней</div>
          <div className="card">
            {history.status === "loading" && <LoadingState />}
            {history.status === "error" && <ErrorState message={history.message} />}
            {history.status === "ok" && (
              <LineChart
                points={history.data.history.map((h) => ({
                  label: h.date.slice(5),
                  value: h.equity_rub,
                }))}
                formatValue={(v) => `${Math.round(v).toLocaleString("ru-RU")} ₽`}
              />
            )}
          </div>

          <div className="section-title">Позиции</div>
          {dashboard.data.holdings.length === 0 && (
            <div className="state-block">
              Пока нет позиций — купить акции можно в чате бота, кнопка «Купить» в разделе
              «Портфель».
            </div>
          )}
          {dashboard.data.holdings.map((h) => (
            <div className="row" key={h.ticker} style={{ cursor: "default" }}>
              <div className="row-main">
                <div className="row-label">{h.ticker}</div>
                <div className="row-sub">
                  {h.quantity} шт. · сред. {h.avg_price_rub} ₽ · тек. {h.price_rub} ₽
                </div>
              </div>
              <Direction value={Number(h.pnl_rub)}>
                <span className="row-value">{h.pnl_rub} ₽</span>
              </Direction>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
