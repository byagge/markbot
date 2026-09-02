import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.enums import OwnedGiftType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import OwnedGiftRegular, OwnedGiftUnique

from bot.services import user_client

logger = logging.getLogger(__name__)


@dataclass
class ParsedGift:
    is_unique: bool = False
    star_count: int = 0
    was_refunded: bool = False
    model_name: str = ""
    rarity_per_mille: int = 1000
    rarity_label: str = ""
    transfer_stars: int = 0
    total_count: int = 0
    remaining_count: int = 0
    is_premium: bool = False
    upgrade_star_count: int = 0


async def _paginate_gifts(method, id_kw: dict, extra_kw: dict | None = None) -> tuple[int, list]:
    gifts: list = []
    total_count = 0
    offset = ""
    extra_kw = extra_kw or {}

    for _ in range(40):
        try:
            result = await method(
                limit=100,
                offset=offset,
                sort_by_price=True,
                **id_kw,
                **extra_kw,
            )
        except TelegramBadRequest as exc:
            logger.info("gifts fetch failed %s %s: %s", method.__name__, {**id_kw, **extra_kw}, exc)
            return 0, []
        except Exception as exc:
            logger.warning("gifts fetch error %s %s: %s", method.__name__, {**id_kw, **extra_kw}, exc)
            return 0, []

        total_count = max(total_count, result.total_count)
        gifts.extend(result.gifts)
        if not result.next_offset:
            break
        offset = result.next_offset

    if total_count < len(gifts):
        total_count = len(gifts)
    return total_count, gifts


async def _fetch_via_bot(bot: Bot, user_id: int, username: str | None) -> tuple[int, list]:
    attempts: list[tuple[str, object, dict, dict]] = [
        ("user_gifts", bot.get_user_gifts, {"user_id": user_id}, {}),
        ("chat_id", bot.get_chat_gifts, {"chat_id": user_id}, {}),
        ("chat_id_profile", bot.get_chat_gifts, {"chat_id": user_id}, {"exclude_unsaved": True}),
        ("chat_id_all", bot.get_chat_gifts, {"chat_id": user_id}, {"exclude_unsaved": False}),
    ]

    if username:
        uname = username.lstrip("@")
        attempts.extend([
            ("chat_username", bot.get_chat_gifts, {"chat_id": f"@{uname}"}, {}),
            ("chat_username_profile", bot.get_chat_gifts, {"chat_id": f"@{uname}"}, {"exclude_unsaved": True}),
        ])

    best_total = 0
    best_gifts: list = []
    best_source = "none"

    for label, method, id_kw, extra_kw in attempts:
        total, gifts = await _paginate_gifts(method, id_kw, extra_kw)
        if total > best_total or (total == best_total and len(gifts) > len(best_gifts)):
            best_total, best_gifts, best_source = total, gifts, label
        if best_total > 0 and len(best_gifts) >= best_total:
            break

    logger.info(
        "bot gifts uid=%s username=%s: total=%s fetched=%s source=%s",
        user_id,
        username,
        best_total,
        len(best_gifts),
        best_source,
    )
    return best_total, best_gifts


async def fetch_all_user_gifts(
    bot: Bot,
    user_id: int,
    username: str | None = None,
) -> tuple[int, list]:
    bot_total, bot_gifts = await _fetch_via_bot(bot, user_id, username)

    if user_client.is_ready():
        user_total, user_gifts = await user_client.fetch_saved_gifts(user_id, username)
        if user_total > bot_total or (user_total == bot_total and len(user_gifts) > len(bot_gifts)):
            logger.info(
                "gifts for uid=%s username=%s: total=%s fetched=%s source=user_client",
                user_id,
                username,
                user_total,
                len(user_gifts),
            )
            return user_total, user_gifts

    return bot_total, bot_gifts


def _normalize_gift(gift_item) -> ParsedGift | None:
    if isinstance(gift_item, ParsedGift):
        return gift_item

    if gift_item.__class__.__name__ == "Gift":
        return _from_pyrogram_gift(gift_item)

    if isinstance(gift_item, OwnedGiftUnique):
        gift = gift_item.gift
        model = gift.model
        return ParsedGift(
            is_unique=True,
            model_name=(model.name if model else None) or gift.base_name or "NFT",
            rarity_per_mille=model.rarity_per_mille if model else 1000,
            rarity_label=(model.rarity or "") if model else "",
            transfer_stars=gift_item.transfer_star_count or 0,
        )

    if isinstance(gift_item, OwnedGiftRegular):
        if gift_item.was_refunded:
            return ParsedGift(was_refunded=True)
        gift = gift_item.gift
        if not gift:
            return None
        return ParsedGift(
            star_count=gift.star_count or 0,
            total_count=gift.total_count or 0,
            remaining_count=gift.remaining_count or 0,
            is_premium=bool(gift.is_premium),
            upgrade_star_count=gift.upgrade_star_count or 0,
        )

    if getattr(gift_item, "type", None) == OwnedGiftType.UNIQUE:
        gift = gift_item.gift
        model = getattr(gift, "model", None)
        return ParsedGift(
            is_unique=True,
            model_name=getattr(model, "name", None) or getattr(gift, "base_name", "NFT"),
            transfer_stars=getattr(gift_item, "transfer_star_count", 0) or 0,
        )

    gift = getattr(gift_item, "gift", None)
    if gift:
        return ParsedGift(star_count=getattr(gift, "star_count", 0) or 0)
    return None


def _from_pyrogram_gift(gift) -> ParsedGift | None:
    from pyrogram import enums
    from pyrogram.types import Gift

    if not isinstance(gift, Gift):
        return None

    if gift.was_refunded:
        return ParsedGift(was_refunded=True)

    if gift.type == enums.GiftType.UPGRADED:
        model_name = gift.title or gift.name or "NFT"
        rarity_pm = 1000
        rarity_label = ""
        if gift.model:
            model_name = gift.model.name or model_name
            rarity = gift.model.rarity
            if rarity is not None:
                rarity_label = type(rarity).__name__.replace("UpgradedGiftAttributeRarity", "").lower()
                per_mille = getattr(rarity, "per_mille", None)
                if per_mille is not None:
                    rarity_pm = per_mille
        return ParsedGift(
            is_unique=True,
            model_name=model_name,
            rarity_per_mille=rarity_pm,
            rarity_label=rarity_label,
            transfer_stars=gift.transfer_star_count or 0,
        )

    limits = gift.overall_limits
    return ParsedGift(
        star_count=gift.star_count or 0,
        total_count=limits.total_count or 0 if limits else 0,
        remaining_count=limits.remaining_count or 0 if limits else 0,
        is_premium=bool(gift.is_premium),
        upgrade_star_count=gift.upgrade_star_count or 0,
    )


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


def _gift_label(parsed: ParsedGift) -> str:
    if parsed.is_unique:
        if parsed.rarity_per_mille and parsed.rarity_per_mille < 50:
            return f"NFT «{parsed.model_name}» (редкий {parsed.rarity_per_mille}/1000)"
        return f"NFT «{parsed.model_name}»"
    if parsed.total_count:
        return f"лимитированный ({parsed.star_count}⭐)"
    if parsed.is_premium:
        return f"Premium ({parsed.star_count}⭐)"
    return f"{parsed.star_count}⭐"


def _model_points(parsed: ParsedGift) -> float:
    if parsed.was_refunded:
        return 0.0

    if parsed.is_unique:
        points = max(2.0, (1000 - parsed.rarity_per_mille) / 40)
        crafted = parsed.rarity_label.lower()
        if crafted == "legendary":
            points += 6
        elif crafted == "epic":
            points += 4
        elif crafted == "rare":
            points += 2
        elif crafted == "uncommon":
            points += 1
        transfer = parsed.transfer_stars
        if transfer >= 1000:
            points += 3
        elif transfer >= 500:
            points += 2
        return min(18.0, points)

    points = min(6.0, parsed.star_count / 30)
    if parsed.total_count:
        scarcity = parsed.remaining_count or parsed.total_count
        if scarcity <= 100:
            points += 4
        elif scarcity <= 1000:
            points += 2
        else:
            points += 1
    if parsed.is_premium:
        points += 1.5
    if parsed.upgrade_star_count:
        points += 1
    return min(10.0, points)


def _build_gifts_summary(count: int, visible: list[ParsedGift]) -> str:
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
        return 0, 0, "нет на профиле или скрыты", 0, "подарков нет"

    parsed = [p for g in gifts if (p := _normalize_gift(g)) and not p.was_refunded]
    count = max(total_count, len(parsed))
    if count <= 0:
        return 0, 0, "нет на профиле или скрыты", 0, "подарков нет"

    model_scores = [_model_points(g) for g in parsed]
    total_model = sum(model_scores)
    avg_model = total_model / len(parsed)

    unique_count = sum(1 for g in parsed if g.is_unique)
    total_stars = sum(
        g.star_count + (g.transfer_stars or 750 if g.is_unique else 0)
        for g in parsed
    )

    quantity_pts = min(8, count * 1.5)
    model_pts = min(17, avg_model * 1.4 + min(6, unique_count * 1.5))
    score = min(25, int(quantity_pts + model_pts))

    summary = _build_gifts_summary(count, parsed)

    if unique_count and count >= 3:
        note = f"{_plural_gifts(count)} ({unique_count} NFT) — легенда"
    elif unique_count:
        note = f"{_plural_gifts(count)}, {unique_count} NFT"
    elif count >= 5:
        note = f"{_plural_gifts(count)} — красавчик"
    else:
        note = _plural_gifts(count)

    return score, count, note, total_stars, summary
