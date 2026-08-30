import aiosqlite
from pathlib import Path

from bot.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    is_premium INTEGER DEFAULT 0,
    nav_message_id INTEGER,
    registered_at TEXT DEFAULT (datetime('now')),
    last_active TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rater_telegram_id INTEGER NOT NULL,
    target_telegram_id INTEGER,
    target_username TEXT,
    total_score INTEGER NOT NULL,
    avatar_score INTEGER NOT NULL,
    username_score INTEGER NOT NULL,
    gifts_score INTEGER NOT NULL,
    bio_score INTEGER NOT NULL,
    age_score INTEGER NOT NULL,
    gifts_count INTEGER DEFAULT 0,
    verdict TEXT,
    is_self INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS required_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT UNIQUE NOT NULL,
    channel_title TEXT NOT NULL,
    channel_link TEXT NOT NULL,
    invite_link TEXT,
    joins_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS broadcasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    sent_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_ratings_total ON ratings(total_score DESC);
CREATE INDEX IF NOT EXISTS idx_ratings_gifts ON ratings(gifts_score DESC);
CREATE INDEX IF NOT EXISTS idx_ratings_username ON ratings(username_score DESC);
CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
"""


class Database:
    def __init__(self, path: str | None = None):
        self.path = path or settings.database_path

    async def init(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.executescript(SCHEMA)
            await self._migrate(conn)
            await conn.commit()

    async def _migrate(self, conn: aiosqlite.Connection) -> None:
        cur = await conn.execute("PRAGMA table_info(required_channels)")
        cols = {row[1] for row in await cur.fetchall()}
        if "invite_link" not in cols:
            await conn.execute("ALTER TABLE required_channels ADD COLUMN invite_link TEXT")
        if "joins_count" not in cols:
            await conn.execute(
                "ALTER TABLE required_channels ADD COLUMN joins_count INTEGER DEFAULT 0"
            )

    async def connect(self) -> aiosqlite.Connection:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        conn = await aiosqlite.connect(self.path)
        conn.row_factory = aiosqlite.Row
        return conn


db = Database()
