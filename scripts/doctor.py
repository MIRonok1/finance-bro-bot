#!/usr/bin/env python3
"""Диагностика окружения Netrun. Запускается вручную после деплоя.

Каждый пункт независим и печатает статус OK/FAIL со своей причиной —
падение одной проверки не должно останавливать остальные. Результат
определяет, реалистичны ли Фаза 2 (MOEX) и Веха 4 (Anthropic API из
админских скриптов) на этом хостинге.

Сознательно синхронный (httpx.Client, не async): это одноразовый ручной
инструмент диагностики, а не часть рантайма бота, усложнять его asyncio
незачем.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import time
from datetime import UTC, datetime
from importlib import metadata as importlib_metadata

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover — Python < 3.9, у нас всегда 3.12
    ZoneInfo = None  # type: ignore[assignment, misc]

import httpx

DATA_DIR = "/data"
MOEX_URL = "https://iss.moex.com/iss/engines.json"
ANTHROPIC_URL = "https://api.anthropic.com/v1/models"


def _ok(label: str, detail: str = "") -> None:
    line = f"[OK]   {label}"
    if detail:
        line += f" — {detail}"
    print(line)


def _fail(label: str, reason: str) -> None:
    print(f"[FAIL] {label} — {reason}")


def check_python_and_packages() -> None:
    print("\n== Python и пакеты ==")
    try:
        _ok("Python версия", sys.version.replace("\n", " "))
        pkgs = sorted(
            f"{dist.metadata['Name']}=={dist.version}"
            for dist in importlib_metadata.distributions()
            if dist.metadata.get("Name")
        )
        _ok("Установленные пакеты", f"{len(pkgs)} шт.")
        for pkg in pkgs:
            print(f"       {pkg}")
    except Exception as exc:  # noqa: BLE001
        _fail("Python и пакеты", repr(exc))


def check_data_dir() -> None:
    print("\n== Директория /data ==")
    try:
        if not os.path.isdir(DATA_DIR):
            _fail("/data существует", f"путь {DATA_DIR} не найден или не директория")
            return
        _ok("/data существует")
    except Exception as exc:  # noqa: BLE001
        _fail("/data существует", repr(exc))
        return

    try:
        test_path = os.path.join(DATA_DIR, ".doctor_write_test")
        with open(test_path, "w", encoding="utf-8") as f:
            f.write("doctor")
        with open(test_path, encoding="utf-8") as f:
            content = f.read()
        os.remove(test_path)
        if content == "doctor":
            _ok("/data доступна на запись")
        else:
            _fail("/data доступна на запись", "прочитанное содержимое не совпало с записанным")
    except Exception as exc:  # noqa: BLE001
        _fail("/data доступна на запись", repr(exc))

    try:
        usage = shutil.disk_usage(DATA_DIR)
        free_mb = usage.free / (1024 * 1024)
        _ok("Свободное место", f"{free_mb:.1f} MB")
    except Exception as exc:  # noqa: BLE001
        _fail("Свободное место", repr(exc))


def check_sqlite_roundtrip() -> None:
    print("\n== SQLite round-trip в /data ==")
    db_path = os.path.join(DATA_DIR, ".doctor_test.db")
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS doctor_probe (id INTEGER PRIMARY KEY, val TEXT)")
        conn.execute("INSERT INTO doctor_probe (val) VALUES (?)", ("hello",))
        conn.commit()
        row = conn.execute("SELECT val FROM doctor_probe LIMIT 1").fetchone()
        conn.close()
        os.remove(db_path)
        if row and row[0] == "hello":
            _ok("Запись/чтение SQLite")
        elif not row:
            _fail("Запись/чтение SQLite", "строка не найдена после записи")
        else:
            _fail("Запись/чтение SQLite", f"неожиданное значение: {row}")
    except Exception as exc:  # noqa: BLE001
        _fail("Запись/чтение SQLite", repr(exc))


def check_http(
    label: str,
    url: str,
    headers: dict[str, str] | None = None,
    body_preview: bool = False,
) -> None:
    print(f"\n== HTTP: {label} ==")
    try:
        start = time.monotonic()
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers or {})
        elapsed_ms = (time.monotonic() - start) * 1000
        detail = f"код {resp.status_code}, {elapsed_ms:.0f} ms"
        if body_preview:
            preview = resp.text[:200].replace("\n", " ")
            detail += f", тело: {preview!r}"
        if resp.status_code < 500:
            _ok(label, detail)
        else:
            _fail(label, detail)
    except Exception as exc:  # noqa: BLE001
        _fail(label, repr(exc))


def check_moex() -> None:
    check_http("MOEX ISS API (egress)", MOEX_URL, body_preview=True)


def check_anthropic() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n== HTTP: Anthropic API ==")
        print("[SKIP] ANTHROPIC_API_KEY не задан — проверка пропущена (нормально для бота)")
        return
    check_http(
        "Anthropic API (egress)",
        ANTHROPIC_URL,
        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        body_preview=False,
    )


def check_timezone() -> None:
    print("\n== Часовые пояса ==")
    try:
        tz_env = os.environ.get("TZ", "(не задан)")
        _ok("TZ env", tz_env)
        now_utc = datetime.now(UTC)
        _ok("Текущее время UTC", now_utc.isoformat())
        if ZoneInfo is not None:
            now_msk = now_utc.astimezone(ZoneInfo("Europe/Moscow"))
            _ok("Текущее время Europe/Moscow", now_msk.isoformat())
        else:
            _fail("Текущее время Europe/Moscow", "zoneinfo недоступен")
    except Exception as exc:  # noqa: BLE001
        _fail("Часовые пояса", repr(exc))


def main() -> None:
    print("=== Finance bro doctor: диагностика окружения ===")
    check_python_and_packages()
    check_data_dir()
    check_sqlite_roundtrip()
    check_moex()
    check_anthropic()
    check_timezone()
    print("\n=== Готово ===")


if __name__ == "__main__":
    main()
