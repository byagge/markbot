from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.database.repo import Repository
from bot.keyboards.callbacks import MenuCB
from bot.keyboards.inline import (
    main_menu_kb,
    rating_info_kb,
    top_categories_kb,
)
from bot.keyboards.reply import rate_other_pick_kb
from bot.states import RateOtherStates
from bot.utils.navigation import drop_reply_keyboard, edit_or_send
from bot.utils.texts import (
    main_menu_text,
    rate_other_prompt,
    rating_info_text,
    top_categories_text,
)

router = Router()


@router.callback_query(MenuCB.filter(F.action == "menu"))
async def show_menu(callback: CallbackQuery, state: FSMContext, repo: Repository) -> None:
    await state.clear()
    await callback.answer()
    if callback.message:
        await drop_reply_keyboard(callback.bot, callback.message.chat.id)
    await edit_or_send(
        callback,
        main_menu_text(),
        main_menu_kb(),
        repo=repo,
        user_id=callback.from_user.id,
    )


@router.callback_query(MenuCB.filter(F.action == "info"))
async def show_info(callback: CallbackQuery, state: FSMContext, repo: Repository) -> None:
    await state.clear()
    await callback.answer()
    if callback.message:
        await drop_reply_keyboard(callback.bot, callback.message.chat.id)
    await edit_or_send(callback, rating_info_text(), rating_info_kb(), repo=repo, user_id=callback.from_user.id)


@router.callback_query(MenuCB.filter(F.action == "rate_other"))
async def show_rate_other(callback: CallbackQuery, state: FSMContext, repo: Repository) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(RateOtherStates.waiting_target)
    user = callback.from_user
    await repo.upsert_user(user.id, user.username, user.first_name, user.last_name, user.is_premium or False)
    if not callback.message:
        return
    chat_id = callback.message.chat.id
    try:
        await callback.message.delete()
    except Exception:
        pass
    msg = await callback.bot.send_message(
        chat_id,
        rate_other_prompt(),
        reply_markup=rate_other_pick_kb(),
        parse_mode="HTML",
    )
    await repo.set_nav_message(callback.from_user.id, msg.message_id)


@router.callback_query(MenuCB.filter(F.action == "top"))
async def show_top_menu(callback: CallbackQuery, state: FSMContext, repo: Repository) -> None:
    await state.clear()
    await callback.answer()
    if callback.message:
        await drop_reply_keyboard(callback.bot, callback.message.chat.id)
    await edit_or_send(callback, top_categories_text(), top_categories_kb(), repo=repo, user_id=callback.from_user.id)
