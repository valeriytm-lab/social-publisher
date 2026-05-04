from pathlib import Path

import httpx

from app.config import settings
from app.models import PublishResult
from app.publishers.base import BasePublisher

GRAPH_API = "https://graph.facebook.com/v21.0"


class FacebookPublisher(BasePublisher):
    def __init__(self, target: str = "page") -> None:
        self.access_token = settings.facebook_access_token
        self.target = target
        if target == "page":
            self.target_id = settings.facebook_page_id
        else:
            self.target_id = settings.facebook_group_id

    def is_configured(self) -> bool:
        return bool(self.access_token and self.target_id)

    async def publish(
        self,
        text: str,
        images: list[Path] | None = None,
        video: Path | None = None,
        **kwargs: object,
    ) -> PublishResult:
        platform = f"facebook_{self.target}"
        if not self.is_configured():
            return PublishResult(
                platform=platform,
                success=False,
                message=f"Facebook ({self.target}) не настроен. Укажите токен и ID.",
            )

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                if video:
                    return await self._publish_video(client, text, video, platform)
                if images:
                    return await self._publish_photos(client, text, images, platform)
                return await self._publish_text(client, text, platform)
        except httpx.HTTPError as e:
            return PublishResult(
                platform=platform, success=False, message=f"Ошибка HTTP: {e}"
            )

    async def _publish_text(
        self, client: httpx.AsyncClient, text: str, platform: str
    ) -> PublishResult:
        resp = await client.post(
            f"{GRAPH_API}/{self.target_id}/feed",
            data={"message": text, "access_token": self.access_token},
        )
        data = resp.json()
        if "id" in data:
            post_id = data["id"]
            return PublishResult(
                platform=platform,
                success=True,
                message=f"Текст опубликован в Facebook ({self.target}).",
                url=f"https://facebook.com/{post_id}",
            )
        error = data.get("error", {}).get("message", "Unknown error")
        return PublishResult(
            platform=platform, success=False, message=f"Ошибка Facebook: {error}"
        )

    async def _publish_photos(
        self,
        client: httpx.AsyncClient,
        text: str,
        images: list[Path],
        platform: str,
    ) -> PublishResult:
        if len(images) == 1:
            with open(images[0], "rb") as f:
                resp = await client.post(
                    f"{GRAPH_API}/{self.target_id}/photos",
                    data={"caption": text, "access_token": self.access_token},
                    files={"source": (images[0].name, f, "image/jpeg")},
                )
            data = resp.json()
            if "id" in data:
                return PublishResult(
                    platform=platform,
                    success=True,
                    message=f"Фото опубликовано в Facebook ({self.target}).",
                    url=f"https://facebook.com/{data['id']}",
                )
            error = data.get("error", {}).get("message", "Unknown error")
            return PublishResult(
                platform=platform, success=False, message=f"Ошибка: {error}"
            )

        # Multiple photos: upload each unpublished, then create post with attachments
        photo_ids = []
        for img in images:
            with open(img, "rb") as f:
                resp = await client.post(
                    f"{GRAPH_API}/{self.target_id}/photos",
                    data={
                        "published": "false",
                        "access_token": self.access_token,
                    },
                    files={"source": (img.name, f, "image/jpeg")},
                )
            data = resp.json()
            if "id" in data:
                photo_ids.append(data["id"])

        if not photo_ids:
            return PublishResult(
                platform=platform,
                success=False,
                message="Не удалось загрузить фото в Facebook.",
            )

        attached: dict[str, str] = {"message": text, "access_token": self.access_token}
        for i, pid in enumerate(photo_ids):
            attached[f"attached_media[{i}]"] = f'{{"media_fbid":"{pid}"}}'

        resp = await client.post(
            f"{GRAPH_API}/{self.target_id}/feed",
            data=attached,
        )
        data = resp.json()
        if "id" in data:
            return PublishResult(
                platform=platform,
                success=True,
                message=f"{len(photo_ids)} фото опубликовано в Facebook ({self.target}).",
                url=f"https://facebook.com/{data['id']}",
            )
        error = data.get("error", {}).get("message", "Unknown error")
        return PublishResult(
            platform=platform, success=False, message=f"Ошибка: {error}"
        )

    async def _publish_video(
        self,
        client: httpx.AsyncClient,
        text: str,
        video: Path,
        platform: str,
    ) -> PublishResult:
        with open(video, "rb") as f:
            resp = await client.post(
                f"{GRAPH_API}/{self.target_id}/videos",
                data={
                    "description": text,
                    "access_token": self.access_token,
                },
                files={"source": (video.name, f, "video/mp4")},
            )
        data = resp.json()
        if "id" in data:
            return PublishResult(
                platform=platform,
                success=True,
                message=f"Видео опубликовано в Facebook ({self.target}).",
                url=f"https://facebook.com/{data['id']}",
            )
        error = data.get("error", {}).get("message", "Unknown error")
        return PublishResult(
            platform=platform, success=False, message=f"Ошибка: {error}"
        )
