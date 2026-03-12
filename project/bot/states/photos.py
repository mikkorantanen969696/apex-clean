from aiogram.fsm.state import State, StatesGroup


class PhotoUploadStates(StatesGroup):
    before_photos = State()
    after_photos = State()
