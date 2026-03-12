from __future__ import annotations

import os
from dataclasses import dataclass

from aiogram import Bot


@dataclass(slots=True)
class StorageService:
    bot: Bot
    base_dir: str = "storage"

    async def save_telegram_photos(self, order_id: int, kind: str, file_ids: list[str]) -> list[str]:
        os.makedirs(self.base_dir, exist_ok=True)
        out_dir = os.path.join(self.base_dir, f"order_{order_id}", kind)
        os.makedirs(out_dir, exist_ok=True)

        saved: list[str] = []
        for idx, file_id in enumerate(file_ids, start=1):
            file = await self.bot.get_file(file_id)
            path = os.path.join(out_dir, f"{idx}.jpg")
            await self.bot.download_file(file.file_path, destination=path)
            saved.append(path)
        return saved
