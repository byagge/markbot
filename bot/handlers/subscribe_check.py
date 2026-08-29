from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.database.repo import Repository
from bot.keyboards.callbacks import SubCB
from bot.keyboards.inline import main_menu_kb, subscribe_kb
from bot.services.subscription import format_subscribe_message, get_missing_channels
from bot.utils.navigation import edit_or_send
from bot.utils.texts import main_menu_text

router = Router()


@router.callback_query(SubCB.filter(F.action == "check"))
async def check_subscription(callback: CallbackQuery, repo: Repository) -> None:
    user = callback.from_user
    missing = await get_missing_channels(callback.bot, repo, user.id)

    if missing:
        text = format_subscribe_message(missing)
        await callback.answer("Ты ещё не подписан! Нажми «Подписаться»", show_alert=True)
        if callback.message:
            try:
                await callback.message.edit_text(
                    text, reply_markup=subscribe_kb(missing), parse_mode="HTML"
                )
            except Exception:
                await callback.message.answer(
                    text, reply_markup=subscribe_kb(missing), parse_mode="HTML"
                )
        return

    from bot.utils.emoji import plain

    await callback.answer(f"{plain('check')} Подписка подтверждена!", show_alert=False)
    await edit_or_send(
        callback,
        main_menu_text(),
        main_menu_kb(),
        repo=repo,
        user_id=user.id,
    )
