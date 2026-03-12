import asyncio

from project.bot.dispatcher import build_dispatcher
from project.bot.lifecycle import on_startup
from project.config.settings import Settings
from project.utils.logging import setup_logging


async def main() -> None:
    settings = Settings()
    setup_logging(settings)

    dp, bot = build_dispatcher(settings)
    await on_startup(settings)

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
