import re

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, User


async def resolve_target_user(message: Message, bot: Bot) -> User | None:
    """Resolve user from forward or @username via getChat."""
    if message.forward_origin and getattr(message.forward_origin, "sender_user", None):
        return message.forward_origin.sender_user
    if message.forward_from:
        return message.forward_from

    username: str | None = None
    if message.text:
        match = re.search(r"@([a-zA-Z0-9_]{4,32})", message.text.strip())
        if match:
            username = match.group(1)
    if not username and message.entities and message.text:
        for ent in message.entities:
            if ent.type == "mention":
                username = message.text[ent.offset + 1 : ent.offset + ent.length]
                break

    if not username:
        return None

    try:
        chat = await bot.get_chat(f"@{username}")
        return User(
            id=chat.id,
            is_bot=bool(getattr(chat, "is_bot", False)),
            first_name=chat.first_name or username,
            last_name=chat.last_name,
            username=chat.username or username,
            is_premium=bool(getattr(chat, "is_premium", False)),
        )
    except TelegramBadRequest:
        return None


async def fetch_profile_description(bot: Bot, user_id: int) -> str | None:
    try:
        chat = await bot.get_chat(user_id)
        bio = getattr(chat, "bio", None)
        return bio.strip() if bio else None
    except TelegramBadRequest:
        return None


async def user_has_photo(bot: Bot, user_id: int) -> bool:
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        return bool(photos.total_count)
    except TelegramBadRequest:
        return True
