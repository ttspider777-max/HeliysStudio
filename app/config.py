import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    env = BASE_DIR / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = {int(x) for x in os.environ.get("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()}
WEBAPP_URL = os.environ.get("WEBAPP_URL", "").rstrip("/")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
DEV = os.environ.get("DEV", "0") == "1"

DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
TMP_DIR = DATA_DIR / "tmp"
DB_PATH = DATA_DIR / "storyframe.db"
WEBAPP_DIR = BASE_DIR / "webapp"

DATA_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Значения по умолчанию (админ может менять их в Mini App)
DEFAULTS = {
    "free_gens": "5",
    "pack_size": "10",
    "pack_price": "15",
    "premium_price": "50",
    "greeting": (
        "<b>Привет, {name}!</b>\n\n"
        "Добро пожаловать в <b>HeliysStudio</b>. Я нарежу твоё фото на сториз и подберу красивую рамку под цвет аватарки.\n\n"
        "Жми кнопку ниже 👇"
    ),
}
