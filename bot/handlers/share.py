from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from bot.config import settings
from bot.database.repo import Repository
from bot.handlers.rate_self import perform_self_rating
from bot.keyboards.callbacks import MenuCB
from bot.utils.emoji import plain
from bot.utils.navigation import drop_reply_keyboard

router = Router()


@router.callback_query(MenuCB.filter(F.action == "rate_self"))
async def rate_self_callback(callback: CallbackQuery, state: FSMContext, repo: Repository) -> None:
    await state.clear()
    await callback.answer()
    if not callback.message:
        return
    await drop_reply_keyboard(callback.bot, callback.message.chat.id)
    await perform_self_rating(callback.message, callback.from_user, repo, callback)


@router.inline_query()
async def inline_share(inline_query: InlineQuery, repo: Repository) -> None:
    user = inline_query.from_user
    rating = await repo.get_user_best_rating(user.id)
    if rating and rating.target_username:
        score = rating.total_score
        uname = rating.target_username
    else:
        score = 0
        uname = user.username or "user"

    text = (
        f"{plain('trophy')} Профиль @{uname} — {score}/100 в ProfileMark!\n"
        f"Оцени свой: @{settings.bot_username_clean}"
    )
    await inline_query.answer(
        [
            InlineQueryResultArticle(
                id="share",
                title=f"{plain('share')} Поделиться: {score}/100",
                description=f"@{uname}",
                input_message_content=InputTextMessageContent(message_text=text, parse_mode="HTML"),
            )
        ],
        cache_time=10,
        is_personal=True,
    )
