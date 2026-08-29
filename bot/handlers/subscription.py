import logging

from aiogram import Router
from aiogram.types import ChatMemberUpdated

from bot.database.repo import Repository

logger = logging.getLogger(__name__)

router = Router(name="subscription")

JOIN_STATUSES = frozenset({"member", "restricted", "administrator", "creator"})
LEFT_STATUSES = frozenset({"left", "kicked"})


@router.chat_member()
async def on_channel_join(event: ChatMemberUpdated, repo: Repository) -> None:
    """Track joins via bot-created invite links."""
    if not event.invite_link or not event.invite_link.invite_link:
        return

    old_status = event.old_chat_member.status
    new_status = event.new_chat_member.status

    if old_status not in LEFT_STATUSES or new_status not in JOIN_STATUSES:
        return

    updated = await repo.increment_joins_by_invite(event.invite_link.invite_link)
    if updated:
        logger.info(
            "Join via invite link: user=%s channel=%s",
            event.new_chat_member.user.id,
            event.chat.id,
        )
