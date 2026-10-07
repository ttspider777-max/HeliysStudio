"""Точка входа для хостингов, которые ищут bot.py: запускает то же, что и main.py."""
import asyncio

from main import main

if __name__ == "__main__":
    asyncio.run(main())
