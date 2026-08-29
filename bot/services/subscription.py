from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from bot.database.repo import Repository
from bot.utils.texts import subscribe_text


async def create_tracked_invite(bot: Bot, channel_id: str) -> str | None:
    """Create Telegram invite link with join tracking."""
    try:
        invite = await bot.create_chat_invite_link(
            chat_id=channel_id,
            name="ProfileMark",
        )
        return invite.invite_link
    except TelegramBadRequest:
        return None


async def ensure_channel_links(bot: Bot, repo: Repository, channel: dict) -> dict:
    """Ensure channel has tracked invite link; fallback to public link."""
    ch = dict(channel)
    if ch.get("invite_link"):
        return ch

    invite = await create_tracked_invite(bot, ch["channel_id"])
    if invite:
        await repo.set_invite_link(ch["channel_id"], invite)
        ch["invite_link"] = invite
        ch["channel_link"] = invite
    return ch


def subscribe_url(channel: dict) -> str:
    return channel.get("invite_link") or channel["channel_link"]


async def get_missing_channels(bot: Bot, repo: Repository, user_id: int) -> list[dict]:
    channels = await repo.get_active_channels()
    if not channels:
        return []

    missing: list[dict] = []
    for row in channels:
        ch = dict(row)
        try:
            member = await bot.get_chat_member(ch["channel_id"], user_id)
            if member.status in ("left", "kicked"):
                ch = await ensure_channel_links(bot, repo, ch)
                missing.append(ch)
        except Exception:
            ch = await ensure_channel_links(bot, repo, ch)
            missing.append(ch)
    return missing


def format_subscribe_message(missing: list[dict]) -> str:
    lines = []
    for ch in missing:
        url = subscribe_url(ch)
        lines.append(f"• <a href=\"{url}\">{ch['channel_title']}</a>")
    return subscribe_text("\n".join(lines))
