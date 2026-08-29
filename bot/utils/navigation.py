import asyncio
from typing import Union

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from bot.database.repo import Repository

ParseTarget = Union[Message, CallbackQuery]


async def edit_or_send(
    target: ParseTarget,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    repo: Repository | None = None,
    user_id: int | None = None,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = True,
) -> Message:
    """Single-message navigation: edit existing nav message or send new."""
    if isinstance(target, CallbackQuery):
        message = target.message
        if message is None:
            raise ValueError("Callback without message")
        try:
            if message.photo or message.sticker:
                await message.delete()
                bot = target.bot
                chat_id = message.chat.id
                new_msg = await bot.send_message(
                    chat_id,
                    text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                    disable_web_page_preview=disable_web_page_preview,
                )
                if repo and user_id:
                    await repo.set_nav_message(user_id, new_msg.message_id)
                return new_msg
            return await message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                return message
            bot = target.bot
            chat_id = message.chat.id
            new_msg = await bot.send_message(
                chat_id,
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_web_page_preview,
            )
            if repo and user_id:
                await repo.set_nav_message(user_id, new_msg.message_id)
            return new_msg
    else:
        msg = await target.answer(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
        )
        if repo and user_id:
            await repo.set_nav_message(user_id, msg.message_id)
        return msg


from bot.utils.emoji import e, plain

LOADING_STEPS = [
    f"{e('bullet')} Проверяю аватарку",
    f"{e('bullet')} Сканирую юзернейм",
    f"{e('bullet')} Ищу подарки",
    f"{e('bullet')} Считаю итоговый рейтинг",
]


async def run_loading_animation(
    message: Message,
    header: str,
    steps: list[str] | None = None,
    delay: float = 0.55,
) -> None:
    steps = steps or LOADING_STEPS
    lines = [header, ""]
    for step in steps:
        lines.append(step)
        try:
            await message.edit_text("\n".join(lines), parse_mode="HTML")
        except TelegramBadRequest:
            pass
        await asyncio.sleep(delay)


async def send_sticker_safe(bot: Bot, chat_id: int, sticker_id: str) -> None:
    if not sticker_id:
        return
    try:
        await bot.send_sticker(chat_id, sticker_id)
    except TelegramBadRequest:
        pass
