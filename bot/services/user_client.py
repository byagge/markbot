"""Optional Telegram user account (Pyrogram MTProto) for gifts and username resolution."""

from __future__ import annotations

import logging

from aiogram.types import User

logger = logging.getLogger(__name__)

_client = None
_ready = False


async def init(api_id: int, api_hash: str, session: str) -> bool:
    global _client, _ready
    if not api_id or not api_hash or not session.strip():
        return False

    try:
        from pyrogram import Client

        _client = Client(
            "profilemark_user",
            api_id=api_id,
            api_hash=api_hash,
            session_string=session.strip(),
            in_memory=True,
            no_updates=True,
        )
        await _client.start()
        me = await _client.get_me()
        logger.info("Pyrogram user client ready: %s (@%s)", me.id, me.username)
        _ready = True
        return True
    except Exception:
        logger.exception("Failed to init Pyrogram user client")
        if _client:
            try:
                await _client.stop()
            except Exception:
                pass
        _client = None
        _ready = False
        return False


async def close() -> None:
    global _client, _ready
    if _client:
        try:
            await _client.stop()
        except Exception:
            pass
    _client = None
    _ready = False


def is_ready() -> bool:
    return _ready and _client is not None


def _to_aiogram_user(u) -> User:
    return User(
        id=u.id,
        is_bot=bool(u.is_bot),
        first_name=u.first_name or "user",
        last_name=u.last_name,
        username=u.username,
        is_premium=bool(u.is_premium),
    )


async def _resolve_peer(user_id: int | None = None, username: str | None = None):
    """Resolve and cache peer — required before get_chat_gifts by numeric id."""
    if username:
        return await _client.get_users(username.lstrip("@"))
    if user_id:
        return await _client.get_users(user_id)
    return None


async def resolve_user(username: str | None = None, user_id: int | None = None) -> User | None:
    if not is_ready():
        return None

    try:
        u = await _resolve_peer(user_id=user_id, username=username)
        if u is None:
            return None
        return _to_aiogram_user(u)
    except Exception as exc:
        logger.info("pyrogram resolve failed %s %s: %s", username, user_id, exc)
        return None


async def fetch_profile_bio(user_id: int | None = None, username: str | None = None) -> str | None:
    if not is_ready():
        return None

    try:
        u = await _resolve_peer(user_id=user_id, username=username)
        if u is None:
            return None
        bio = getattr(u, "bio", None)
        if bio and bio.strip():
            return bio.strip()
    except Exception as exc:
        logger.info("pyrogram bio failed: %s", exc)
    return None


async def fetch_saved_gifts(user_id: int, username: str | None = None) -> tuple[int, list]:
    if not is_ready():
        return 0, []

    gifts: list = []
    total = 0

    try:
        peer = await _resolve_peer(user_id=user_id, username=username)
        if peer is None:
            return 0, []
        chat_id = peer.id
    except Exception as exc:
        logger.info("pyrogram peer resolve failed uid=%s username=%s: %s", user_id, username, exc)
        return 0, []

    try:
        total = await _client.get_chat_gifts_count(chat_id)
    except Exception as exc:
        logger.info("pyrogram gifts count failed uid=%s: %s", chat_id, exc)

    try:
        async for gift in _client.get_chat_gifts(
            chat_id,
            exclude_unsaved=True,
            exclude_hosted=True,
            sort_by_price=True,
        ):
            gifts.append(gift)
    except Exception as exc:
        logger.info("pyrogram gifts fetch failed uid=%s: %s", chat_id, exc)
        if total > 0:
            return total, gifts
        return 0, []

    count = max(total, len(gifts))
    return count, gifts
