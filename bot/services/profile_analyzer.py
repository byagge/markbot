from dataclasses import dataclass
import hashlib
import re

from aiogram.types import User

from bot.utils.emoji import stars


@dataclass
class ProfileScores:
    avatar: int
    username: int
    gifts: int
    bio: int
    age: int
    gifts_count: int
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
        }


def _seed(user_id: int, salt: str) -> int:
    h = hashlib.md5(f"{user_id}:{salt}".encode()).hexdigest()
    return int(h[:8], 16)


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


def analyze_profile(user: User, has_photo: bool = True) -> ProfileScores:
    uid = user.id
    seed = _seed(uid, "profile")

    # Avatar — up to 25
    if not has_photo:
        avatar, avatar_note = 0, "нет фото / скрыто"
    else:
        avatar = 12 + (seed % 14)
        if user.is_premium:
            avatar = min(25, avatar + 3)
        avatar_note = "есть фото" if avatar >= 15 else "базовое"

    # Username — up to 25
    username_score, username_note = analyze_username(user.username)

    # Gifts — simulated (Bot API не отдаёт подарки), up to 25
    gifts_count = (seed % 8) if user.is_premium else (seed % 5)
    if gifts_count == 0:
        gifts, gifts_note = seed % 6, "подарков не видно"
    elif gifts_count <= 2:
        gifts = 10 + gifts_count * 3
        gifts_note = f"{gifts_count} подарка в профиле"
    elif gifts_count <= 5:
        gifts = 18 + (gifts_count - 2)
        gifts_note = f"{gifts_count} подарков — красавчик"
    else:
        gifts = 25
        gifts_note = f"{gifts_count} подарков — легенда"
    gifts = min(25, gifts)

    # Bio — up to 15 (simulated from seed + premium)
    bio_base = 5 + (seed % 11)
    if user.is_premium:
        bio_base += 2
    if user.first_name and len(user.first_name) > 2:
        bio_base += 1
    bio = min(15, bio_base)
    bio_note = "оформлено" if bio >= 10 else "минимум"

    # Age — up to 10 (mockup shows 15 but spec says 10; using 10 per spec)
    year = estimate_account_year(uid)
    age_map = {2013: 10, 2014: 10, 2015: 9, 2016: 8, 2017: 7, 2018: 6, 2019: 5, 2020: 4, 2021: 3, 2022: 2, 2023: 1, 2024: 0}
    age = age_map.get(year, 0)
    if year <= 2016:
        age_note = f"с {year} года — олдфаг"
    elif year <= 2020:
        age_note = f"с {year} года"
    else:
        age_note = "новый аккаунт"

    return ProfileScores(
        avatar=avatar,
        username=username_score,
        gifts=gifts,
        bio=bio,
        age=age,
        gifts_count=gifts_count,
        avatar_note=avatar_note,
        username_note=username_note,
        gifts_note=gifts_note,
        bio_note=bio_note,
        age_note=age_note,
    )
