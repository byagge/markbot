"""Premium Telegram custom emoji helpers.

Fill IDs in .env as EMOJI_FIRE=5368324170671202286 etc.
Get IDs from @PremiumEmoji bot or from message entities.
"""

from __future__ import annotations

from bot.config import settings

# key -> (fallback unicode, settings attribute)
CATALOG: dict[str, tuple[str, str]] = {
    "fire": ("🔥", "emoji_fire"),
    "trophy": ("🏆", "emoji_trophy"),
    "star": ("⭐", "emoji_star"),
    "people": ("👥", "emoji_people"),
    "question": ("❓", "emoji_question"),
    "back": ("⬅️", "emoji_back"),
    "share": ("📤", "emoji_share"),
    "refresh": ("🔄", "emoji_refresh"),
    "swords": ("⚔️", "emoji_swords"),
    "globe": ("🌍", "emoji_globe"),
    "gift": ("🎁", "emoji_gift"),
    "letters": ("🔤", "emoji_letters"),
    "chart": ("📊", "emoji_chart"),
    "search": ("🔍", "emoji_search"),
    "sparkles": ("✨", "emoji_sparkles"),
    "picture": ("🖼", "emoji_picture"),
    "memo": ("📝", "emoji_memo"),
    "hourglass": ("⏳", "emoji_hourglass"),
    "speech": ("💬", "emoji_speech"),
    "warning": ("⚠️", "emoji_warning"),
    "bulb": ("💡", "emoji_bulb"),
    "megaphone": ("📢", "emoji_megaphone"),
    "check": ("✅", "emoji_check"),
    "tools": ("🛠", "emoji_tools"),
    "loudspeaker": ("📣", "emoji_loudspeaker"),
    "chart_up": ("📈", "emoji_chart_up"),
    "green": ("🟢", "emoji_green"),
    "gold": ("🥇", "emoji_gold"),
    "silver": ("🥈", "emoji_silver"),
    "bronze": ("🥉", "emoji_bronze"),
    "point_down": ("👇", "emoji_point_down"),
    "user": ("👤", "emoji_user"),
    "medal": ("🏅", "emoji_medal"),
    "handshake": ("🤝", "emoji_handshake"),
    "party": ("🎉", "emoji_party"),
    "cross": ("❌", "emoji_cross"),
    "plus": ("➕", "emoji_plus"),
    "bullet": ("▪️", "emoji_bullet"),
    "home": ("🏠", "emoji_home"),
}


def _fallback(key: str) -> str:
    return CATALOG.get(key, ("•", ""))[0]


def emoji_id(key: str) -> str:
    attr = CATALOG.get(key, ("", ""))[1]
    if not attr:
        return ""
    return (getattr(settings, attr, "") or "").strip()


def e(key: str) -> str:
    """HTML premium emoji for message text."""
    fb = _fallback(key)
    eid = emoji_id(key)
    if eid:
        return f'<tg-emoji emoji-id="{eid}">{fb}</tg-emoji>'
    return fb


def plain(key: str) -> str:
    """Plain unicode fallback (inline queries, alerts)."""
    return _fallback(key)


def btn_label(key: str, text: str) -> tuple[str, str | None]:
    """Button text + optional icon_custom_emoji_id."""
    eid = emoji_id(key)
    if eid:
        return text, eid
    return f"{_fallback(key)} {text}", None


def stars(count: int) -> str:
    if count <= 0:
        return ""
    one = e("star")
    return one * count
