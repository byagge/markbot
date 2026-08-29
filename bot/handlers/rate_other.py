from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, User

from bot.database.repo import Repository
from bot.keyboards.callbacks import RateCB
from bot.keyboards.inline import rate_other_result_kb
from bot.services.openai_service import generate_compare_verdict, generate_verdict
from bot.services.profile_analyzer import analyze_profile
from bot.services.profile_fetcher import resolve_target_user
from bot.states import RateOtherStates
from bot.utils.emoji import e, plain
from bot.utils.navigation import edit_or_send, run_loading_animation
from bot.utils.texts import display_name, format_compare_result, format_rating_result

router = Router()


async def perform_other_rating(
    message: Message,
    target: User,
    rater: User,
    repo: Repository,
    callback: CallbackQuery | None = None,
) -> None:
    name = display_name(target.username, target.first_name)
    header = f"{e('search')} <b>Анализирую профиль {name}...</b>"

    if callback:
        msg = await edit_or_send(callback, f"{header}\n", repo=repo, user_id=rater.id)
    else:
        msg = await message.answer(f"{header}\n", parse_mode="HTML")

    await run_loading_animation(msg, header)

    scores = await analyze_profile(message.bot, target)
    verdict = await generate_verdict(target.username, scores, is_self=False)

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
    except Exception:
        new_msg = await message.answer(text, reply_markup=kb, parse_mode="HTML")
        await repo.set_nav_message(rater.id, new_msg.message_id)


@router.message(RateOtherStates.waiting_target)
async def receive_target(message: Message, state: FSMContext, repo: Repository) -> None:
    user = message.from_user
    if not user:
        return

    target = await resolve_target_user(message, message.bot)
    if not target:
        nav_id = await repo.get_nav_message(user.id)
        text = (
            f"{e('cross')} <b>Не понял.</b> Пришли @username или перешли сообщение.\n\n"
            "Пример: <code>@durov</code>\n\n"
            "<i>Юзернейм должен быть публичным.</i>"
        )
        if nav_id:
            try:
                await message.bot.edit_message_text(text, message.chat.id, nav_id, parse_mode="HTML")
            except Exception:
                await message.answer(text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
        return

    await state.clear()
    try:
        await message.delete()
    except Exception:
        pass

    nav_id = await repo.get_nav_message(user.id)
    if nav_id:
        try:
            nav_msg = await message.bot.edit_message_text(
                plain("hourglass"), message.chat.id, nav_id, parse_mode="HTML"
            )
            fake = Message.model_validate(nav_msg.model_dump())
            fake.chat = message.chat
            await perform_other_rating(fake, target, user, repo)
            return
        except Exception:
            pass

    await perform_other_rating(message, target, user, repo)


@router.callback_query(RateCB.filter(F.action == "compare"))
async def compare_profiles(callback: CallbackQuery, callback_data: RateCB, repo: Repository) -> None:
    await callback.answer(f"{plain('swords')} Сравниваю...")
    user = callback.from_user
    if not callback.message:
        return

    my_scores = await analyze_profile(callback.bot, user)
    stored = await repo.get_last_other_rating(user.id, callback_data.uid)

    if stored and stored.target_username:
        other = User(
            id=callback_data.uid,
            is_bot=False,
            first_name=stored.target_username,
            username=stored.target_username,
        )
        other_scores = await analyze_profile(callback.bot, other)
    else:
        other = User(id=callback_data.uid, is_bot=False, first_name="user")
        other_scores = await analyze_profile(callback.bot, other)

    my_name = display_name(user.username, user.first_name)
    other_name = display_name(other.username, other.first_name)
    verdict = await generate_compare_verdict(my_scores, other_scores, my_name, other_name)
    text = format_compare_result(my_name, other_name, my_scores, other_scores, verdict)

    from bot.keyboards.inline import rate_other_result_kb

    kb = rate_other_result_kb(other.username, other_scores.total, other.id)
    await edit_or_send(callback, text, kb, repo=repo, user_id=user.id)
