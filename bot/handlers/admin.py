from datetime import datetime

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.database.repo import Repository, period_range
from bot.keyboards.callbacks import AdminCB
from bot.keyboards.inline import admin_channels_kb, admin_menu_kb, admin_stats_kb
from bot.states import AdminStates
from bot.services.subscription import create_tracked_invite, ensure_channel_links
from bot.utils.emoji import e, plain

router = Router(name="admin")


def is_admin(user_id: int) -> bool:
    return user_id in settings.admins


async def _edit_admin(
    callback: CallbackQuery,
    text: str,
    markup,
) -> None:
    if not callback.message:
        return
    try:
        await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except TelegramBadRequest as e_err:
        if "message is not modified" not in str(e_err).lower():
            raise


async def stats_text(repo: Repository, period: str) -> str:
    start, end, label = period_range(period)
    users = await repo.count_users_between(start, end)
    ratings = await repo.count_ratings_between(start, end)
    active_since = start or datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    active = await repo.count_active(active_since) if start else await repo.count_users()
    total_users = await repo.count_users()

    return (
        f"{e('chart_up')} <b>Статистика за период: {label}</b>\n\n"
        f"{e('people')} <b>Новых пользователей:</b> {users}\n"
        f"{e('star')} <b>Оценок профилей:</b> {ratings}\n"
        f"{e('green')} <b>Активных:</b> {active}\n\n"
        f"{e('chart')} <b>Всего пользователей:</b> {total_users}\n\n"
        f"<i>PeterRate Admin Panel</i>"
    )


async def channels_admin_text(bot, repo: Repository, channels: list[dict]) -> str:
    refreshed: list[dict] = []
    for ch in channels:
        refreshed.append(await ensure_channel_links(bot, repo, ch))

    total_joins = await repo.total_channel_joins()
    if not refreshed:
        return f"{e('megaphone')} <b>Каналов нет</b>\n\nДобавь канал {e('plus')}"

    lines = [
        f"{e('megaphone')} <b>Обязательная подписка</b>",
        f"\n{e('people')} <b>Всего по ссылкам:</b> {total_joins}\n",
    ]
    for ch in refreshed:
        url = ch.get("invite_link") or ch["channel_link"]
        joins = int(ch.get("joins_count") or 0)
        lines.append(
            f"<b>{ch['channel_title']}</b>\n"
            f"├ {e('people')} По ссылке: <b>{joins}</b>\n"
            f"└ 🔗 <a href=\"{url}\">invite-link</a>\n"
        )
    return "\n".join(lines)


def admin_panel_text() -> str:
    return f"{e('tools')} <b>Админ-панель PeterRate</b>"


@router.message(Command("admin"))
async def admin_cmd(message: Message, state: FSMContext) -> None:
    if not message.from_user:
        return
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа.")
        return
    await state.clear()
    await message.answer(
        admin_panel_text(),
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )


@router.message(Command("cancel"))
async def admin_cancel(message: Message, state: FSMContext) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    current = await state.get_state()
    if not current:
        return
    await state.clear()
    await message.answer(
        f"{plain('check')} Действие отменено.\n/admin — вернуться в панель",
        parse_mode="HTML",
    )


@router.callback_query(AdminCB.filter(F.action == "menu"))
async def admin_menu_back(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await callback.answer()
    await _edit_admin(callback, admin_panel_text(), admin_menu_kb())


@router.callback_query(AdminCB.filter(F.action == "close"))
async def admin_close(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await state.clear()
    await callback.answer()
    if callback.message:
        await callback.message.delete()


@router.callback_query(AdminCB.filter(F.action == "stats"))
async def admin_stats(callback: CallbackQuery, callback_data: AdminCB, repo: Repository) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    period = callback_data.period or "today"
    await callback.answer()
    text = await stats_text(repo, period)
    await _edit_admin(callback, text, admin_stats_kb(period))


@router.callback_query(AdminCB.filter(F.action == "users_count"))
async def admin_users(callback: CallbackQuery, repo: Repository) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    total = await repo.count_users()
    await callback.answer(f"{plain('people')} Всего пользователей: {total}", show_alert=True)


@router.callback_query(AdminCB.filter(F.action == "broadcast"))
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminStates.broadcast_text)
    if callback.message:
        await callback.message.answer(
            f"{plain('loudspeaker')} <b>Рассылка</b>\n\n"
            "Отправь текст сообщения (HTML).\n"
            "/cancel — отмена",
            parse_mode="HTML",
        )


@router.message(AdminStates.broadcast_text, F.text)
async def admin_broadcast_send(message: Message, state: FSMContext, repo: Repository) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer(f"{plain('check')} Рассылка отменена.")
        return

    await state.clear()
    user_ids = await repo.get_all_user_ids()
    if not user_ids:
        await message.answer("Нет пользователей для рассылки.")
        return

    sent = failed = 0
    status = await message.answer(f"{plain('loudspeaker')} Рассылка... 0/{len(user_ids)}")

    for i, uid in enumerate(user_ids):
        try:
            await message.bot.send_message(uid, message.text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
        if i % 25 == 0 and i > 0:
            try:
                await status.edit_text(f"{plain('loudspeaker')} Рассылка... {i}/{len(user_ids)}")
            except TelegramBadRequest:
                pass

    await repo.log_broadcast(message.from_user.id, (message.text or "")[:500], sent, failed)
    await status.edit_text(
        f"{plain('check')} <b>Рассылка завершена</b>\n\n"
        f"Отправлено: {sent}\nОшибок: {failed}",
        parse_mode="HTML",
    )


@router.callback_query(AdminCB.filter(F.action == "channels"))
async def admin_channels(callback: CallbackQuery, repo: Repository) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    channels = [dict(c) for c in await repo.get_active_channels()]
    text = await channels_admin_text(callback.bot, repo, channels)
    await _edit_admin(callback, text, admin_channels_kb(channels))


@router.callback_query(AdminCB.filter(F.action == "add_channel"))
async def admin_add_channel(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminStates.add_channel)
    if callback.message:
        await callback.message.answer(
            f"{plain('plus')} <b>Добавить канал</b>\n\n"
            "Отправь @username канала или ID <code>-100...</code>\n"
            "Бот должен быть админом канала.\n"
            "/cancel — отмена",
            parse_mode="HTML",
        )


@router.message(AdminStates.add_channel, F.text)
async def admin_save_channel(message: Message, state: FSMContext, repo: Repository) -> None:
    if not message.from_user or not is_admin(message.from_user.id):
        return
    if message.text and message.text.startswith("/cancel"):
        await state.clear()
        await message.answer(f"{plain('check')} Отменено.")
        return

    raw_id = message.text.strip()
    title = raw_id
    link = f"https://t.me/{raw_id.lstrip('@')}"
    channel_id = raw_id

    try:
        chat = await message.bot.get_chat(raw_id)
        channel_id = str(chat.id)
        title = chat.title or raw_id
        if chat.username:
            link = f"https://t.me/{chat.username}"
    except TelegramBadRequest:
        await message.answer(
            f"{plain('cross')} Не удалось найти канал. Проверь ID и права бота."
        )
        return

    invite_link = await create_tracked_invite(message.bot, channel_id)
    if not invite_link:
        await message.answer(
            f"{plain('warning')} Канал найден, но не удалось создать invite-ссылку.\n"
            "Сделай бота <b>админом канала</b> с правом приглашать пользователей.",
            parse_mode="HTML",
        )
        return

    await repo.add_channel(channel_id, title, invite_link, invite_link)
    await state.clear()
    channels = [dict(c) for c in await repo.get_active_channels()]
    await message.answer(
        f"{plain('check')} Канал <b>{title}</b> добавлен!\n"
        f"ID: <code>{channel_id}</code>\n"
        f"🔗 Трекинг-ссылка создана",
        reply_markup=admin_channels_kb(channels),
        parse_mode="HTML",
    )


@router.callback_query(AdminCB.filter(F.action == "del_channel"))
async def admin_del_channel(callback: CallbackQuery, callback_data: AdminCB, repo: Repository) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    if not callback_data.channel_id:
        await callback.answer("Ошибка: канал не найден", show_alert=True)
        return
    await repo.remove_channel(callback_data.channel_id)
    await callback.answer("Канал удалён")
    channels = [dict(c) for c in await repo.get_active_channels()]
    text = await channels_admin_text(callback.bot, repo, channels)
    await _edit_admin(callback, text, admin_channels_kb(channels))
