from db import init_db
from bot import dp, bot

# === MAIN ===
if __name__ == "__main__":
    import asyncio
    asyncio.run(init_db())
    dp.run_polling(bot)