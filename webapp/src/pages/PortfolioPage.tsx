import { useEffect, useRef, useState } from "react";

import { api } from "../api";
import { Direction } from "../components/Direction";
import { ErrorState } from "../components/ErrorState";
import { LineChart } from "../components/LineChart";
import { LoadingState } from "../components/LoadingState";
import { getInitData } from "../telegram";
import { useApiData } from "../useApiData";

interface LivePrice {
  price_rub: string;
  tick: number; // меняется на каждое обновление — триггерит CSS-анимацию пульса заново
}

/** wss://.../api/portfolio/ws?initData=... — тот же origin, что и остальной
 * Mini App. initData едет query-параметром, а не заголовком: браузерный
 * WebSocket не умеет ставить кастомные заголовки на handshake (см.
 * app/webapp/server.py). */
function portfolioWsUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/api/portfolio/ws?initData=${encodeURIComponent(
    getInitData(),
  )}`;
}

/** Живые цены по холдингам через WebSocket (Фаза 4) — только отображение
 * текущей цены + "пульс"-индикатор; P&L/equity остаются серверным расчётом
 * из /api/portfolio (см. план: не дублировать денежную арифметику на
 * фронте, тут только визуальный "живой" эффект). */
function useLivePrices(): Record<string, LivePrice> {
  const [prices, setPrices] = useState<Record<string, LivePrice>>({});
  const tickRef = useRef(0);

  useEffect(() => {
    if (!getInitData()) return; // вне Telegram-клиента (например, локальный тест) — не подключаемся

    const ws = new WebSocket(portfolioWsUrl());
    ws.onmessage = (event) => {
      let msg: { type?: string; ticker?: string; price_rub?: string };
      try {
        msg = JSON.parse(event.data as string);
      } catch {
        return;
      }
      if (msg.type !== "price" || !msg.ticker || !msg.price_rub) return;
      tickRef.current += 1;
      setPrices((prev) => ({
        ...prev,
        [msg.ticker as string]: { price_rub: msg.price_rub as string, tick: tickRef.current },
      }));
    };

    return () => ws.close();
  }, []);

  return prices;
}

export function PortfolioPage() {
  const dashboard = useApiData(api.portfolio);
  const history = useApiData(api.portfolioHistory);
  const livePrices = useLivePrices();

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
          {dashboard.data.holdings.map((h) => {
            const live = livePrices[h.ticker];
            const priceRub = live?.price_rub ?? h.price_rub;
            return (
              <div className="row" key={h.ticker} style={{ cursor: "default" }}>
                <div className="row-main">
                  <div className="row-label">
                    {h.ticker}
                    {live && <span key={live.tick} className="live-pulse" />}
                  </div>
                  <div className="row-sub">
                    {h.quantity} шт. · сред. {h.avg_price_rub} ₽ · тек. {priceRub} ₽
                  </div>
                </div>
                <Direction value={Number(h.pnl_rub)}>
                  <span className="row-value">{h.pnl_rub} ₽</span>
                </Direction>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}
