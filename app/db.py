import aiosqlite

async def init_db():
    async with aiosqlite.connect("bot.db") as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT
            )
        ''')
        await db.commit()

async def save_name(user_id: int, name: str):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("INSERT OR REPLACE INTO users (user_id, name) VALUES (?, ?)", (user_id, name))
        await db.commit()

async def get_name(user_id: int):
    async with aiosqlite.connect("bot.db") as db:
        cursor = await db.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return row[0] if row else None
