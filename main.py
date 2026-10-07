import asyncio
import logging
import sys

from aiohttp import web
from aiogram import Dispatcher
from aiogram.types import MenuButtonWebApp, WebAppInfo

from app import db
from app.config import BOT_TOKEN, HOST, PORT, WEBAPP_URL
from app.core import bot, cleanup_tmp
from app.handlers import router
from app.server import make_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("storyframe")


async def tmp_janitor():
    while True:
        await asyncio.sleep(1800)
        cleanup_tmp()


async def main():
    if not BOT_TOKEN:
        sys.exit("BOT_TOKEN не задан в .env")

    runner = web.AppRunner(make_app())
    await runner.setup()
    await web.TCPSite(runner, HOST, PORT).start()
    log.info("Mini App сервер: http://localhost:%s", PORT)

    me = await bot.me()
    log.info("Бот: @%s", me.username)
    if WEBAPP_URL:
        await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="Открыть", web_app=WebAppInfo(url=WEBAPP_URL)))
        log.info("Mini App URL: %s", WEBAPP_URL)
    else:
        log.warning("WEBAPP_URL пуст — кнопка Mini App не появится (см. README).")

    cleanup_tmp()
    asyncio.create_task(tmp_janitor())
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot, allowed_updates=["message", "callback_query", "pre_checkout_query"])


if __name__ == "__main__":
    asyncio.run(main())
