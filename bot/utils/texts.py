from bot.services.profile_analyzer import ProfileScores, stars_for_score
from bot.utils.emoji import e


def display_name(username: str | None, first_name: str | None = None) -> str:
    if username:
        return f"@{username}"
    if first_name:
        return first_name
    return "профиль"


def format_rating_result(
    username: str | None,
    scores: ProfileScores,
    verdict: str,
    first_name: str | None = None,
) -> str:
    name = display_name(username, first_name)
    stars = stars_for_score(scores.total)

    def line(key: str, label: str, val: int, max_val: int, note: str) -> str:
        suffix = f" <i>({note})</i>" if note else ""
        return f"{e(key)} <b>{label}:</b> {val}/{max_val}{suffix}"

    return (
        f"{e('trophy')} <b>Оценка профиля:</b> {name}\n\n"
        f"{e('sparkles')} <b>Итог:</b> {scores.total}/100 {stars}\n\n"
        f"{line('picture', 'Аватарка', scores.avatar, 25, scores.avatar_note)}\n"
        f"{line('letters', 'Юзернейм', scores.username, 25, scores.username_note)}\n"
        f"{line('gift', 'Подарки', scores.gifts, 25, scores.gifts_note)}\n"
        f"{line('memo', 'Био', scores.bio, 15, scores.bio_note)}\n"
        f"{line('hourglass', 'Возраст аккаунта', scores.age, 10, scores.age_note)}\n\n"
        f"{e('speech')} <b>Вердикт:</b> {verdict}"
    )


def format_compare_result(
    my_name: str,
    other_name: str,
    my_scores: ProfileScores,
    other_scores: ProfileScores,
    verdict: str,
) -> str:
    diff = my_scores.total - other_scores.total
    if diff > 0:
        winner = f"{e('medal')} <b>Победитель:</b> {my_name} (+{diff})"
    elif diff < 0:
        winner = f"{e('medal')} <b>Победитель:</b> {other_name} (+{abs(diff)})"
    else:
        winner = f"{e('handshake')} <b>Ничья!</b>"

    return (
        f"{e('swords')} <b>Сравнение профилей</b>\n\n"
        f"{e('user')} {my_name} — <b>{my_scores.total}/100</b> {stars_for_score(my_scores.total)}\n"
        f"{e('user')} {other_name} — <b>{other_scores.total}/100</b> {stars_for_score(other_scores.total)}\n\n"
        f"{winner}\n\n"
        f"{e('speech')} {verdict}"
    )


def main_menu_text() -> str:
    return (
        f"{e('fire')} <b>ProfileMark</b> — оцени свой Telegram-профиль!\n\n"
        f"Узнай рейтинг от 0 до 100, сравни с друзьями и попади в топ {e('trophy')}\n\n"
        f"{e('point_down')} Выбери действие:"
    )


def rate_other_prompt() -> str:
    return (
        f"{e('people')} <b>Оценка другого профиля</b>\n\n"
        "Пришли мне:\n"
        "• Юзернейм (например: <code>@durov</code>)\n"
        "• Или перешли любое сообщение от этого человека\n\n"
        f"{e('warning')} <i>Учти: я смогу оценить только то, что открыто в приватности — "
        "если у человека скрыт юзернейм/фото/подарки, часть баллов не посчитается.</i>"
    )


def rating_info_text() -> str:
    return (
        f"{e('question')} <b>Как работает система оценки</b>\n\n"
        "Итоговый рейтинг — от <b>0 до 100</b> баллов по 5 категориям:\n\n"
        f"{e('picture')} <b>Аватарка</b> — до 25 баллов\n"
        "Наличие фото, качество, давность установки\n\n"
        f"{e('letters')} <b>Юзернейм</b> — до 25 баллов\n"
        "Короткий ник лучше, цифры и _ снижают оценку\n\n"
        f"{e('gift')} <b>Подарки</b> — до 25 баллов\n"
        "Количество, редкость и стоимость подарков\n\n"
        f"{e('memo')} <b>Био и оформление</b> — до 15 баллов\n"
        "Заполненность описания, ссылки, emoji-статус\n\n"
        f"{e('hourglass')} <b>Возраст аккаунта</b> — до 10 баллов\n"
        "Чем раньше регистрация — тем больше баллов\n\n"
        f"{e('warning')} <i>Если данные скрыты приватностью — категория получает 0 баллов.</i>\n\n"
        f"{e('bulb')} <i>Совет: открой юзернейм и подарки в настройках приватности для точной оценки.</i>"
    )


def top_categories_text() -> str:
    return f"{e('trophy')} <b>Топ-10 профилей</b>\n\n{e('point_down')} Выбери категорию:"


def subscribe_text(channels_html: str) -> str:
    return (
        f"{e('megaphone')} <b>Для использования бота нужна подписка</b>\n\n"
        f"1️⃣ Нажми кнопку <b>«Подписаться»</b> ниже\n"
        f"2️⃣ Вступи в канал по ссылке\n"
        f"3️⃣ Вернись и нажми {e('check')} <b>Проверить подписку</b>\n\n"
        f"{channels_html}"
    )


TOP_PERIOD_LABEL = {
    "general": "за всё время",
    "gifts": "по подаркам",
    "username": "по юзернейму",
    "friends": "среди друзей",
}


def medal_emoji(rank: int) -> str:
    if rank == 0:
        return e("gold")
    if rank == 1:
        return e("silver")
    if rank == 2:
        return e("bronze")
    nums = ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    idx = rank - 3
    return nums[idx] if 0 <= idx < len(nums) else f"{rank + 1}."
