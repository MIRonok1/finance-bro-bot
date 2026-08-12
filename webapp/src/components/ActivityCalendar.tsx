import type { ActivityDay } from "../api";

interface ActivityCalendarProps {
  days: ActivityDay[];
}

/** Duolingo-style календарь активности — сетка последних 4 недель.
 * Монохромно, как весь остальной дизайн: залитая ячейка = был активен в
 * этот день, контурная = нет. Никакого цвета для "стрика", только заливка
 * (см. global.css: направление P&L тоже показываем глифом, не цветом). */
export function ActivityCalendar({ days }: ActivityCalendarProps) {
  return (
    <div className="activity-grid">
      {days.map((day) => (
        <div
          key={day.date}
          className={day.active ? "activity-cell activity-cell-active" : "activity-cell"}
          title={day.date}
        />
      ))}
    </div>
  );
}
