from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError
from aiogram.types import Message, MessageOriginHiddenUser, User

from bot.database.repo import Repository
from bot.keyboards.reply import PICK_USER_REQUEST_ID

logger = logging.getLogger(__name__)

RESERVED_PATHS = {
    "joinchat", "addstickers", "share", "socks", "proxy", "c", "s", "iv",
    "addlist", "boost", "giftcode", "nft", "login", "setlanguage",
}

HOMOGLYPHS = str.maketrans({
    "А": "A", "а": "a", "В": "B", "Е": "E", "е": "e", "К": "K", "к": "k",
    "М": "M", "Н": "H", "О": "O", "о": "o", "Р": "P", "р": "p", "С": "C",
    "с": "c", "Т": "T", "У": "Y", "Х": "X", "х": "x", "І": "I", "і": "i",
})

USERNAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")
MENTION_RE = re.compile(r"@([A-Za-z][A-Za-z0-9_]{3,31})")
TME_RE = re.compile(
    r"(?:https?://)?(?:t\.me|telegram\.me|telegram\.dog)/([A-Za-z][A-Za-z0-9_]{3,31})",
    re.IGNORECASE,
)


@dataclass
class ResolveResult:
    user: User | None = None
    error: str | None = None
    has_photo: bool | None = None


def _clean_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    text = text.replace("\ufeff", "").replace("\u2060", "")
    text = text.replace("＠", "@")
    return text.translate(HOMOGLYPHS).strip()


def normalize_username(raw: str) -> str | None:
    value = _clean_text(raw).lstrip("@")
    if "/" in value:
        value = value.split("/", 1)[0]
    value = value.strip(".")
    if value.lower() in RESERVED_PATHS:
        return None
    if USERNAME_RE.fullmatch(value):
        return value
    return None


def extract_username(text: str) -> str | None:
    cleaned = _clean_text(text)
    tme = TME_RE.search(cleaned.replace(" ", ""))
    if tme:
        return normalize_username(tme.group(1))
    mention = MENTION_RE.search(cleaned)
    if mention:
        return normalize_username(mention.group(1))
    if cleaned.startswith("@"):
        return normalize_username(cleaned)
    return None


def user_from_chat(chat) -> User:
    first = chat.first_name or chat.title or chat.username or "user"
    return User(
        id=chat.id,
        is_bot=bool(getattr(chat, "is_bot", False)),
        first_name=first,
        last_name=getattr(chat, "last_name", None),
        username=chat.username,
        is_premium=bool(getattr(chat, "is_premium", False)),
    )


def user_from_row(telegram_id: int, username: str | None, first_name: str | None, is_premium: bool = False) -> User:
    return User(
        id=telegram_id,
        is_bot=False,
        first_name=first_name or username or "user",
        username=username,
        is_premium=is_premium,
    )


async def get_chat_user(bot: Bot, chat_id: int | str) -> User | None:
    try:
        chat = await bot.get_chat(chat_id)
        if getattr(chat, "type", None) in {"channel", "group", "supergroup"}:
            return None
        return user_from_chat(chat)
    except (TelegramBadRequest, TelegramForbiddenError) as exc:
        logger.info("getChat(%s) failed: %s", chat_id, exc)
        return None
    except TelegramAPIError as exc:
        logger.warning("getChat(%s) api error: %s", chat_id, exc)
        return None


async def resolve_target_user(message: Message, bot: Bot, repo: Repository | None = None) -> ResolveResult:
    if message.users_shared and message.users_shared.users:
        if message.users_shared.request_id != PICK_USER_REQUEST_ID:
            return ResolveResult(error="Неизвестный запрос выбора пользователя.")
        shared = message.users_shared.users[0]
        user = User(
            id=shared.user_id,
            is_bot=False,
            first_name=shared.first_name or shared.username or "user",
            last_name=shared.last_name,
            username=shared.username,
        )
        has_photo = bool(shared.photo) if shared.photo is not None else None
        filled = await get_chat_user(bot, shared.user_id)
        if filled:
            if not user.username:
                user.username = filled.username
            if user.first_name == "user" and filled.first_name:
                user.first_name = filled.first_name
            user.is_premium = filled.is_premium
        return ResolveResult(user=user, has_photo=has_photo)

    origin = message.forward_origin
    if origin is not None:
        sender = getattr(origin, "sender_user", None)
        if sender:
            return ResolveResult(user=sender)
        if isinstance(origin, MessageOriginHiddenUser):
            return ResolveResult(
                error="Этот человек скрыл пересылку. Нажми «Выбрать пользователя» или пришли публичный @username.",
            )
        sender_chat = getattr(origin, "sender_chat", None) or getattr(origin, "chat", None)
        if sender_chat and getattr(sender_chat, "username", None):
            user = await get_chat_user(bot, f"@{sender_chat.username}")
            if user:
                return ResolveResult(user=user)

    if message.forward_from:
        return ResolveResult(user=message.forward_from)

    if message.entities and message.text:
        for ent in message.entities:
            if ent.type == "text_mention" and ent.user:
                return ResolveResult(user=ent.user)
            if ent.type == "mention":
                raw = ent.extract_from(message.text)
                username = normalize_username(raw)
                if username:
                    return await _resolve_username(bot, username, repo)
            if ent.type in {"url", "text_link"}:
                raw = ent.url if ent.type == "text_link" and ent.url else ent.extract_from(message.text)
                username = extract_username(raw or "")
                if username:
                    return await _resolve_username(bot, username, repo)

    if message.text:
        username = extract_username(message.text)
        if username:
            return await _resolve_username(bot, username, repo)
        if message.text.strip().isdigit():
            user = await get_chat_user(bot, int(message.text.strip()))
            if user:
                return ResolveResult(user=user)

    if message.contact and message.contact.user_id:
        user = await get_chat_user(bot, message.contact.user_id)
        if user:
            return ResolveResult(user=user)
        return ResolveResult(
            user=User(
                id=message.contact.user_id,
                is_bot=False,
                first_name=message.contact.first_name or "user",
                last_name=message.contact.last_name,
            )
        )

    return ResolveResult(
        error="Не понял. Пришли @username, ссылку t.me/..., перешли сообщение или нажми «Выбрать пользователя».",
    )


async def _resolve_username(bot: Bot, username: str, repo: Repository | None) -> ResolveResult:
    live = await get_chat_user(bot, f"@{username}")
    if live:
        return ResolveResult(user=live)

    async def from_row(row: dict) -> ResolveResult | None:
        uid = row["telegram_id"]
        filled = await get_chat_user(bot, uid)
        if filled:
            if filled.username and filled.username.lower() != username.lower():
                return None
            return ResolveResult(user=filled)
        return ResolveResult(
            user=user_from_row(
                uid,
                row.get("username") or username,
                row.get("first_name"),
                bool(row.get("is_premium")),
            )
        )

    if repo:
        row = await repo.find_by_username(username)
        if row:
            result = await from_row(row)
            if result:
                return result

        rated = await repo.find_rated_by_username(username)
        if rated:
            result = await from_row(rated)
            if result:
                return result

    return ResolveResult(
        error=(
            f"Не могу открыть @{username} только по нику — Telegram не отдаёт ботам id чужих аккаунтов.\n\n"
            "Сделай одно из этого:\n"
            "• нажми <b>Выбрать пользователя</b> и укажи его в списке\n"
            "• перешли любое его сообщение\n"
            "• пусть он сначала напишет боту /start"
        )
    )


async def fetch_profile_description(bot: Bot, user_id: int, username: str | None = None) -> str | None:
    candidates: list[int | str] = [user_id]
    if username:
        candidates.append(f"@{username.lstrip('@')}")

    for chat_id in candidates:
        try:
            chat = await bot.get_chat(chat_id)
            bio = getattr(chat, "bio", None)
            if bio and bio.strip():
                return bio.strip()
        except TelegramAPIError:
            continue
    return None


async def user_has_photo(bot: Bot, user_id: int) -> bool | None:
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        return bool(photos.total_count)
    except TelegramAPIError:
        return None
