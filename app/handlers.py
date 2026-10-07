from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery

from . import db
from .core import (
    awaiting,
    bot,
    broadcast_state,
    is_admin,
    missing_channels,
    open_app_kb,
    safe_send,
    greeting_for,
    subscribe_kb,
    tmp_path,
)

log = logging.getLogger("storyframe")
router = Router()


def _user_dict(m: Message) -> dict:
    u = m.from_user
    return {"id": u.id, "username": u.username, "first_name": u.first_name, "last_name": u.last_name}


async def _gate(m: Message) -> bool:
    """True — можно продолжать. Иначе уже ответили пользователю (бан / подписка)."""
    row, _ = db.upsert_user(_user_dict(m))
    if row["banned"]:
        await m.answer("⛔ Доступ к боту ограничен.")
        return False
    missing = await missing_channels(m.from_user.id)
    if missing:
        await m.answer("Чтобы пользоваться ботом, подпишись на каналы ниже:", reply_markup=subscribe_kb(missing))
        return False
    return True


@router.message(CommandStart())
async def start(m: Message):
    if not await _gate(m):
        return
    await safe_send(m.chat.id, greeting_for(m.from_user.first_name), open_app_kb())


@router.callback_query(F.data == "check_sub")
async def check_sub(c: CallbackQuery):
    missing = await missing_channels(c.from_user.id)
    if missing:
        await c.answer("Ты ещё не подписан на все каналы", show_alert=True)
        return
    await c.answer("Готово!")
    await safe_send(c.message.chat.id, greeting_for(c.from_user.first_name), open_app_kb())


# ---------- админ: ожидаемое сообщение (приветствие / рассылка) ----------
@router.message(Command("cancel"))
async def cancel(m: Message):
    if awaiting.pop(m.from_user.id, None):
        await m.answer("Отменено.")


@router.message(F.from_user.func(lambda u: is_admin(u.id) and u.id in awaiting))
async def admin_awaited(m: Message):
    kind = awaiting.pop(m.from_user.id)
    html = m.html_text or ""
    if not html.strip():
        awaiting[m.from_user.id] = kind
        await m.answer("Пришли текстовое сообщение (или /cancel).")
        return
    if kind == "greeting":
        db.set_setting("greeting", html)
        await m.answer("✅ Приветствие обновлено. Так оно выглядит:")
        await safe_send(m.chat.id, greeting_for(m.from_user.first_name), open_app_kb())
    elif kind == "broadcast":
        asyncio.create_task(run_broadcast(html, m.chat.id))
        await m.answer("📣 Рассылка запущена, прогресс виден в админ-панели.")


async def run_broadcast(html: str, admin_chat: int) -> None:
    if broadcast_state["running"]:
        return
    ids = db.all_user_ids()
    broadcast_state.update(running=True, sent=0, failed=0, total=len(ids))
    for uid in ids:
        ok = await safe_send(uid, html, open_app_kb())
        broadcast_state["sent" if ok else "failed"] += 1
        await asyncio.sleep(0.05)
    broadcast_state["running"] = False
    await safe_send(admin_chat, f"📣 Рассылка завершена: доставлено {broadcast_state['sent']}, ошибок {broadcast_state['failed']}.")


@router.message(Command("emojiid"))
async def emoji_id(m: Message):
    if not is_admin(m.from_user.id):
        return
    await m.answer("Пришли мне сообщение с премиум-эмодзи — верну готовые теги для приветствия.")


@router.message(F.entities.func(lambda ents: bool(ents) and any(e.type == "custom_emoji" for e in ents)) & F.from_user.func(lambda u: is_admin(u.id)))
async def emoji_tags(m: Message):
    tags = [
        f'<code>&lt;tg-emoji emoji-id="{e.custom_emoji_id}"&gt;{e.extract_from(m.text or m.caption or "")}&lt;/tg-emoji&gt;</code>'
        for e in (m.entities or [])
        if e.type == "custom_emoji"
    ]
    await m.answer("Теги премиум-эмодзи:\n" + "\n".join(tags))


# ---------- фото из чата → в Mini App ----------
@router.message(F.photo | F.document.mime_type.startswith("image/"))
async def got_photo(m: Message):
    if not await _gate(m):
        return
    file_id = m.photo[-1].file_id if m.photo else m.document.file_id
    try:
        await bot.download(file_id, destination=tmp_path("pending", m.from_user.id))
    except Exception as e:  # noqa: BLE001
        log.warning("download pending failed: %s", e)
        await m.answer("Не получилось загрузить фото, попробуй ещё раз.")
        return
    await m.answer(
        "📸 Фото получено! Открой приложение — там можно нарезать его на сториз или подобрать рамку под цвет.",
        reply_markup=open_app_kb("Открыть с этим фото"),
    )


# ---------- Telegram Stars ----------
@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    row = db.get_user(q.from_user.id)
    kind, _, uid = (q.invoice_payload or "").partition(":")
    ok = bool(row) and not row["banned"] and kind in ("pack", "premium") and uid == str(q.from_user.id)
    await q.answer(ok=ok, error_message=None if ok else "Покупка недоступна")


@router.message(F.successful_payment)
async def paid(m: Message):
    p = m.successful_payment
    kind, _, uid = p.invoice_payload.partition(":")
    if uid != str(m.from_user.id):
        return
    db.log_payment(m.from_user.id, kind, p.total_amount, p.telegram_payment_charge_id)
    if kind == "pack":
        size = db.get_int("pack_size")
        db.add_balance(m.from_user.id, size)
        await m.answer(f"✅ Оплачено! Начислено <b>{size}</b> генераций.", reply_markup=open_app_kb())
    elif kind == "premium":
        db.set_premium(m.from_user.id, True)
        await m.answer("👑 <b>Premium активирован!</b>\nТеперь рамки и нарезка сторис — без ограничений.", reply_markup=open_app_kb())


# ---------- всё остальное ----------
@router.message()
async def fallback(m: Message):
    if not await _gate(m):
        return
    await m.answer("Открой приложение, чтобы нарезать сториз или сделать рамку 👇", reply_markup=open_app_kb())
