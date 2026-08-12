// Обёртка над window.Telegram.WebApp (официальный скрипт подключён в
// index.html). Типы — только то, чем реально пользуемся; полный набор
// полей Telegram WebApp API нам не нужен (см. CLAUDE.md про абстракции
// "на будущее").

export interface TelegramWebAppUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
}

export interface TelegramWebApp {
  initData: string;
  initDataUnsafe: { user?: TelegramWebAppUser };
  colorScheme: "light" | "dark";
  ready: () => void;
  expand: () => void;
  close: () => void;
  BackButton: {
    show: () => void;
    hide: () => void;
    onClick: (cb: () => void) => void;
    offClick: (cb: () => void) => void;
  };
  HapticFeedback?: {
    impactOccurred: (style: "light" | "medium" | "heavy") => void;
  };
}

declare global {
  interface Window {
    Telegram?: { WebApp: TelegramWebApp };
  }
}

export function getTelegramWebApp(): TelegramWebApp | null {
  return window.Telegram?.WebApp ?? null;
}

export function getInitData(): string {
  return getTelegramWebApp()?.initData ?? "";
}

export function getTelegramUser(): TelegramWebAppUser | null {
  return getTelegramWebApp()?.initDataUnsafe.user ?? null;
}

/** Тактильная отдача для мини-игр (Фаза 4) — тихо no-op вне Telegram-клиента
 * или на платформах без поддержки haptics. */
export function haptic(style: "light" | "medium" | "heavy" = "light"): void {
  getTelegramWebApp()?.HapticFeedback?.impactOccurred(style);
}
