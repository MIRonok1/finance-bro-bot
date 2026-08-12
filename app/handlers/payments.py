"""Пейволл на Telegram Stars: /subscribe -> инвойс (currency=XTR, пустой
provider_token) -> pre_checkout_query -> successful_payment -> entitlement.
/refund (админ) — refundStarPayment. Всё активно только при
PAYWALL_ENABLED=true; сам факт наличия этих хендлеров не включает пейволл."""

from __future__ import annotations

import logging

import aiosqlite
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import LabeledPrice, Message, PreCheckoutQuery

from app import texts
from app.config import Settings
from app.payments import repo as payments_repo
from app.payments.plans import MONTHLY_PLAN, PLANS

logger = logging.getLogger(__name__)

router = Router(name="payments")

INVOICE_PAYLOAD_PREFIX = "sub"


def _build_payload(plan_code: str, user_id: int) -> str:
    return f"{INVOICE_PAYLOAD_PREFIX}:{plan_code}:{user_id}"


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message, db: aiosqlite.Connection, settings: Settings) -> None:
    if not settings.paywall_enabled:
        await message.answer(texts.PAYWALL_DISABLED)
        return

    user_id = message.from_user.id
    if await payments_repo.has_active_entitlement(db, user_id):
        await message.answer(texts.PAYWALL_ALREADY_ACTIVE)
        return

    plan = MONTHLY_PLAN
    await message.answer_invoice(
        title=plan.title,
        description=plan.description,
        payload=_build_payload(plan.code, user_id),
        currency="XTR",
        prices=[LabeledPrice(label=plan.title, amount=plan.stars_price)],
        provider_token="",
    )


@router.pre_checkout_query()
async def on_pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    payload = pre_checkout_query.invoice_payload
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != INVOICE_PAYLOAD_PREFIX or parts[1] not in PLANS:
        await pre_checkout_query.answer(ok=False, error_message=texts.PAYWALL_INVOICE_INVALID)
        return
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(message: Message, db: aiosqlite.Connection) -> None:
    payment = message.successful_payment
    parts = payment.invoice_payload.split(":")
    plan = PLANS.get(parts[1]) if len(parts) == 3 else None
    if plan is None:
        logger.error("Неизвестный/битый payload в successful_payment: %s", payment.invoice_payload)
        return

    user_id = message.from_user.id
    created = await payments_repo.grant_entitlement(
        db,
        user_id,
        plan.code,
        plan.duration_days,
        source="stars_purchase",
        stars_paid=payment.total_amount,
        charge_id=payment.telegram_payment_charge_id,
    )
    if not created:
        # charge_id уже обработан — повторная доставка от Telegram,
        # доступ уже выдан, просто не начисляем повторно.
        logger.info(
            "Повторная доставка successful_payment, charge_id=%s уже обработан",
            payment.telegram_payment_charge_id,
        )

    await message.answer(texts.PAYWALL_PAYMENT_SUCCESS.format(days=plan.duration_days))


@router.message(Command("refund"))
async def cmd_refund(message: Message, db: aiosqlite.Connection, settings: Settings) -> None:
    user = message.from_user
    if not user or user.id not in settings.admin_ids_set:
        await message.answer(texts.ADMIN_ACCESS_DENIED)
        return

    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer(texts.PAYWALL_REFUND_USAGE)
        return

    try:
        target_user_id = int(parts[1])
    except ValueError:
        await message.answer(texts.PAYWALL_REFUND_USAGE)
        return
    charge_id = parts[2]

    try:
        await message.bot.refund_star_payment(
            user_id=target_user_id, telegram_payment_charge_id=charge_id
        )
    except Exception as exc:  # noqa: BLE001 — показываем причину админу как есть
        logger.exception("Не удалось выполнить возврат Stars")
        await message.answer(texts.PAYWALL_REFUND_FAILED.format(error=str(exc)))
        return

    await message.answer(texts.PAYWALL_REFUND_DONE)
