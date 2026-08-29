import logging

from aiogram import Bot
from aiogram.enums import OwnedGiftType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import OwnedGiftRegular, OwnedGiftUnique

logger = logging.getLogger(__name__)


async def fetch_all_user_gifts(bot: Bot, user_id: int) -> tuple[int, list]:
    """Fetch all gifts via getUserGifts with pagination."""
    gifts: list = []
    total_count = 0
    offset = ""

    try:
        while True:
            result = await bot.get_user_gifts(
                user_id=user_id,
                offset=offset,
                limit=100,
                sort_by_price=True,
            )
            total_count = max(result.total_count, total_count)
            gifts.extend(result.gifts)
            if not result.next_offset:
                break
            offset = result.next_offset
    except TelegramBadRequest as exc:
        logger.info("getUserGifts failed for %s: %s", user_id, exc)
        return 0, []
    except Exception as exc:
        logger.warning("getUserGifts error for %s: %s", user_id, exc)
        return 0, []

    if total_count < len(gifts):
        total_count = len(gifts)

    return total_count, gifts


def _plural_gifts(count: int) -> str:
    n = abs(count) % 100
    n1 = n % 10
    if 11 <= n <= 19:
        return f"{count} подарков"
    if n1 == 1:
        return f"{count} подарок"
    if 2 <= n1 <= 4:
        return f"{count} подарка"
    return f"{count} подарков"


def _gift_label(gift_item) -> str:
    if isinstance(gift_item, OwnedGiftUnique):
        gift = gift_item.gift
        model = gift.model.name if gift.model else gift.base_name
        rarity = gift.model.rarity_per_mille if gift.model else 0
        if rarity and rarity < 50:
            return f"NFT «{model}» (редкий {rarity}/1000)"
        return f"NFT «{model}»"
    if isinstance(gift_item, OwnedGiftRegular):
        gift = gift_item.gift
        stars = gift.star_count if gift else 0
        if gift and gift.total_count:
            return f"лимитированный ({stars}⭐)"
        if gift and gift.is_premium:
            return f"Premium ({stars}⭐)"
        return f"{stars}⭐"
    if getattr(gift_item, "type", None) == OwnedGiftType.UNIQUE:
        gift = gift_item.gift
        model = getattr(getattr(gift, "model", None), "name", None) or getattr(gift, "base_name", "NFT")
        return f"NFT «{model}»"
    gift = getattr(gift_item, "gift", None)
    stars = getattr(gift, "star_count", 0) or 0
    return f"{stars}⭐"


def _model_points(gift_item) -> float:
    """Score a single gift by its model / rarity / star value."""
    if isinstance(gift_item, OwnedGiftUnique):
        gift = gift_item.gift
        model = gift.model
        rarity_pm = model.rarity_per_mille if model else 1000
        points = max(2.0, (1000 - rarity_pm) / 40)
        crafted = (model.rarity or "").lower() if model else ""
        if crafted == "legendary":
            points += 6
        elif crafted == "epic":
            points += 4
        elif crafted == "rare":
            points += 2
        elif crafted == "uncommon":
            points += 1
        transfer = gift_item.transfer_star_count or 0
        if transfer >= 1000:
            points += 3
        elif transfer >= 500:
            points += 2
        return min(18.0, points)

    if isinstance(gift_item, OwnedGiftRegular):
        if gift_item.was_refunded:
            return 0.0
        gift = gift_item.gift
        if not gift:
            return 0.0
        points = min(6.0, gift.star_count / 30)
        if gift.total_count:
            scarcity = gift.remaining_count or gift.total_count
            if scarcity <= 100:
                points += 4
            elif scarcity <= 1000:
                points += 2
            else:
                points += 1
        if gift.is_premium:
            points += 1.5
        if gift.upgrade_star_count:
            points += 1
        return min(10.0, points)

    if getattr(gift_item, "type", None) == OwnedGiftType.UNIQUE:
        return 8.0
    gift = getattr(gift_item, "gift", None)
    stars = getattr(gift, "star_count", 0) or 0
    return min(6.0, stars / 30)


def _build_gifts_summary(count: int, visible: list) -> str:
    if not visible:
        return "подарков нет"
    labels = [_gift_label(g) for g in visible[:20]]
    summary = f"{count} шт.: " + ", ".join(labels)
    if count > len(labels):
        summary += f" (+ещё {count - len(labels)})"
    return summary


def analyze_gifts(total_count: int, gifts: list) -> tuple[int, int, str, int, str]:
    """
    Returns: score (0-25), visible_count, note, total_stars, summary for AI
    """
    if total_count <= 0 or not gifts:
        return 0, 0, "подарков не видно", 0, "подарков не видно"

    visible = [
        g for g in gifts
        if not isinstance(g, OwnedGiftRegular) or not g.was_refunded
    ]
    count = max(total_count, len(visible))
    if count <= 0:
        return 0, 0, "подарков не видно", 0, "подарков не видно"

    model_scores = [_model_points(g) for g in visible]
    total_model = sum(model_scores)
    avg_model = total_model / len(visible)

    unique_count = sum(
        1 for g in visible
        if isinstance(g, OwnedGiftUnique) or getattr(g, "type", None) == OwnedGiftType.UNIQUE
    )
    total_stars = sum(
        (g.gift.star_count if isinstance(g, OwnedGiftRegular) and g.gift else 0)
        + (g.transfer_star_count or 750 if isinstance(g, OwnedGiftUnique) else 0)
        for g in visible
    )

    quantity_pts = min(8, count * 1.5)
    model_pts = min(17, avg_model * 1.4 + min(6, unique_count * 1.5))
    score = min(25, int(quantity_pts + model_pts))

    summary = _build_gifts_summary(count, visible)

    if unique_count and count >= 3:
        note = f"{_plural_gifts(count)} ({unique_count} NFT) — легенда"
    elif unique_count:
        note = f"{_plural_gifts(count)}, {unique_count} NFT"
    elif count >= 5:
        note = f"{_plural_gifts(count)} — красавчик"
    else:
        note = _plural_gifts(count)

    return score, count, note, total_stars, summary
