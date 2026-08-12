"""Все пользовательские тексты бота. Русские строки живут только здесь —
если понадобится английская версия, добавляем параллельный набор констант,
не разбрасывая строки по хендлерам."""

START_GREETING = (
    "Привет! Это Finance bro — тренажёр для подготовки к интервью "
    "в инвестбанкинг и на другие финансовые позиции.\n\n"
    "Выбирай модуль:"
)

HELP_TEXT = (
    "Finance bro — тренажёр для подготовки к финансовым интервью.\n\n"
    "Команды:\n"
    "/start — главное меню\n"
    "/stats — статистика и повторение\n"
    "/help — эта справка\n\n"
    "Модули:\n"
    "• Теория и кейсы — DCF, мультипликаторы, LBO, accounting, M&A\n"
    "• Быстрый счёт — арифметика под интервью на время\n"
    "• Портфель — симулятор на данных MOEX"
)

BTN_THEORY = "📚 Теория и кейсы"
BTN_MENTAL_MATH = "🧮 Быстрый счёт"
BTN_PORTFOLIO = "📈 Портфель"
BTN_WEBAPP = "🖥 Открыть приложение"

# --- Быстрый счёт (Веха 2) ---
MM_CHOOSE_DIFFICULTY = "Быстрый счёт — выбери сложность:"
MM_STOP_BUTTON = "🛑 Завершить"
MM_CONTINUE = "▶️ Продолжить"
MM_FINISH = "🏁 Закончить"
MM_CORRECT = "✅ Верно!"
MM_INCORRECT = "❌ Неверно."
MM_YOUR_ANSWER = "Твой ответ: {answer}"
MM_CORRECT_ANSWER = "Правильный ответ: {answer}"
MM_STREAK = "🔥 Серия: {streak}"
MM_SPEED_FAST = "⚡ {s} сек"
MM_SPEED_NORMAL = "🙂 {s} сек"
MM_SPEED_SLOW = "🐢 {s} сек"
MM_COULD_NOT_PARSE = "Не смог распознать число — попробуй ещё раз."
MM_CHECKPOINT = "Пройдено {total}, верно {correct}, лучшая серия за всё время — {best_streak}."
MM_SESSION_DONE = (
    "Готово! Всего {total}, верно {correct} ({pct}%), лучшая серия в этой сессии — {best_streak}."
)
MM_BACK_TO_MENU = "⬅️ В меню"
MM_NOT_IN_SESSION = "Сессия не активна — начни заново через /start."

# --- Квиз (Веха 1) ---
QUIZ_CHOOSE_TOPIC = "Выбери тему:"
QUIZ_CHOOSE_DIFFICULTY = "Выбери сложность (или «Любая»):"
QUIZ_DIFF_ANY = "Любая"
QUIZ_NO_QUESTIONS = (
    "По этой теме и сложности пока нет одобренных вопросов. Попробуй другую комбинацию."
)
QUIZ_QUESTION_HEADER = "Вопрос {i}/{n} · {topic} · сложность {difficulty}"
QUIZ_NUMERIC_HINT = "\n\nНапиши число (например: 1.5, 1 500 000, 1.5 млрд)."
QUIZ_OPEN_HINT = "\n\nНапиши свой ответ текстом — после этого покажу эталонный разбор."
QUIZ_CORRECT = "✅ Верно!"
QUIZ_INCORRECT = "❌ Неверно."
QUIZ_YOUR_ANSWER = "Твой ответ: {answer}"
QUIZ_COULD_NOT_PARSE = "Не смог распознать число в ответе — попробуй ещё раз."
QUIZ_EXPLANATION = "Разбор:\n{explanation}"
QUIZ_RATE_YOURSELF = "Как оцениваешь свой ответ по сравнению с разбором?"
QUIZ_RATE_CORRECT = "✅ Верно"
QUIZ_RATE_PARTIAL = "🟡 Частично"
QUIZ_RATE_INCORRECT = "❌ Неверно"
QUIZ_NEXT = "Далее ➡️"
QUIZ_SESSION_DONE = "Сессия завершена: {correct}/{total} верно."
QUIZ_BACK_TO_MENU = "⬅️ В меню"
QUIZ_NOT_IN_SESSION = "Сессия не активна — начни заново через /start."

# --- Прогресс и повторение (Веха 3) ---
STATS_HEADER = "📊 Твоя статистика"
STATS_TOPIC_LINE = "{title}: {correct}/{total} ({pct}%){weak_marker}"
STATS_WEAK_MARKER = " ⚠️ слабое место"
STATS_QUIZ_HEADER = "📚 Теория и кейсы"
STATS_NO_QUIZ_ATTEMPTS = (
    "Пока нет попыток в «Теория и кейсы» — начни сессию, чтобы увидеть статистику."
)
STATS_MENTAL_MATH_HEADER = "🧮 Быстрый счёт"
STATS_MENTAL_MATH_LINE = "Всего задач: {total}, верно: {correct} ({pct}%), лучшая серия: {best}"
STATS_NO_MENTAL_MATH = "Пока нет попыток в «Быстрый счёт»."
STATS_DAILY_STREAK = "🔥 Серия дней подряд: {streak}"
STATS_DUE_REVIEW = "🔁 Вопросов на повторение: {count}"
STATS_START_REVIEW_BUTTON = "🔁 Начать повторение"
STATS_NOTHING_TO_REVIEW = (
    "Нечего повторять — все вопросы либо не отвечены, либо ещё не подошёл срок."
)

# --- Портфель (Веха 5, Фаза 2) ---
PORTFOLIO_HEADER = "📈 Портфель"
PORTFOLIO_CASH_LINE = "Свободные деньги: {cash}₽"
PORTFOLIO_EQUITY_LINE = "Общая стоимость: {equity}₽"
PORTFOLIO_DAILY_PNL_LINE = "P&L за день: {pnl}₽ ({pct}%)"
PORTFOLIO_VS_IMOEX_LINE = "IMOEX за день: {pct}%"
PORTFOLIO_HOLDING_LINE = "{ticker}: {qty} шт. × {avg}₽ (тек. {price}₽, P&L {pnl}₽)"
PORTFOLIO_NO_HOLDINGS = "Пока нет позиций."
PORTFOLIO_BUY_BUTTON = "🛒 Купить"
PORTFOLIO_SELL_BUTTON = "💰 Продать"
PORTFOLIO_REFRESH_BUTTON = "🔄 Обновить"
PORTFOLIO_BACK_BUTTON = "⬅️ В меню"
PORTFOLIO_ASK_TICKER = "Какой тикер? (например, SBER)"
PORTFOLIO_ASK_QUANTITY_BUY = "Сколько акций {ticker} купить? Цена сейчас {price}₽."
PORTFOLIO_ASK_QUANTITY_SELL = (
    "Сколько акций {ticker} продать? В портфеле {qty} шт., цена сейчас {price}₽."
)
PORTFOLIO_INVALID_QUANTITY = "Введи целое положительное число."
PORTFOLIO_TICKER_NOT_FOUND = (
    "Не нашёл тикер {ticker} на MOEX (или рынок сейчас закрыт). Попробуй другой."
)
PORTFOLIO_MOEX_UNAVAILABLE = "MOEX сейчас недоступен, попробуй позже."
PORTFOLIO_BUY_DONE = "Куплено {qty} {ticker} по {price}₽. Остаток денег: {cash}₽."
PORTFOLIO_SELL_DONE = "Продано {qty} {ticker} по {price}₽. Остаток денег: {cash}₽."
PORTFOLIO_NO_HOLDINGS_TO_SELL = "Нечего продавать — портфель пуст."
PORTFOLIO_CHOOSE_TICKER_TO_SELL = "Что продать?"

ADMIN_WELCOME = "Админ-панель.\n/review — проверить черновики вопросов (approve/edit/reject)."
ADMIN_ACCESS_DENIED = "Эта команда доступна только администраторам."

# --- /review черновиков (Веха 4) ---
REVIEW_NO_DRAFTS = "Черновиков нет — нечего проверять."
REVIEW_DONE = "Черновики закончились."
REVIEW_CARD = (
    "Черновик {i}/{n} · id={id} · {type} · сложность {difficulty}\n\n"
    "{body}\n\n"
    "Разбор:\n{explanation}"
)
REVIEW_STATUS_SET = "Статус: {status}"
REVIEW_SEND_NEW_BODY = "Пришли новый текст вопроса (body) взамен текущего."
REVIEW_BODY_UPDATED = "Текст обновлён."

# --- Пейволл на Telegram Stars (Веха 6) ---
PAYWALL_DISABLED = "Подписка сейчас не нужна — всё доступно бесплатно."
PAYWALL_ALREADY_ACTIVE = "У тебя уже есть активная подписка."
PAYWALL_INVOICE_INVALID = "Не удалось создать счёт — попробуй ещё раз через /subscribe."
PAYWALL_PAYMENT_SUCCESS = "Оплата прошла! Доступ открыт на {days} дней."
PAYWALL_REFUND_USAGE = "Формат: /refund <user_id> <charge_id>"
PAYWALL_REFUND_DONE = "Возврат выполнен."
PAYWALL_REFUND_FAILED = "Не удалось выполнить возврат: {error}"
PAYWALL_LIMIT_REACHED = (
    "Бесплатный лимит на сегодня исчерпан ({limit} сессий в день). Оформи подписку: /subscribe"
)

ERROR_GENERIC = (
    "Что-то пошло не так на нашей стороне. Мы уже знаем об этом — попробуй ещё раз чуть позже."
)

THROTTLED = "Слишком много запросов подряд — подожди секунду."
