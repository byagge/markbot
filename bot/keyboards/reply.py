from aiogram.types import KeyboardButton, KeyboardButtonRequestUsers, ReplyKeyboardMarkup, ReplyKeyboardRemove

CANCEL_TEXTS = {"назад", "отмена", "⬅️ назад", "/cancel"}
PICK_USER_TEXT = "Выбрать пользователя"


def rate_other_pick_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=PICK_USER_TEXT,
                    request_users=KeyboardButtonRequestUsers(
                        request_id=1,
                        user_is_bot=False,
                        max_quantity=1,
                        request_name=True,
                        request_username=True,
                        request_photo=True,
                    ),
                )
            ],
            [KeyboardButton(text="Назад")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        is_persistent=False,
        input_field_placeholder="@username или перешли сообщение",
    )


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
