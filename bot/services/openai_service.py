from openai import AsyncOpenAI

from bot.config import settings
from bot.services.profile_analyzer import ProfileScores
from bot.utils.emoji import plain

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI | None:
    global _client
    if not settings.openai_api_key:
        return None
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


FALLBACK_VERDICTS = [
    "Профиль выше среднего. Подкачай подарки — и будешь в топ-10%.",
    "Крепкий середнячок, но юзернейм подкачал.",
    "Отличная база! Докрути описание профиля и будет огонь 🔥",
    "Неплохо, но есть куда расти. Подарки — твоя зона роста.",
    "Солидный профиль, видно что не первый день в Telegram.",
]


def _fallback_verdict(scores: ProfileScores) -> str:
    weakest = min(
        [("аватарку", scores.avatar, 25), ("юзернейм", scores.username, 25),
         ("подарки", scores.gifts, 25), ("описание профиля", scores.bio, 15), ("возраст", scores.age, 10)],
        key=lambda x: x[1] / x[2],
    )
    if scores.total >= 85:
        return f"Топовый профиль! Ты в элите Telegram {plain('trophy')}"
    if scores.total >= 70:
        return f"Профиль выше среднего. Подкачай {weakest[0]} — и будешь в топ-10%."
    if scores.total >= 50:
        return f"Крепкий середнячок, но {weakest[0]} подкачал."
    return f"Есть потенциал! Начни с {weakest[0]} — это даст быстрый буст."


async def generate_verdict(
    username: str | None,
    scores: ProfileScores,
    is_self: bool = True,
) -> str:
    client = get_client()
    if not client:
        return _fallback_verdict(scores)

    name = f"@{username}" if username else "пользователь"
    prompt = f"""Ты — дерзкий, но дружелюбный бот PeterRate. Напиши вердикт профиля Telegram в 1-2 предложения.
Профиль: {name}, итог {scores.total}/100.
Аватар {scores.avatar}/25, юзернейм {scores.username}/25, подарки {scores.gifts}/25.
Подарки (реальные данные API, не выдумывай): {scores.gifts_summary}
Описание профиля {scores.bio}/15, возраст {scores.age}/10.
{"Это оценка своего профиля." if is_self else "Это оценка чужого профиля."}
Стиль: живой, с лёгким юмором, без markdown, до 120 символов.
Если упоминаешь подарки — опирайся только на строку «Подарки» выше."""

    try:
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.9,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text[:200] if text else _fallback_verdict(scores)
    except Exception:
        return _fallback_verdict(scores)


async def generate_compare_verdict(
    my_scores: ProfileScores,
    other_scores: ProfileScores,
    my_name: str,
    other_name: str,
) -> str:
    client = get_client()
    diff = my_scores.total - other_scores.total
    if not client:
        if diff > 10:
            return f"Ты впереди на {diff} баллов! {other_name} пусть подтягивается 😎"
        if diff < -10:
            return f"{other_name} обходит тебя на {abs(diff)} баллов. Пора апгрейдить профиль!"
        return f"Почти равны! Разница минимальная — битва продолжается {plain('swords')}"

    prompt = f"""Сравни два профиля Telegram коротко (1-2 предложения, дерзко, с юмором):
{my_name}: {my_scores.total}/100
{other_name}: {other_scores.total}/100
Без markdown."""

    try:
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.9,
        )
        return (resp.choices[0].message.content or "").strip()[:200]
    except Exception:
        if diff > 0:
            return f"Ты побеждаешь с отрывом {diff} баллов! {plain('trophy')}"
        if diff < 0:
            return f"{other_name} впереди на {abs(diff)} баллов {plain('swords')}"
        return f"Ничья! Абсолютное равенство {plain('handshake')}"
