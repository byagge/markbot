from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import settings
from bot.database.repo import Repository
from bot.keyboards.inline import main_menu_kb, subscribe_kb
from bot.services.subscription import format_subscribe_message, get_missing_channels
from bot.utils.navigation import send_sticker_safe
from bot.utils.texts import main_menu_text

router = Router()


async def _send_main_or_subscribe(message: Message, repo: Repository) -> None:
    user = message.from_user
    if not user:
        return

    if user.id not in settings.admins:
        missing = await get_missing_channels(message.bot, repo, user.id)
        if missing:
            text = format_subscribe_message(missing)
            msg = await message.answer(text, reply_markup=subscribe_kb(missing), parse_mode="HTML")
            await repo.set_nav_message(user.id, msg.message_id)
            return

    msg = await message.answer(main_menu_text(), reply_markup=main_menu_kb(), parse_mode="HTML")
    await repo.set_nav_message(user.id, msg.message_id)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, repo: Repository) -> None:
    await state.clear()
    user = message.from_user
    if not user:
        return

    await repo.upsert_user(
        user.id,
        user.username,
        user.first_name,
        user.last_name,
        user.is_premium or False,
    )

    await send_sticker_safe(message.bot, message.chat.id, settings.welcome_sticker_id)
    await _send_main_or_subscribe(message, repo)


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext, repo: Repository) -> None:
    await state.clear()
    await _send_main_or_subscribe(message, repo)
