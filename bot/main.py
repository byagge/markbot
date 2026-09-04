import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats

from bot.config import settings
from bot.database import db
from bot.handlers import router
from bot.middlewares import DatabaseMiddleware, SubscriptionMiddleware
from bot.services import user_client

from bot.utils.emoji import plain

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand(command="start", description=f"{plain('home')} Главное меню"),
    BotCommand(command="menu", description=f"{plain('memo')} Меню"),
]


async def on_startup(bot: Bot) -> None:
    await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeAllPrivateChats())
    me = await bot.get_me()
    logger.info("Bot @%s ready", me.username)
    if settings.telegram_api_id and settings.telegram_api_hash and settings.telegram_session:
        ok = await user_client.init(
            settings.telegram_api_id,
            settings.telegram_api_hash,
            settings.telegram_session,
        )
        if not ok:
            logger.warning("Pyrogram user client not available — gifts/username via Bot API only")
    else:
        logger.info("Pyrogram user client not configured (TELEGRAM_API_ID/HASH/SESSION)")


async def on_shutdown(bot: Bot) -> None:
    await user_client.close()


async def main() -> None:
    await db.init()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.update.middleware(DatabaseMiddleware())
    dp.update.middleware(SubscriptionMiddleware())
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.include_router(router)

    logger.info("PeterRate bot starting...")
    await dp.start_polling(
        bot,
        allowed_updates=["message", "callback_query", "chat_member", "inline_query"],
    )


if __name__ == "__main__":
    asyncio.run(main())
