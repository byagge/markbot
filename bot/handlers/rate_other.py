from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User

from bot.database.repo import Repository
from bot.keyboards.callbacks import RateCB
from bot.keyboards.inline import rate_other_result_kb
from bot.keyboards.reply import CANCEL_TEXTS, PICK_USER_TEXT, remove_kb
from bot.services.openai_service import generate_compare_verdict, generate_verdict
from bot.services.profile_analyzer import analyze_profile
from bot.services.profile_fetcher import resolve_target_user
from bot.states import RateOtherStates
from bot.utils.emoji import e, plain
from bot.utils.navigation import edit_or_send, run_loading_animation
from bot.utils.texts import display_name, format_compare_result, format_rating_result, main_menu_text

router = Router()


async def perform_other_rating(
    message: Message,
    target: User,
    rater: User,
    repo: Repository,
    callback: CallbackQuery | None = None,
    has_photo: bool | None = None,
) -> None:
    name = display_name(target.username, target.first_name)
    header = f"{e('search')} <b>Анализирую профиль {name}...</b>"

    if callback:
        msg = await edit_or_send(callback, f"{header}\n", repo=repo, user_id=rater.id)
    else:
        msg = await message.answer(
            f"{header}\n",
            reply_markup=remove_kb(),
            parse_mode="HTML",
        )

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


async def _show_resolve_error(message: Message, user_id: int, repo: Repository, text: str) -> None:
    from bot.keyboards.inline import rate_other_prompt_kb
    from bot.keyboards.reply import rate_other_pick_kb

    nav_id = await repo.get_nav_message(user_id)
    full = f"{e('cross')} <b>Не получилось.</b>\n\n{text}"
    if nav_id:
        try:
            await message.bot.edit_message_text(
                full,
                chat_id=message.chat.id,
                message_id=nav_id,
                parse_mode="HTML",
                reply_markup=rate_other_prompt_kb(),
            )
            return
        except TelegramBadRequest:
            pass
    await message.answer(full, parse_mode="HTML", reply_markup=rate_other_pick_kb())


@router.message(RateOtherStates.waiting_target)
async def receive_target(message: Message, state: FSMContext, repo: Repository) -> None:
    user = message.from_user
    if not user:
        return

    text = (message.text or "").strip()
    if text.lower() in CANCEL_TEXTS:
        await state.clear()
        msg = await message.answer(
            main_menu_text(),
            reply_markup=remove_kb(),
            parse_mode="HTML",
        )
        from bot.keyboards.inline import main_menu_kb

        await msg.edit_text(main_menu_text(), reply_markup=main_menu_kb(), parse_mode="HTML")
        await repo.set_nav_message(user.id, msg.message_id)
        return

    if text == PICK_USER_TEXT:
        return

    result = await resolve_target_user(message, message.bot, repo)
    if not result.user:
        await _show_resolve_error(
            message,
            user.id,
            repo,
            result.error
            or "Пришли @username, перешли сообщение или нажми «Выбрать пользователя».",
        )
        return

    await state.clear()
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    await perform_other_rating(
        message,
        result.user,
        user,
        repo,
        has_photo=result.has_photo,
    )


@router.callback_query(RateCB.filter(F.action == "compare"))
async def compare_profiles(callback: CallbackQuery, callback_data: RateCB, repo: Repository) -> None:
    await callback.answer(f"{plain('swords')} Сравниваю...")
    user = callback.from_user
    if not callback.message:
        return

    my_scores = await analyze_profile(callback.bot, user)
    stored = await repo.get_last_other_rating(user.id, callback_data.uid)

    other_username = stored.target_username if stored else None
    other = User(
        id=callback_data.uid,
        is_bot=False,
        first_name=other_username or "user",
        username=other_username,
    )
    other_scores = await analyze_profile(callback.bot, other)

    my_name = display_name(user.username, user.first_name)
    other_name = display_name(other.username, other.first_name)
    verdict = await generate_compare_verdict(my_scores, other_scores, my_name, other_name)
    text = format_compare_result(my_name, other_name, my_scores, other_scores, verdict)
    kb = rate_other_result_kb(other.username, other_scores.total, other.id)
    await edit_or_send(callback, text, kb, repo=repo, user_id=user.id)
