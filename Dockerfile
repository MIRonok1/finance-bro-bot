# ПРОВЕРЕНО ВЖИВУЮ (2026-08-12): текущий прод-деплой на Netrun идёт через
# GitHub-автодетект Python (pip install -r requirements.txt), этот
# Dockerfile НЕ используется платформой. Оставлен для локальной сборки и
# на случай, если Netrun добавит поддержку Docker. Именно поэтому
# webapp/dist коммитится в git предсобранным, а не собирается стадией
# ниже — см. README.md → «Деплой на Netrun».

# --- Стадия 1: сборка фронтенда Mini App (React + Vite) ---
FROM node:20-slim AS webapp-build

WORKDIR /webapp
COPY webapp/package.json webapp/package-lock.json* ./
RUN npm ci

COPY webapp/ .
RUN npm run build
# Результат: /webapp/dist — статические файлы, их заберёт вторая стадия.

# --- Стадия 2: рантайм бота + Mini App сервер ---
FROM python:3.12-slim

# Логи должны сразу попадать в stdout, без буферизации.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=webapp-build /webapp/dist /app/webapp/dist

# /data — единственное постоянное хранилище на Netrun, монтируется платформой.
VOLUME ["/data"]

# Бот работает через long polling — этот порт только для Mini App
# (статика + /api/*), не вебхук бота. Значение должно совпадать с
# WEBAPP_PORT/PORT в env, иначе платформа не сможет прокинуть трафик сюда.
EXPOSE 8080

CMD ["python", "main.py"]
