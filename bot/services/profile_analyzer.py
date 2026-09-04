from dataclasses import dataclass
import re

from aiogram import Bot
from aiogram.types import User

from bot.services import user_client
from bot.services.profile_fetcher import fetch_profile_description, user_has_photo
from bot.utils.emoji import stars


@dataclass
class ProfileScores:
    avatar: int
    username: int
    gifts: int
    bio: int
    age: int
    gifts_count: int
    gifts_summary: str = ""
    avatar_note: str = ""
    username_note: str = ""
    gifts_note: str = ""
    bio_note: str = ""
    age_note: str = ""

    @property
    def total(self) -> int:
        return self.avatar + self.username + self.gifts + self.bio + self.age

    def as_dict(self) -> dict:
        return {
            "avatar": self.avatar,
            "username": self.username,
            "gifts": self.gifts,
            "bio": self.bio,
            "age": self.age,
            "total": self.total,
            "gifts_count": self.gifts_count,
            "gifts_summary": self.gifts_summary,
        }


def scores_from_rating_row(row) -> ProfileScores:
    return ProfileScores(
        avatar=row.avatar_score,
        username=row.username_score,
        gifts=row.gifts_score,
        bio=row.bio_score,
        age=row.age_score,
        gifts_count=row.gifts_count,
    )


def estimate_account_year(user_id: int) -> int:
    if user_id < 50_000_000:
        return 2013
    if user_id < 200_000_000:
        return 2015
    if user_id < 500_000_000:
        return 2017
    if user_id < 1_000_000_000:
        return 2019
    if user_id < 2_000_000_000:
        return 2021
    if user_id < 5_000_000_000:
        return 2023
    return 2024


def stars_for_score(score: int) -> str:
    if score >= 90:
        return stars(5)
    if score >= 75:
        return stars(4)
    if score >= 60:
        return stars(3)
    if score >= 40:
        return stars(2)
    return stars(1)


def analyze_username(username: str | None) -> tuple[int, str]:
    if not username:
        return 0, "скрыт — 0 баллов"

    score = 25
    notes: list[str] = []

    length = len(username)
    if length <= 5:
        notes.append("короткий")
    elif length <= 8:
        score -= 2
    elif length <= 12:
        score -= 5
    else:
        score -= 10
        notes.append("длинный")

    if re.search(r"\d", username):
        score -= 6
        notes.append("есть цифры")
    if "_" in username:
        score -= 4
        notes.append("underscore")
    if re.search(r"[^a-zA-Z0-9_]", username):
        score -= 5

    if username.lower() in {"admin", "bot", "support", "official"}:
        score -= 8

    score = max(0, min(25, score))
    note = ", ".join(notes) if notes else "чистый ник"
    return score, note


def analyze_profile_description(description: str | None) -> tuple[int, str]:
    if not description or not description.strip():
        return 0, "не заполнено"

    text = description.strip()
    score = 4
    if len(text) >= 15:
        score += 3
    if len(text) >= 40:
        score += 3
    if len(text) >= 80:
        score += 2
    if "http" in text or "t.me/" in text or "@" in text:
        score += 2

    score = min(15, score)
    if score >= 12:
        note = "полное описание"
    elif score >= 8:
        note = "оформлено"
    else:
        note = "минимум"
    return score, note


def _avatar_score(user: User, has_photo: bool | None) -> tuple[int, str]:
    if has_photo is None:
        score = 16 if user.is_premium else 12
        return min(25, score), "фото не проверено"
    if not has_photo:
        return 0, "нет фото / скрыто"
    score = 18 if user.is_premium else 14
    return min(25, score), "есть фото"


def _age_score(user_id: int) -> tuple[int, str]:
    year = estimate_account_year(user_id)
    age_map = {
        2013: 10, 2014: 10, 2015: 9, 2016: 8, 2017: 7, 2018: 6,
        2019: 5, 2020: 4, 2021: 3, 2022: 2, 2023: 1, 2024: 0,
    }
    age = age_map.get(year, 0)
    if year <= 2016:
        note = f"с {year} года — олдфаг"
    elif year <= 2020:
        note = f"с {year} года"
    else:
        note = "новый аккаунт"
    return age, note


async def analyze_profile(
    bot: Bot,
    user: User,
    has_photo: bool | None = None,
    lookup_username: str | None = None,
) -> ProfileScores:
    lookup = (lookup_username or user.username or "").lstrip("@") or None

    await user_client.ensure_initialized()
    if lookup and user_client.is_ready():
        verified = await user_client.resolve_user(username=lookup)
        if verified:
            user = verified
            lookup = verified.username or lookup

    uid = user.id

    if has_photo is None:
        has_photo = await user_has_photo(bot, uid, lookup or user.username)

    avatar, avatar_note = _avatar_score(user, has_photo)
    username_score, username_note = analyze_username(user.username)

    from bot.services.gifts import analyze_gifts, fetch_all_user_gifts

    total_gifts, gifts_list = await fetch_all_user_gifts(bot, uid, lookup or user.username)
    gifts, gifts_count, gifts_note, _, gifts_summary = analyze_gifts(total_gifts, gifts_list)

    description = await fetch_profile_description(bot, uid, user.username)
    bio, bio_note = analyze_profile_description(description)

    age, age_note = _age_score(uid)

    return ProfileScores(
        avatar=avatar,
        username=username_score,
        gifts=gifts,
        bio=bio,
        age=age,
        gifts_count=gifts_count,
        gifts_summary=gifts_summary,
        avatar_note=avatar_note,
        username_note=username_note,
        gifts_note=gifts_note,
        bio_note=bio_note,
        age_note=age_note,
    )
