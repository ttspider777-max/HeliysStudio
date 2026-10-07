"""HTTP-сервер: раздаёт Mini App и API."""
from __future__ import annotations

import asyncio
import io
import json
import logging
import time
from urllib.parse import unquote

from aiohttp import web
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
from aiogram.types import BufferedInputFile, InputMediaDocument, InputMediaPhoto, LabeledPrice

from . import db, imaging
from .auth import validate_init_data
from .config import BOT_TOKEN, DEV, ADMIN_IDS, TMP_DIR, WEBAPP_DIR
from .core import (
    awaiting,
    bot,
    broadcast_state,
    is_admin,
    log,
    missing_channels,
    tmp_path,
    user_lock,
)

MAX_UPLOAD = 25 * 1024 * 1024
routes = web.RouteTableDef()


def ok(data: dict | None = None, **extra) -> web.Response:
    return web.json_response({"ok": True, **(data or {}), **extra})


def fail(error: str, status: int = 400, **extra) -> web.Response:
    return web.json_response({"ok": False, "error": error, **extra}, status=status)


# --------------------------------------------------------------------------------------
# middleware: проверка подписи initData, бан
# --------------------------------------------------------------------------------------
@web.middleware
async def auth_mw(request: web.Request, handler):
    if not request.path.startswith("/api/"):
        return await handler(request)
    user = validate_init_data(request.headers.get("X-Init-Data", ""), BOT_TOKEN)
    request["dev"] = False
    if not user and DEV and request.remote in ("127.0.0.1", "::1"):
        request["dev"] = True
        uid = int(request.headers.get("X-Dev-User") or (next(iter(ADMIN_IDS), 1)))
        user = {"id": uid, "first_name": unquote(request.headers.get("X-Dev-Name") or "Dev"), "username": request.headers.get("X-Dev-Username") or "dev_user"}
    if not user:
        return fail("unauthorized", 401)
    row, is_new = db.upsert_user(user)
    if row["banned"]:
        return fail("banned", 403)
    request["uid"] = int(user["id"])
    request["tg_user"] = user
    request["is_new"] = is_new
    if request.path.startswith("/api/admin/") and not is_admin(request["uid"]):
        return fail("forbidden", 403)
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except Exception:  # noqa: BLE001
        log.exception("API error %s", request.path)
        return fail("server_error", 500)


def _profile(uid: int, tg_user: dict) -> dict:
    u = db.get_user(uid)
    return {
        "id": uid,
        "first_name": u["first_name"] or "",
        "last_name": u["last_name"] or "",
        "username": u["username"] or "",
        "photo_url": tg_user.get("photo_url", ""),
        "joined_at": u["joined_at"],
        "free_left": u["free_left"],
        "balance": u["balance"],
        "premium": bool(u["premium"]),
        "gens_total": u["gens_total"],
        "tutorial_seen": bool(u["tutorial_seen"]),
        "is_admin": is_admin(uid),
        "has_pending": tmp_path("pending", uid).exists(),
        "prices": {
            "pack_size": db.get_int("pack_size"),
            "pack_price": db.get_int("pack_price"),
            "premium_price": db.get_int("premium_price"),
            "free_gens": db.get_int("free_gens"),
        },
    }


@routes.get("/api/me")
async def me(request: web.Request):
    uid = request["uid"]
    missing = await missing_channels(uid)
    return ok({"me": _profile(uid, request["tg_user"]), "missing": missing})


@routes.post("/api/tutorial/seen")
async def tutorial_seen(request: web.Request):
    db.mark_tutorial_seen(request["uid"])
    return ok()


@routes.post("/api/check_sub")
async def check_sub(request: web.Request):
    return ok(missing=await missing_channels(request["uid"]))


# --------------------------------------------------------------------------------------
# получение исходного изображения: файл / фото из чата / аватарка Telegram
# --------------------------------------------------------------------------------------
async def read_source(request: web.Request, form, persist_as: str | None = None) -> bytes | web.Response:
    uid = request["uid"]
    source = form.get("source", "file")
    if source == "pending":
        p = tmp_path("pending", uid)
        if not p.exists():
            return fail("no_pending")
        return p.read_bytes()
    if source == "avatar":
        try:
            photos = await bot.get_user_profile_photos(uid, limit=1)
            if not photos.total_count:
                return fail("no_avatar")
            buf = io.BytesIO()
            await bot.download(photos.photos[0][-1].file_id, destination=buf)
            return buf.getvalue()
        except TelegramAPIError:
            return fail("no_avatar")
    f = form.get("file")
    if f is None or not hasattr(f, "file"):
        return fail("no_file")
    data = f.file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        return fail("too_big", 413)
    return data


async def need_credits(uid: int) -> web.Response | None:
    if not db.can_generate(uid):
        return fail("no_credits", 402)
    missing = await missing_channels(uid)
    if missing:
        return fail("not_subscribed", 428, missing=missing)
    return None


async def deliver_error(e: Exception) -> web.Response:
    if isinstance(e, TelegramForbiddenError):
        return fail("start_bot", 409)
    log.warning("deliver failed: %s", e)
    return fail("send_failed", 502)


# --------------------------------------------------------------------------------------
# нарезка сторис
# --------------------------------------------------------------------------------------
@routes.post("/api/slice")
async def slice_story(request: web.Request):
    uid = request["uid"]
    form = await request.post()
    async with user_lock(uid):
        if (r := await need_credits(uid)) is not None:
            return r
        data = await read_source(request, form)
        if isinstance(data, web.Response):
            return data
        try:
            parts = int(form.get("parts", 3))
            mode = "fit" if form.get("mode") == "fit" else "fill"
            as_file = form.get("as_file", "1") == "1"
            im = await asyncio.to_thread(imaging.open_image, data)
            tiles = await asyncio.to_thread(imaging.slice_story, im, parts, mode)
        except Exception:  # noqa: BLE001
            return fail("bad_image")
        try:
            if not request["dev"]:
                await _send_tiles(uid, tiles, as_file)
        except Exception as e:  # noqa: BLE001
            return await deliver_error(e)
        db.consume(uid, "slice")
        return ok(me=_profile(uid, request["tg_user"]), parts=len(tiles))


async def _send_tiles(uid: int, tiles: list[bytes], as_file: bool) -> None:
    n = len(tiles)
    cap = f"✂️ Сториз: {n} {'часть' if n == 1 else 'части' if n < 5 else 'частей'}. Выкладывай по порядку 1 → {n}."
    if n == 1:
        f = BufferedInputFile(tiles[0], "story_1.jpg")
        await (bot.send_document(uid, f, caption=cap) if as_file else bot.send_photo(uid, f, caption=cap))
        return
    media = []
    for i, t in enumerate(tiles, 1):
        f = BufferedInputFile(t, f"story_{i}.jpg")
        kw = {"caption": cap} if i == 1 else {}
        media.append(InputMediaDocument(media=f, **kw) if as_file else InputMediaPhoto(media=f, **kw))
    await bot.send_media_group(uid, media)


# --------------------------------------------------------------------------------------
# рамки для аватарки
# --------------------------------------------------------------------------------------
def _frame_src(uid: int):
    p = tmp_path("frame", uid)
    return p if p.exists() else None


def _palettes_payload(pals) -> list[dict]:
    return [{"name": n, "c1": imaging.hex_of(a), "c2": imaging.hex_of(b)} for n, a, b in pals]


def _frame_previews(uid: int, palette: int, only_palette: bool = False):
    data = tmp_path("frame", uid).read_bytes()
    im = imaging.open_image(data)
    pals = imaging.make_palettes(im)
    palette = max(0, min(len(pals) - 1, palette))
    _, c1, c2 = pals[palette]
    return pals, imaging.previews(im, c1, c2, only_palette=only_palette)


def _frame_hq(uid: int, style: str, palette: int) -> str:
    im = imaging.open_image(tmp_path("frame", uid).read_bytes())
    pals = imaging.make_palettes(im)
    _, c1, c2 = pals[max(0, min(len(pals) - 1, palette))]
    img = imaging.render_frame(imaging.square_avatar(im, 512), style, c1, c2, 512)
    return imaging.data_url(imaging.webp_bytes(img, 90))


@routes.post("/api/frames/upload")
async def frames_upload(request: web.Request):
    uid = request["uid"]
    form = await request.post()
    data = await read_source(request, form)
    if isinstance(data, web.Response):
        return data
    try:
        im = await asyncio.to_thread(imaging.open_image, data)
        small = await asyncio.to_thread(imaging.square_avatar, im, 1024)
        buf = io.BytesIO()
        small.save(buf, "JPEG", quality=95)
        tmp_path("frame", uid).write_bytes(buf.getvalue())
        pals, prev = await asyncio.to_thread(_frame_previews, uid, 0)
    except Exception:  # noqa: BLE001
        return fail("bad_image")
    return ok(palettes=_palettes_payload(pals), previews=prev, palette=0, cats=imaging.CATS)


@routes.post("/api/frames/previews")
async def frames_previews(request: web.Request):
    uid = request["uid"]
    body = await request.json()
    if not _frame_src(uid):
        return fail("no_source", 410)
    pals, prev = await asyncio.to_thread(_frame_previews, uid, int(body.get("palette", 0)), True)
    return ok(previews=prev)


@routes.post("/api/frames/hq")
async def frames_hq(request: web.Request):
    uid = request["uid"]
    body = await request.json()
    if body.get("style") not in imaging.STYLES:
        return fail("bad_style")
    if not _frame_src(uid):
        return fail("no_source", 410)
    return ok(img=await asyncio.to_thread(_frame_hq, uid, body["style"], int(body.get("palette", 0))))


@routes.post("/api/frames/render")
async def frames_render(request: web.Request):
    uid = request["uid"]
    body = await request.json()
    style = body.get("style")
    if style not in imaging.STYLES:
        return fail("bad_style")
    async with user_lock(uid):
        if (r := await need_credits(uid)) is not None:
            return r
        if not _frame_src(uid):
            return fail("no_source", 410)

        def work() -> bytes:
            im = imaging.open_image(tmp_path("frame", uid).read_bytes())
            pals = imaging.make_palettes(im)
            _, c1, c2 = pals[max(0, min(len(pals) - 1, int(body.get("palette", 0))))]
            return imaging.png_bytes(imaging.render_frame(imaging.square_avatar(im, 1024), style, c1, c2, 1024))

        png = await asyncio.to_thread(work)
        try:
            name = imaging.STYLES[style]["name"]
            if not request["dev"]:
                await bot.send_document(
                    uid, BufferedInputFile(png, f"avatar_frame_{style}.png"), caption=f"🖼 Рамка «{name}» — PNG 1024×1024 с прозрачным фоном."
                )
        except Exception as e:  # noqa: BLE001
            return await deliver_error(e)
        db.consume(uid, "frame")
        return ok(me=_profile(uid, request["tg_user"]))


# --------------------------------------------------------------------------------------
# покупки за Telegram Stars (только отсюда, из Mini App)
# --------------------------------------------------------------------------------------
@routes.post("/api/buy")
async def buy(request: web.Request):
    uid = request["uid"]
    kind = (await request.json()).get("kind")
    if kind == "pack":
        size, price = db.get_int("pack_size"), db.get_int("pack_price")
        title, desc = f"{size} генераций", f"Пакет из {size} генераций для нарезки сторис и рамок"
    elif kind == "premium":
        price = db.get_int("premium_price")
        title, desc = "Premium", "Безлимитные рамки и нарезка сторис навсегда"
    else:
        return fail("bad_kind")
    if kind == "premium" and db.get_user(uid)["premium"]:
        return fail("already_premium")
    link = await bot.create_invoice_link(
        title=title, description=desc, payload=f"{kind}:{uid}", currency="XTR", prices=[LabeledPrice(label=title, amount=price)]
    )
    return ok(link=link)


# --------------------------------------------------------------------------------------
# админ-панель
# --------------------------------------------------------------------------------------
def _user_row(r: dict) -> dict:
    return {
        "id": r["id"],
        "username": r["username"] or "",
        "name": " ".join(x for x in (r["first_name"], r["last_name"]) if x),
        "joined_at": r["joined_at"],
        "last_seen": r["last_seen"],
        "free_left": r["free_left"],
        "balance": r["balance"],
        "premium": bool(r["premium"]),
        "banned": bool(r["banned"]),
        "gens_total": r["gens_total"],
        "stars_spent": r["stars_spent"],
    }


@routes.get("/api/admin/stats")
async def a_stats(request: web.Request):
    return ok(stats=db.stats(), broadcast=broadcast_state)


@routes.get("/api/admin/users")
async def a_users(request: web.Request):
    q = request.query
    rows, total = db.list_users(q.get("q", ""), int(q.get("offset", 0)), min(int(q.get("limit", 20)), 50), q.get("banned") == "1")
    return ok(users=[_user_row(r) for r in rows], total=total)


@routes.get("/api/admin/user")
async def a_user(request: web.Request):
    try:
        u = db.get_user(int(request.query.get("id", "")))
    except ValueError:
        return fail("bad_id")
    return ok(user=_user_row(dict(u))) if u else fail("not_found", 404)


@routes.post("/api/admin/ban")
async def a_ban(request: web.Request):
    b = await request.json()
    uid = int(b["id"])
    if is_admin(uid):
        return fail("cant_ban_admin")
    if not db.set_banned(uid, bool(b["banned"])):
        return fail("not_found", 404)
    return ok(user=_user_row(dict(db.get_user(uid))))


@routes.post("/api/admin/balance")
async def a_balance(request: web.Request):
    b = await request.json()
    uid, delta = int(b["id"]), int(b["delta"])
    if db.add_balance(uid, delta) is None:
        return fail("not_found", 404)
    return ok(user=_user_row(dict(db.get_user(uid))))


@routes.post("/api/admin/premium")
async def a_premium(request: web.Request):
    b = await request.json()
    uid = int(b["id"])
    if not db.get_user(uid):
        return fail("not_found", 404)
    db.set_premium(uid, bool(b["on"]))
    return ok(user=_user_row(dict(db.get_user(uid))))


@routes.get("/api/admin/greeting")
async def a_greeting_get(request: web.Request):
    return ok(html=db.get_setting("greeting"))


@routes.post("/api/admin/greeting")
async def a_greeting_set(request: web.Request):
    html = str((await request.json()).get("html", "")).strip()
    if not html or len(html) > 3500:
        return fail("bad_text")
    db.set_setting("greeting", html)
    return ok()


@routes.post("/api/admin/await")
async def a_await(request: web.Request):
    """Админ хочет прислать приветствие/рассылку прямо в бота (чтобы сохранились премиум-эмодзи)."""
    uid = request["uid"]
    kind = (await request.json()).get("kind")
    if kind not in ("greeting", "broadcast"):
        return fail("bad_kind")
    awaiting[uid] = kind
    what = "новое приветствие" if kind == "greeting" else "текст рассылки"
    try:
        await bot.send_message(uid, f"✍️ Пришли <b>{what}</b> одним сообщением — можно с премиум-эмодзи и форматированием.\n/cancel — отмена.")
    except TelegramAPIError:
        awaiting.pop(uid, None)
        return fail("start_bot", 409)
    return ok()


@routes.get("/api/admin/channels")
async def a_channels(request: web.Request):
    return ok(channels=db.list_channels())


@routes.post("/api/admin/channels")
async def a_channel_add(request: web.Request):
    b = await request.json()
    ref = str(b.get("ref", "")).strip()
    for p in ("https://t.me/", "http://t.me/", "t.me/"):
        if ref.startswith(p):
            ref = "@" + ref[len(p) :].split("/")[0].split("?")[0]
    if not ref:
        return fail("bad_ref")
    if not ref.startswith("@") and not ref.lstrip("-").isdigit():
        ref = "@" + ref
    try:
        chat = await bot.get_chat(int(ref) if ref.lstrip("-").isdigit() else ref)
        me_member = await bot.get_chat_member(chat.id, (await bot.me()).id)
    except TelegramAPIError:
        return fail("chat_not_found")
    if me_member.status not in ("administrator", "creator"):
        return fail("bot_not_admin")
    link = str(b.get("link", "")).strip() or (f"https://t.me/{chat.username}" if chat.username else "")
    if not link:
        return fail("need_link")
    stored_ref = f"@{chat.username}" if chat.username else str(chat.id)
    db.add_channel(stored_ref, str(b.get("title", "")).strip() or chat.title or stored_ref, link)
    return ok(channels=db.list_channels())


@routes.post("/api/admin/channels/delete")
async def a_channel_del(request: web.Request):
    db.del_channel(int((await request.json())["id"]))
    return ok(channels=db.list_channels())


@routes.get("/api/admin/settings")
async def a_settings_get(request: web.Request):
    return ok(settings={k: db.get_int(k) for k in ("free_gens", "pack_size", "pack_price", "premium_price")})


@routes.post("/api/admin/settings")
async def a_settings_set(request: web.Request):
    b = await request.json()
    for k in ("free_gens", "pack_size", "pack_price", "premium_price"):
        if k in b:
            v = int(b[k])
            if v < (0 if k == "free_gens" else 1) or v > 100000:
                return fail("bad_value")
            db.set_setting(k, str(v))
    return ok()


@routes.post("/api/admin/broadcast")
async def a_broadcast(request: web.Request):
    from .handlers import run_broadcast

    if broadcast_state["running"]:
        return fail("running")
    html = str((await request.json()).get("html", "")).strip()
    if not html:
        return fail("bad_text")
    asyncio.create_task(run_broadcast(html, request["uid"]))
    return ok()


# --------------------------------------------------------------------------------------
# статика
# --------------------------------------------------------------------------------------
@routes.get("/api/pending")
async def pending_photo(request: web.Request):
    p = tmp_path("pending", request["uid"])
    if not p.exists():
        return fail("no_pending", 404)
    return web.Response(body=p.read_bytes(), content_type="application/octet-stream", headers={"Cache-Control": "no-store"})


@routes.get("/")
async def index(request: web.Request):
    ver = str(int(max(f.stat().st_mtime for f in WEBAPP_DIR.iterdir() if f.is_file())))
    html = (WEBAPP_DIR / "index.html").read_text(encoding="utf-8").replace("{{V}}", ver)
    return web.Response(text=html, content_type="text/html", headers={"Cache-Control": "no-cache"})


_demo_cache: dict[str, bytes] = {}


_DEMO_PHOTO = WEBAPP_DIR / "demo_photo.jpg"


def _demo_avatar(n: int = 512):
    """Картинка для обучения и демо-рамок: фото из webapp/demo_photo.jpg, иначе нарисованный портрет."""
    if _DEMO_PHOTO.exists():
        return imaging.square_avatar(imaging.open_image(_DEMO_PHOTO.read_bytes()), n)
    return imaging.demo_avatar(n)


@routes.get("/demo/avatar.png")
async def demo_avatar_png(request: web.Request):
    return web.Response(body=imaging.png_bytes(_demo_avatar(1024)), content_type="image/png")


@routes.get("/demo/{sid}.webp")
async def demo_frame(request: web.Request):
    sid = request.match_info["sid"]
    if sid not in imaging.STYLES:
        raise web.HTTPNotFound()
    if sid not in _demo_cache:
        def work() -> bytes:
            av = _demo_avatar()
            _, c1, c2 = imaging.make_palettes(av)[0]
            return imaging.webp_bytes(imaging.render_frame(av, sid, c1, c2, 384), 88)

        _demo_cache[sid] = await asyncio.to_thread(work)
    return web.Response(body=_demo_cache[sid], content_type="image/webp", headers={"Cache-Control": "public, max-age=86400"})


@routes.get("/healthz")
async def health(request: web.Request):
    return web.Response(text="ok")


def make_app() -> web.Application:
    app = web.Application(middlewares=[auth_mw], client_max_size=MAX_UPLOAD + 1024 * 1024)
    app.add_routes(routes)
    app.router.add_static("/static/", WEBAPP_DIR, show_index=False, append_version=True)
    return app
