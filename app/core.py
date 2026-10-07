"""Общие объекты: бот, блокировки, отправка сообщений, обязательная подписка."""
from __future__ import annotations

import asyncio
import logging
import re
import time

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from . import db
from .config import ADMIN_IDS, BOT_TOKEN, TMP_DIR, WEBAPP_URL

log = logging.getLogger("storyframe")

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)) if BOT_TOKEN else None

# админ ждёт от нас следующее сообщение: uid -> "greeting" | "broadcast"
awaiting: dict[int, str] = {}
_locks: dict[int, asyncio.Lock] = {}
broadcast_state: dict = {"running": False, "sent": 0, "failed": 0, "total": 0}

_EMOJI_RE = re.compile(r'<tg-emoji emoji-id="\d+">(.*?)</tg-emoji>', re.S)


def user_lock(uid: int) -> asyncio.Lock:
    return _locks.setdefault(uid, asyncio.Lock())


def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS


def strip_custom_emoji(html: str) -> str:
    return _EMOJI_RE.sub(r"\1", html)


def open_app_kb(text: str = "Открыть приложение") -> InlineKeyboardMarkup | None:
    if not WEBAPP_URL:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, web_app=WebAppInfo(url=WEBAPP_URL))]])


async def safe_send(chat_id: int, html: str, reply_markup=None) -> bool:
    """Отправка HTML-текста; если не вышло с премиум-эмодзи — повтор с обычными."""
    try:
        await bot.send_message(chat_id, html, reply_markup=reply_markup)
        return True
    except TelegramForbiddenError:
        return False
    except TelegramAPIError as e:
        log.warning("send_message %s failed: %s", chat_id, e)
        try:
            await bot.send_message(chat_id, strip_custom_emoji(html), reply_markup=reply_markup)
            return True
        except TelegramAPIError:
            return False


def greeting_for(name: str) -> str:
    html = db.get_setting("greeting")
    return html.replace("{name}", name or "друг")


# ---------- обязательная подписка ----------
async def missing_channels(uid: int) -> list[dict]:
    if is_admin(uid):
        return []
    missing = []
    for ch in db.list_channels():
        ref = ch["chat_ref"]
        try:
            member = await bot.get_chat_member(int(ref) if ref.lstrip("-").isdigit() else ref, uid)
            if member.status in ("left", "kicked"):
                missing.append({"id": ch["id"], "title": ch["title"], "link": ch["link"]})
        except TelegramAPIError as e:  # бот не админ в канале — не блокируем пользователя
            log.warning("get_chat_member %s failed: %s", ref, e)
    return missing


def subscribe_kb(missing: list[dict]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"Подписаться: {m['title']}", url=m["link"])] for m in missing]
    rows.append([InlineKeyboardButton(text="Я подписался ✔", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------- временные файлы ----------
def tmp_path(kind: str, uid: int):
    return TMP_DIR / f"{kind}_{uid}.bin"


def cleanup_tmp(max_age: int = 3600) -> None:
    now = time.time()
    for p in TMP_DIR.glob("*.bin"):
        try:
            if now - p.stat().st_mtime > max_age:
                p.unlink()
        except OSError:
            pass
