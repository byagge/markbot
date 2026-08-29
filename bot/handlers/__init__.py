from aiogram import Router

from bot.handlers import admin, menu, rate_other, rate_self, share, start, subscribe_check, subscription, top

router = Router()
router.include_router(admin.router)
router.include_router(subscription.router)
router.include_router(subscribe_check.router)
router.include_router(start.router)
router.include_router(menu.router)
router.include_router(rate_self.router)
router.include_router(rate_other.router)
router.include_router(top.router)
router.include_router(share.router)
