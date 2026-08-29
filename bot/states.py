from aiogram.fsm.state import State, StatesGroup


class RateOtherStates(StatesGroup):
    waiting_target = State()


class AdminStates(StatesGroup):
    broadcast_text = State()
    add_channel = State()
