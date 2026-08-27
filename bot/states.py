from aiogram.fsm.state import State, StatesGroup


class GuestForm(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_company = State()
    waiting_position = State()