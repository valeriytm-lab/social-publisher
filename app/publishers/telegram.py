import json
from contextlib import ExitStack
from pathlib import Path

import httpx

from app.config import settings
from app.models import PublishResult
from app.publishers.base import BasePublisher


class TelegramPublisher(BasePublisher):
    def __init__(self) -> None:
        self.token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def is_configured(self) -> bool:
        return bool(self.token and self.chat_id)

    async def publish(
        self,
        text: str,
        images: list[Path] | None = None,
        video: Path | None = None,
        **kwargs: object,
    ) -> PublishResult:
        if not self.is_configured():
            return PublishResult(
                platform="telegram",
                success=False,
                message="Telegram не настроен. Укажите TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID.",
            )

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                if video:
                    return await self._send_video(client, text, video)
                if images:
                    return await self._send_photos(client, text, images)
                return await self._send_text(client, text)
        except httpx.HTTPError as e:
            return PublishResult(
                platform="telegram", success=False, message=f"Ошибка HTTP: {e}"
            )

    async def _send_text(self, client: httpx.AsyncClient, text: str) -> PublishResult:
        resp = await client.post(
            f"{self.base_url}/sendMessage",
            json={"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"},
        )
        data = resp.json()
        if data.get("ok"):
            msg_id = data["result"]["message_id"]
            return PublishResult(
                platform="telegram",
                success=True,
                message="Текст опубликован в Telegram.",
                url=f"https://t.me/c/{self.chat_id}/{msg_id}",
            )
        return PublishResult(
            platform="telegram",
            success=False,
            message=f"Ошибка Telegram API: {data.get('description', 'Unknown')}",
        )

    async def _send_photos(
        self, client: httpx.AsyncClient, text: str, images: list[Path]
    ) -> PublishResult:
        if len(images) == 1:
            with open(images[0], "rb") as f:
                resp = await client.post(
                    f"{self.base_url}/sendPhoto",
                    data={"chat_id": self.chat_id, "caption": text, "parse_mode": "HTML"},
                    files={"photo": (images[0].name, f, "image/jpeg")},
                )
            data = resp.json()
            if data.get("ok"):
                return PublishResult(
                    platform="telegram",
                    success=True,
                    message="Фото опубликовано в Telegram.",
                )
            return PublishResult(
                platform="telegram",
                success=False,
                message=f"Ошибка: {data.get('description', 'Unknown')}",
            )

        # Media group for multiple images
        media = []
        files = {}
        with ExitStack() as stack:
            for i, img in enumerate(images):
                media_item: dict[str, str] = {"type": "photo", "media": f"attach://photo{i}"}
                if i == 0:
                    media_item["caption"] = text
                    media_item["parse_mode"] = "HTML"
                media.append(media_item)
                fh = stack.enter_context(open(img, "rb"))
                files[f"photo{i}"] = (img.name, fh, "image/jpeg")

            resp = await client.post(
                f"{self.base_url}/sendMediaGroup",
                data={"chat_id": self.chat_id, "media": json.dumps(media)},
                files=files,
            )
            data = resp.json()
            if data.get("ok"):
                return PublishResult(
                    platform="telegram",
                    success=True,
                    message=f"{len(images)} фото опубликовано в Telegram.",
                )
            return PublishResult(
                platform="telegram",
                success=False,
                message=f"Ошибка: {data.get('description', 'Unknown')}",
            )

    async def _send_video(
        self, client: httpx.AsyncClient, text: str, video: Path
    ) -> PublishResult:
        with open(video, "rb") as f:
            resp = await client.post(
                f"{self.base_url}/sendVideo",
                data={"chat_id": self.chat_id, "caption": text, "parse_mode": "HTML"},
                files={"video": (video.name, f, "video/mp4")},
            )
        data = resp.json()
        if data.get("ok"):
            return PublishResult(
                platform="telegram",
                success=True,
                message="Видео опубликовано в Telegram.",
            )
        return PublishResult(
            platform="telegram",
            success=False,
            message=f"Ошибка: {data.get('description', 'Unknown')}",
        )
