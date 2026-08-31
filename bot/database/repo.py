from dataclasses import dataclass
from datetime import datetime, timedelta

import aiosqlite


@dataclass
class UserRow:
    id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    nav_message_id: int | None


@dataclass
class RatingRow:
    target_username: str | None
    total_score: int
    avatar_score: int
    username_score: int
    gifts_score: int
    bio_score: int
    age_score: int
    gifts_count: int
    verdict: str | None
    rater_telegram_id: int


class Repository:
    def __init__(self, db: aiosqlite.Connection):
        self.db = db

    async def upsert_user(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None = None,
        is_premium: bool = False,
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO users (telegram_id, username, first_name, last_name, is_premium, last_active)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                is_premium = excluded.is_premium,
                last_active = datetime('now')
            """,
            (telegram_id, username, first_name, last_name, int(is_premium)),
        )
        await self.db.commit()

    async def set_nav_message(self, telegram_id: int, message_id: int) -> None:
        await self.db.execute(
            """
            INSERT INTO users (telegram_id, nav_message_id, last_active)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(telegram_id) DO UPDATE SET
                nav_message_id = excluded.nav_message_id,
                last_active = datetime('now')
            """,
            (telegram_id, message_id),
        )
        await self.db.commit()

    async def get_nav_message(self, telegram_id: int) -> int | None:
        cur = await self.db.execute(
            "SELECT nav_message_id FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cur.fetchone()
        return row["nav_message_id"] if row else None

    async def find_by_username(self, username: str) -> dict | None:
        cur = await self.db.execute(
            """
            SELECT telegram_id, username, first_name, is_premium
            FROM users
            WHERE username = ? COLLATE NOCASE
            ORDER BY last_active DESC
            LIMIT 1
            """,
            (username.lstrip("@"),),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def find_rated_by_username(self, username: str) -> dict | None:
        cur = await self.db.execute(
            """
            SELECT r.target_telegram_id AS telegram_id,
                   r.target_username AS username,
                   u.first_name AS first_name,
                   COALESCE(u.is_premium, 0) AS is_premium
            FROM ratings r
            LEFT JOIN users u ON u.telegram_id = r.target_telegram_id
            WHERE r.target_username = ? COLLATE NOCASE
              AND r.target_telegram_id IS NOT NULL
            ORDER BY r.created_at DESC
            LIMIT 1
            """,
            (username.lstrip("@"),),
        )
        row = await cur.fetchone()
        return dict(row) if row else None

    async def save_rating(
        self,
        rater_id: int,
        target_id: int | None,
        target_username: str | None,
        scores: dict,
        verdict: str,
        is_self: bool,
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO ratings (
                rater_telegram_id, target_telegram_id, target_username,
                total_score, avatar_score, username_score, gifts_score,
                bio_score, age_score, gifts_count, verdict, is_self
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rater_id,
                target_id,
                target_username,
                scores["total"],
                scores["avatar"],
                scores["username"],
                scores["gifts"],
                scores["bio"],
                scores["age"],
                scores.get("gifts_count", 0),
                verdict,
                int(is_self),
            ),
        )
        await self.db.commit()

    async def get_last_other_rating(self, rater_id: int, target_id: int) -> RatingRow | None:
        cur = await self.db.execute(
            """
            SELECT target_username, total_score, avatar_score, username_score,
                   gifts_score, bio_score, age_score, gifts_count, verdict, rater_telegram_id
            FROM ratings
            WHERE rater_telegram_id = ? AND target_telegram_id = ? AND is_self = 0
            ORDER BY created_at DESC LIMIT 1
            """,
            (rater_id, target_id),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return RatingRow(**dict(row))

    async def get_user_best_rating(self, telegram_id: int) -> RatingRow | None:
        cur = await self.db.execute(
            """
            SELECT target_username, total_score, avatar_score, username_score,
                   gifts_score, bio_score, age_score, gifts_count, verdict, rater_telegram_id
            FROM ratings
            WHERE rater_telegram_id = ? AND is_self = 1
            ORDER BY total_score DESC, created_at DESC
            LIMIT 1
            """,
            (telegram_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return RatingRow(**dict(row))

    async def get_top(
        self, category: str = "general", limit: int = 10
    ) -> list[aiosqlite.Row]:
        order_map = {
            "general": "r.total_score",
            "gifts": "r.gifts_score",
            "username": "r.username_score",
        }
        order_col = order_map.get(category, "r.total_score")
        cur = await self.db.execute(
            f"""
            SELECT r.target_username, r.total_score, r.gifts_score, r.username_score,
                   r.rater_telegram_id, r.is_self
            FROM ratings r
            INNER JOIN (
                SELECT rater_telegram_id, MAX(total_score) AS max_score
                FROM ratings WHERE is_self = 1
                GROUP BY rater_telegram_id
            ) best ON r.rater_telegram_id = best.rater_telegram_id
                AND r.total_score = best.max_score
            WHERE r.is_self = 1 AND r.target_username IS NOT NULL
            GROUP BY r.rater_telegram_id
            ORDER BY {order_col} DESC
            LIMIT ?
            """,
            (limit,),
        )
        return await cur.fetchall()

    async def get_user_rank(self, telegram_id: int, category: str = "general") -> tuple[int, int] | None:
        order_map = {
            "general": "total_score",
            "gifts": "gifts_score",
            "username": "username_score",
        }
        order_col = order_map.get(category, "total_score")

        cur = await self.db.execute(
            f"""
            WITH best AS (
                SELECT rater_telegram_id, MAX({order_col}) as best_score
                FROM ratings WHERE is_self = 1
                GROUP BY rater_telegram_id
            ),
            ranked AS (
                SELECT rater_telegram_id, best_score,
                       ROW_NUMBER() OVER (ORDER BY best_score DESC) as rank
                FROM best
            )
            SELECT rank, best_score FROM ranked WHERE rater_telegram_id = ?
            """,
            (telegram_id,),
        )
        row = await cur.fetchone()
        if not row:
            return None
        return int(row["rank"]), int(row["best_score"])

    async def get_top10_threshold(self, category: str = "general") -> int | None:
        tops = await self.get_top(category, 10)
        if len(tops) < 10:
            return None
        order_map = {
            "general": "total_score",
            "gifts": "gifts_score",
            "username": "username_score",
        }
        col = order_map.get(category, "total_score")
        return int(tops[-1][col])

    # --- Admin: channels ---
    async def add_channel(
        self,
        channel_id: str,
        title: str,
        link: str,
        invite_link: str | None = None,
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO required_channels (channel_id, channel_title, channel_link, invite_link)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(channel_id) DO UPDATE SET
                channel_title = excluded.channel_title,
                channel_link = excluded.channel_link,
                invite_link = COALESCE(excluded.invite_link, required_channels.invite_link),
                is_active = 1
            """,
            (channel_id, title, link, invite_link),
        )
        await self.db.commit()

    async def set_invite_link(self, channel_id: str, invite_link: str) -> None:
        await self.db.execute(
            """
            UPDATE required_channels
            SET invite_link = ?, channel_link = ?
            WHERE channel_id = ?
            """,
            (invite_link, invite_link, channel_id),
        )
        await self.db.commit()

    async def increment_joins(self, channel_id: str) -> None:
        await self.db.execute(
            "UPDATE required_channels SET joins_count = joins_count + 1 WHERE channel_id = ?",
            (channel_id,),
        )
        await self.db.commit()

    async def increment_joins_by_invite(self, invite_link: str) -> bool:
        cur = await self.db.execute(
            """
            UPDATE required_channels
            SET joins_count = joins_count + 1
            WHERE invite_link = ? AND is_active = 1
            """,
            (invite_link,),
        )
        await self.db.commit()
        return cur.rowcount > 0

    async def get_channel_by_id(self, channel_id: str) -> aiosqlite.Row | None:
        cur = await self.db.execute(
            "SELECT * FROM required_channels WHERE channel_id = ? AND is_active = 1",
            (channel_id,),
        )
        return await cur.fetchone()

    async def total_channel_joins(self) -> int:
        cur = await self.db.execute(
            "SELECT COALESCE(SUM(joins_count), 0) as c FROM required_channels WHERE is_active = 1"
        )
        row = await cur.fetchone()
        return int(row["c"])

    async def remove_channel(self, channel_id: str) -> None:
        await self.db.execute(
            "UPDATE required_channels SET is_active = 0 WHERE channel_id = ?",
            (channel_id,),
        )
        await self.db.commit()

    async def get_active_channels(self) -> list[aiosqlite.Row]:
        cur = await self.db.execute(
            "SELECT * FROM required_channels WHERE is_active = 1 ORDER BY id"
        )
        return await cur.fetchall()

    # --- Admin: stats ---
    async def count_users_between(
        self, start: datetime | None = None, end: datetime | None = None
    ) -> int:
        if start and end:
            cur = await self.db.execute(
                "SELECT COUNT(*) as c FROM users WHERE registered_at >= ? AND registered_at < ?",
                (start.isoformat(), end.isoformat()),
            )
        elif start:
            cur = await self.db.execute(
                "SELECT COUNT(*) as c FROM users WHERE registered_at >= ?",
                (start.isoformat(),),
            )
        else:
            cur = await self.db.execute("SELECT COUNT(*) as c FROM users")
        row = await cur.fetchone()
        return int(row["c"])

    async def count_ratings_between(
        self, start: datetime | None = None, end: datetime | None = None
    ) -> int:
        if start and end:
            cur = await self.db.execute(
                "SELECT COUNT(*) as c FROM ratings WHERE created_at >= ? AND created_at < ?",
                (start.isoformat(), end.isoformat()),
            )
        elif start:
            cur = await self.db.execute(
                "SELECT COUNT(*) as c FROM ratings WHERE created_at >= ?",
                (start.isoformat(),),
            )
        else:
            cur = await self.db.execute("SELECT COUNT(*) as c FROM ratings")
        row = await cur.fetchone()
        return int(row["c"])

    async def count_users(self, since: datetime | None = None) -> int:
        return await self.count_users_between(since)

    async def count_ratings(self, since: datetime | None = None) -> int:
        return await self.count_ratings_between(since)

    async def count_active(self, since: datetime) -> int:
        cur = await self.db.execute(
            "SELECT COUNT(*) as c FROM users WHERE last_active >= ?",
            (since.isoformat(),),
        )
        row = await cur.fetchone()
        return int(row["c"])

    async def get_all_user_ids(self) -> list[int]:
        cur = await self.db.execute("SELECT telegram_id FROM users")
        rows = await cur.fetchall()
        return [int(r["telegram_id"]) for r in rows]

    async def log_broadcast(self, admin_id: int, text: str, sent: int, failed: int) -> None:
        await self.db.execute(
            "INSERT INTO broadcasts (admin_id, text, sent_count, failed_count) VALUES (?, ?, ?, ?)",
            (admin_id, text, sent, failed),
        )
        await self.db.commit()


def period_range(period: str) -> tuple[datetime | None, datetime | None, str]:
    """Return (start, end, label) for stats period."""
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    labels = {
        "today": "сегодня",
        "yesterday": "вчера",
        "week": "неделя",
        "last_week": "прошлая неделя",
        "month": "месяц",
        "all": "всё время",
    }
    if period == "today":
        return today, None, labels["today"]
    if period == "yesterday":
        return today - timedelta(days=1), today, labels["yesterday"]
    if period == "week":
        return today - timedelta(days=today.weekday()), None, labels["week"]
    if period == "last_week":
        week_start = today - timedelta(days=today.weekday())
        return week_start - timedelta(days=7), week_start, labels["last_week"]
    if period == "month":
        return today.replace(day=1), None, labels["month"]
    return None, None, labels["all"]


def period_start(period: str) -> datetime | None:
    start, _, _ = period_range(period)
    return start
