from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import settings
from bot.database import db
from bot.database.repo import Repository
from bot.keyboards.inline import subscribe_kb
from bot.services.subscription import format_subscribe_message, get_missing_channels


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        conn = await db.connect()
        try:
            data["repo"] = Repository(conn)
            return await handler(event, data)
        finally:
            await conn.close()


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        if user.id in settings.admins:
            return await handler(event, data)

        repo: Repository = data["repo"]
        channels = await repo.get_active_channels()
        if not channels:
            return await handler(event, data)

        if isinstance(event, CallbackQuery) and event.data:
            if event.data.startswith("sub:") or event.data.startswith("a:"):
                return await handler(event, data)

        bot = data["bot"]
        missing = await get_missing_channels(bot, repo, user.id)

        if missing:
            text = format_subscribe_message(missing)
            markup = subscribe_kb(missing)
            if isinstance(event, CallbackQuery):
                if event.message:
                    try:
                        await event.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
                    except Exception:
                        await event.message.answer(text, reply_markup=markup, parse_mode="HTML")
                await event.answer("Сначала подпишись на канал!", show_alert=True)
                return None
            if isinstance(event, Message):
                await event.answer(text, reply_markup=markup, parse_mode="HTML")
                return None

        return await handler(event, data)
