from aiogram.fsm.state import State, StatesGroup


class OrderCreateStates(StatesGroup):
    city = State()
    address = State()
    cleaning_type = State()
    scheduled_time = State()
    description = State()
    price = State()
    client_name = State()
    client_phone = State()
