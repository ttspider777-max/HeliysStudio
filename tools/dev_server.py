"""Локальный предпросмотр Mini App в браузере (без Telegram, без отправки сообщений)."""
import os, sys
os.environ["DEV"] = "1"
os.environ["DATA_DIR"] = os.path.join(os.path.dirname(__file__), "..", "data", "dev")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from aiohttp import web
from app.server import make_app
web.run_app(make_app(), host="127.0.0.1", port=8765, print=lambda *_: None)
