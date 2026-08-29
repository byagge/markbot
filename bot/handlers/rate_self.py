from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, User

from bot.database.repo import Repository
from bot.keyboards.callbacks import RateCB
from bot.keyboards.inline import rate_self_result_kb
from bot.services.openai_service import generate_verdict
from bot.services.profile_analyzer import analyze_profile
from bot.utils.navigation import edit_or_send, run_loading_animation
from bot.utils.emoji import e, plain
from bot.utils.texts import format_rating_result

router = Router()


async def perform_self_rating(
    message: Message,
    user: User,
    repo: Repository,
    callback: CallbackQuery | None = None,
) -> None:
    header = f"{e('search')} <b>Анализирую твой профиль...</b>"
    loading_text = f"{header}\n"

    if callback:
        msg = await edit_or_send(callback, loading_text, repo=repo, user_id=user.id)
    else:
        msg = message

    await run_loading_animation(msg, header)

    scores = analyze_profile(user, has_photo=True)
    verdict = await generate_verdict(user.username, scores, is_self=True)

    await repo.save_rating(
        user.id,
        user.id,
        user.username,
        scores.as_dict(),
        verdict,
        is_self=True,
    )

    text = format_rating_result(user.username, scores, verdict, user.first_name)
    kb = rate_self_result_kb(user.username, scores.total)

    try:
        await msg.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        new_msg = await message.answer(text, reply_markup=kb, parse_mode="HTML")
        await repo.set_nav_message(user.id, new_msg.message_id)


@router.callback_query(RateCB.filter(F.action == "retry_self"))
async def retry_self(callback: CallbackQuery, repo: Repository) -> None:
    await callback.answer(f"{plain('refresh')} Пересчитываю...")
    if callback.message and callback.from_user:
        await perform_self_rating(callback.message, callback.from_user, repo, callback)
