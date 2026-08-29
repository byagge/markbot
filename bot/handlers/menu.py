from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.database.repo import Repository
from bot.keyboards.callbacks import MenuCB
from bot.keyboards.inline import (
    main_menu_kb,
    rate_other_prompt_kb,
    rating_info_kb,
    top_categories_kb,
)
from bot.utils.navigation import edit_or_send
from bot.utils.texts import (
    main_menu_text,
    rate_other_prompt,
    rating_info_text,
    top_categories_text,
)

router = Router()


@router.callback_query(MenuCB.filter(F.action == "menu"))
async def show_menu(callback: CallbackQuery, repo: Repository) -> None:
    await callback.answer()
    await edit_or_send(
        callback,
        main_menu_text(),
        main_menu_kb(),
        repo=repo,
        user_id=callback.from_user.id,
    )


@router.callback_query(MenuCB.filter(F.action == "info"))
async def show_info(callback: CallbackQuery, repo: Repository) -> None:
    await callback.answer()
    await edit_or_send(callback, rating_info_text(), rating_info_kb(), repo=repo, user_id=callback.from_user.id)


@router.callback_query(MenuCB.filter(F.action == "rate_other"))
async def show_rate_other(callback: CallbackQuery, state: FSMContext, repo: Repository) -> None:
    from bot.states import RateOtherStates

    await callback.answer()
    await state.set_state(RateOtherStates.waiting_target)
    await edit_or_send(callback, rate_other_prompt(), rate_other_prompt_kb(), repo=repo, user_id=callback.from_user.id)


@router.callback_query(MenuCB.filter(F.action == "top"))
async def show_top_menu(callback: CallbackQuery, repo: Repository) -> None:
    await callback.answer()
    await edit_or_send(callback, top_categories_text(), top_categories_kb(), repo=repo, user_id=callback.from_user.id)
