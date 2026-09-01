from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.callbacks import AdminCB, MenuCB, RateCB, SubCB, TopCB
from bot.utils.emoji import btn_label, plain


def _btn(
    label: str,
    callback_data: str,
    emoji_key: str | None = None,
    style: str | None = None,
) -> InlineKeyboardButton:
    text, icon_id = btn_label(emoji_key, label) if emoji_key else (label, None)
    kwargs: dict = {"text": text, "callback_data": callback_data}
    if icon_id:
        kwargs["icon_custom_emoji_id"] = icon_id
    if style:
        kwargs["style"] = style
    return InlineKeyboardButton(**kwargs)


def _share_btn(label: str, query: str) -> InlineKeyboardButton:
    text, icon_id = btn_label("share", label)
    kwargs: dict = {
        "text": text,
        "switch_inline_query_current_chat": query,
        "style": "success",
    }
    if icon_id:
        kwargs["icon_custom_emoji_id"] = icon_id
    return InlineKeyboardButton(**kwargs)


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("Оценить мой профиль", MenuCB(action="rate_self").pack(), "fire", "success")],
        [_btn("Оценить другого", MenuCB(action="rate_other").pack(), "people", "primary")],
        [_btn("Топ профилей", MenuCB(action="top").pack(), "trophy", "primary")],
        [_btn("Анонимность", MenuCB(action="anonymity").pack(), "user")],
        [_btn("Как считается рейтинг", MenuCB(action="info").pack(), "question")],
    ])


def back_kb(action: str = "menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("Назад", MenuCB(action=action).pack(), "back")],
    ])


def rate_other_prompt_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("Назад", MenuCB(action="menu").pack(), "back")],
    ])


def rate_self_result_kb(username: str | None, score: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_share_btn("Поделиться результатом", f"{plain('trophy')} {score}/100")],
        [_btn("Оценить другого", MenuCB(action="rate_other").pack(), "people", "primary")],
        [_btn("Топ профилей", MenuCB(action="top").pack(), "trophy", "primary")],
        [_btn("Оценить заново", RateCB(action="retry_self").pack(), "refresh")],
    ])


def rate_other_result_kb(username: str | None, score: int, target_uid: int) -> InlineKeyboardMarkup:
    uname = username or "user"
    return InlineKeyboardMarkup(inline_keyboard=[
        [_share_btn("Поделиться результатом", f"{plain('trophy')} @{uname} — {score}/100")],
        [_btn("Оценить ещё кого-то", MenuCB(action="rate_other").pack(), "people", "primary")],
        [_btn("Оценить свой профиль", MenuCB(action="rate_self").pack(), "fire", "success")],
        [_btn("Сравнить с моим профилем", RateCB(action="compare", uid=target_uid).pack(), "swords", "danger")],
    ])


def rating_info_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("Оценить мой профиль", MenuCB(action="rate_self").pack(), "fire", "success")],
        [_btn("Назад", MenuCB(action="menu").pack(), "back")],
    ])


def anonymity_kb(is_on: bool) -> InlineKeyboardMarkup:
    if is_on:
        toggle = _btn("Выключить анонимность", MenuCB(action="toggle_anonymity").pack(), "check", "success")
    else:
        toggle = _btn("Включить анонимность", MenuCB(action="toggle_anonymity").pack(), "user", "primary")
    return InlineKeyboardMarkup(inline_keyboard=[
        [toggle],
        [_btn("Назад", MenuCB(action="menu").pack(), "back")],
    ])


def top_categories_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            _btn("Общий топ", TopCB(action="show", category="general").pack(), "globe", "primary"),
            _btn("По подаркам", TopCB(action="show", category="gifts").pack(), "gift", "primary"),
        ],
        [
            _btn("По юзернейму", TopCB(action="show", category="username").pack(), "letters", "primary"),
            _btn("Топ друзей", TopCB(action="show", category="friends").pack(), "people", "primary"),
        ],
        [_btn("Назад", MenuCB(action="menu").pack(), "back")],
    ])


def top_result_kb(category: str) -> InlineKeyboardMarkup:
    other_cats = [c for c in ("general", "gifts", "username") if c != category]
    rows = [
        [_btn("Улучшить оценку", MenuCB(action="rate_self").pack(), "fire", "success")],
    ]
    cat_labels = {
        "general": ("Общий топ", "globe"),
        "gifts": ("По подаркам", "gift"),
        "username": ("По юзернейму", "letters"),
    }
    if len(other_cats) == 2:
        l0, k0 = cat_labels[other_cats[0]]
        l1, k1 = cat_labels[other_cats[1]]
        rows.append([
            _btn(l0, TopCB(action="show", category=other_cats[0]).pack(), k0, "primary"),
            _btn(l1, TopCB(action="show", category=other_cats[1]).pack(), k1, "primary"),
        ])
    rows.append([_btn("Назад", TopCB(action="categories").pack(), "back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


from bot.services.subscription import subscribe_url


def subscribe_kb(channels: list) -> InlineKeyboardMarkup:
    rows = []
    for ch in channels:
        url = subscribe_url(ch)
        title = ch["channel_title"][:28]
        text, icon_id = btn_label("megaphone", f"Подписаться — {title}")
        kwargs: dict = {"text": text, "url": url}
        if icon_id:
            kwargs["icon_custom_emoji_id"] = icon_id
        rows.append([InlineKeyboardButton(**kwargs)])
    rows.append([_btn("Проверить подписку", SubCB(action="check").pack(), "check", "success")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [_btn("Статистика", AdminCB(action="stats", period="today").pack(), "chart", "primary")],
        [_btn("Рассылка", AdminCB(action="broadcast").pack(), "loudspeaker", "success")],
        [_btn("Обязательная подписка", AdminCB(action="channels").pack(), "megaphone", "primary")],
        [_btn("Всего пользователей", AdminCB(action="users_count").pack(), "people")],
        [_btn("Закрыть", AdminCB(action="close").pack(), "back")],
    ])


def admin_stats_kb(period: str = "today") -> InlineKeyboardMarkup:
    def p(label: str, key: str) -> InlineKeyboardButton:
        mark = " •" if key == period else ""
        return _btn(f"{label}{mark}", AdminCB(action="stats", period=key).pack())

    return InlineKeyboardMarkup(inline_keyboard=[
        [p("Сегодня", "today"), p("Вчера", "yesterday")],
        [p("Неделя", "week"), p("Прошлая неделя", "last_week")],
        [p("Месяц", "month"), p("Все время", "all")],
        [_btn("Назад", AdminCB(action="menu").pack(), "back")],
    ])


def admin_channels_kb(channels: list) -> InlineKeyboardMarkup:
    rows = [[_btn("Добавить канал", AdminCB(action="add_channel").pack(), "plus", "success")]]
    for ch in channels:
        rows.append([
            _btn(ch["channel_title"][:30], AdminCB(action="del_channel", channel_id=ch["channel_id"]).pack(), "cross", "danger"),
        ])
    rows.append([_btn("Назад", AdminCB(action="menu").pack(), "back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
