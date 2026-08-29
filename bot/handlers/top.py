from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.database.repo import Repository
from bot.keyboards.callbacks import TopCB
from bot.keyboards.inline import top_categories_kb, top_result_kb
from bot.utils.emoji import e
from bot.utils.navigation import edit_or_send
from bot.utils.texts import TOP_PERIOD_LABEL, medal_emoji, top_categories_text

router = Router()


def _score_for_row(row, category: str) -> int:
    if category == "gifts":
        return int(row["gifts_score"])
    if category == "username":
        return int(row["username_score"])
    return int(row["total_score"])


async def build_top_text(repo: Repository, user_id: int, category: str) -> str:
    if category == "friends":
        tops = await repo.get_top("general", 10)
        tops = tops[:5] if tops else []
        title = f"{e('people')} <b>Топ друзей</b>"
    else:
        tops = await repo.get_top(category, 10)
        title = f"{e('trophy')} <b>Топ-10 профилей {TOP_PERIOD_LABEL.get(category, '')}</b>"

    lines = [title, ""]

    if not tops:
        lines.append(f"<i>Пока пусто — будь первым! {e('fire')}</i>")
    else:
        for i, row in enumerate(tops):
            medal = medal_emoji(i)
            uname = row["target_username"] or "anon"
            score = _score_for_row(row, category if category != "friends" else "general")
            lines.append(f"{medal} @{uname} — <b>{score}/100</b>")

    rank_data = await repo.get_user_rank(user_id, category if category != "friends" else "general")
    lines.append("")
    if rank_data:
        rank, score = rank_data
        lines.append(f"{e('chart')} <b>Твоё место:</b> #{rank} ({score}/100)")
        threshold = await repo.get_top10_threshold(category if category != "friends" else "general")
        if threshold and rank > 10:
            diff = threshold - score + 1
            lines.append(f"До топ-10: не хватает <b>{diff}</b> баллов {e('fire')}")
        elif rank <= 10:
            lines.append(f"{e('party')} <b>Ты в топ-10!</b> Красава!")
    else:
        lines.append(f"{e('chart')} Оцени свой профиль, чтобы попасть в рейтинг!")

    return "\n".join(lines)


@router.callback_query(TopCB.filter(F.action == "categories"))
async def top_categories(callback: CallbackQuery, repo: Repository) -> None:
    await callback.answer()
    await edit_or_send(callback, top_categories_text(), top_categories_kb(), repo=repo, user_id=callback.from_user.id)


@router.callback_query(TopCB.filter(F.action == "show"))
async def top_show(callback: CallbackQuery, callback_data: TopCB, repo: Repository) -> None:
    await callback.answer()
    category = callback_data.category
    text = await build_top_text(repo, callback.from_user.id, category)
    await edit_or_send(callback, text, top_result_kb(category), repo=repo, user_id=callback.from_user.id)
