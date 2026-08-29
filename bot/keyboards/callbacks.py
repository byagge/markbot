from aiogram.filters.callback_data import CallbackData


class MenuCB(CallbackData, prefix="m"):
    action: str


class RateCB(CallbackData, prefix="r"):
    action: str
    uid: int = 0


class TopCB(CallbackData, prefix="t"):
    action: str
    category: str = "general"


class AdminCB(CallbackData, prefix="a"):
    action: str
    period: str | None = None
    channel_id: str | None = None


class SubCB(CallbackData, prefix="sub"):
    action: str = "check"
