import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User

from bot.database.repo import Repository
from bot.handlers.rate_self import perform_self_rating
from bot.keyboards.callbacks import RateCB
from bot.keyboards.inline import main_menu_kb, rate_other_prompt_kb, rate_other_result_kb
from bot.keyboards.reply import CANCEL_TEXTS, PICK_USER_REQUEST_ID, PICK_USER_TEXT, rate_other_pick_kb, remove_kb
from bot.services.openai_service import generate_compare_verdict, generate_verdict
from bot.services.profile_analyzer import analyze_profile, scores_from_rating_row
from bot.services.profile_fetcher import ResolveResult, get_chat_user, resolve_target_user
from bot.states import RateOtherStates
from bot.utils.emoji import e, plain
from bot.utils.navigation import edit_or_send, run_loading_animation
from bot.utils.texts import display_name, format_compare_result, format_rating_result, main_menu_text

logger = logging.getLogger(__name__)

router = Router()


async def perform_other_rating(
    message: Message,
    target: User,
    rater: User,
    repo: Repository,
    callback: CallbackQuery | None = None,
    has_photo: bool | None = None,
    progress_msg: Message | None = None,
) -> None:
    name = display_name(target.username, target.first_name)
    header = f"{e('search')} <b>Анализирую профиль {name}...</b>"

    if callback:
        msg = await edit_or_send(callback, f"{header}\n", repo=repo, user_id=rater.id)
    elif progress_msg:
        msg = progress_msg
        try:
            await msg.edit_text(f"{header}\n", reply_markup=None, parse_mode="HTML")
        except TelegramBadRequest:
            msg = await message.answer(f"{header}\n", reply_markup=remove_kb(), parse_mode="HTML")
    else:
        msg = await message.answer(
            f"{header}\n",
            reply_markup=remove_kb(),
            parse_mode="HTML",
        )

    try:
        await run_loading_animation(msg, header)
        scores = await analyze_profile(message.bot, target, has_photo=has_photo)
        verdict = await generate_verdict(target.username, scores, is_self=False)

        await repo.upsert_user(
            target.id,
            target.username,
            target.first_name,
            target.last_name,
            target.is_premium or False,
        )
        await repo.save_rating(
            rater.id,
            target.id,
            target.username,
            scores.as_dict(),
            verdict,
            is_self=False,
        )

        text = format_rating_result(target.username, scores, verdict, target.first_name)
        kb = rate_other_result_kb(target.username, scores.total, target.id)

        try:
            await msg.edit_text(text, reply_markup=kb, parse_mode="HTML")
            await repo.set_nav_message(rater.id, msg.message_id)
        except Exception:
            new_msg = await message.answer(text, reply_markup=kb, parse_mode="HTML")
            await repo.set_nav_message(rater.id, new_msg.message_id)
    except Exception:
        logger.exception("other rating failed for %s", target.id)
        err = f"{e('cross')} <b>Ошибка анализа.</b> Попробуй позже."
        try:
            await msg.edit_text(err, parse_mode="HTML")
        except Exception:
            await message.answer(err, parse_mode="HTML")
        raise


async def _show_resolve_error(message: Message, user_id: int, repo: Repository, text: str) -> None:
    full = f"{e('cross')} <b>Не получилось.</b>\n\n{text}"
    nav_id = await repo.get_nav_message(user_id)
    if nav_id:
        try:
            await message.bot.edit_message_text(
                full,
                chat_id=message.chat.id,
                message_id=nav_id,
                parse_mode="HTML",
                reply_markup=rate_other_prompt_kb(),
            )
        except TelegramBadRequest:
            pass
    await message.answer(full, parse_mode="HTML", reply_markup=rate_other_pick_kb())


async def _process_target(message: Message, state: FSMContext, repo: Repository, result: ResolveResult) -> None:
    user = message.from_user
    if not user:
        return

    if not result.user:
        await _show_resolve_error(
            message,
            user.id,
            repo,
            result.error or "Пришли @username, перешли сообщение или нажми «👤 Выбрать пользователя».",
        )
        return

    try:
        await message.bot.send_chat_action(message.chat.id, "typing")
    except TelegramBadRequest:
        pass

    ack: Message | None = None
    try:
        ack = await message.answer(
            f"{e('check')} <b>Пользователь найден</b> — анализирую...",
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        pass

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    if result.user.id == user.id:
        await state.clear()
        await perform_self_rating(message, user, repo, progress_msg=ack)
        return

    try:
        await perform_other_rating(
            message,
            result.user,
            user,
            repo,
            has_photo=result.has_photo,
            progress_msg=ack,
        )
        await state.clear()
    except Exception:
        await state.set_state(RateOtherStates.waiting_target)
        await _show_resolve_error(
            message,
            user.id,
            repo,
            "Что-то пошло не так. Попробуй ещё раз или выбери пользователя кнопкой ниже.",
        )


@router.message(F.users_shared)
async def receive_users_shared(message: Message, state: FSMContext, repo: Repository) -> None:
    if not message.users_shared or not message.users_shared.users:
        return
    if message.users_shared.request_id != PICK_USER_REQUEST_ID:
        return

    await state.set_state(RateOtherStates.waiting_target)
    result = await resolve_target_user(message, message.bot, repo)
    await _process_target(message, state, repo, result)


@router.message(F.contact, StateFilter(None, RateOtherStates.waiting_target))
async def receive_contact(message: Message, state: FSMContext, repo: Repository) -> None:
    await state.set_state(RateOtherStates.waiting_target)
    result = await resolve_target_user(message, message.bot, repo)
    await _process_target(message, state, repo, result)


@router.message(RateOtherStates.waiting_target)
async def receive_target(message: Message, state: FSMContext, repo: Repository) -> None:
    user = message.from_user
    if not user:
        return

    text = (message.text or "").strip()
    if text.lower() in CANCEL_TEXTS or text == "⬅️ Назад":
        await state.clear()
        msg = await message.answer(
            main_menu_text(),
            reply_markup=remove_kb(),
            parse_mode="HTML",
        )
        await msg.edit_text(main_menu_text(), reply_markup=main_menu_kb(), parse_mode="HTML")
        await repo.set_nav_message(user.id, msg.message_id)
        return

    if text == PICK_USER_TEXT or text == "Выбрать пользователя":
        await message.answer(
            f"{e('point_down')} Выбери человека в окне Telegram 👆",
            reply_markup=rate_other_pick_kb(),
            parse_mode="HTML",
        )
        return

    result = await resolve_target_user(message, message.bot, repo)
    await _process_target(message, state, repo, result)


@router.callback_query(RateCB.filter(F.action == "compare"))
async def compare_profiles(callback: CallbackQuery, callback_data: RateCB, repo: Repository) -> None:
    if callback_data.uid <= 0:
        await callback.answer("Нет данных для сравнения", show_alert=True)
        return

    await callback.answer(f"{plain('swords')} Сравниваю...")
    user = callback.from_user
    if not callback.message:
        return

    stored = await repo.get_last_other_rating(user.id, callback_data.uid)
    if not stored:
        await callback.answer("Сначала оцени этот профиль", show_alert=True)
        return

    my_stored = await repo.get_user_best_rating(user.id)
    my_scores = scores_from_rating_row(my_stored) if my_stored else await analyze_profile(callback.bot, user)
    other_scores = scores_from_rating_row(stored)

    other_username = stored.target_username
    other = User(
        id=callback_data.uid,
        is_bot=False,
        first_name=other_username or "user",
        username=other_username,
    )
    filled = await get_chat_user(callback.bot, callback_data.uid)
    if filled:
        other = filled

    my_name = display_name(user.username, user.first_name)
    other_name = display_name(other.username, other.first_name)
    verdict = await generate_compare_verdict(my_scores, other_scores, my_name, other_name)
    text = format_compare_result(my_name, other_name, my_scores, other_scores, verdict)
    kb = rate_other_result_kb(other.username, other_scores.total, other.id)
    await edit_or_send(callback, text, kb, repo=repo, user_id=user.id)
