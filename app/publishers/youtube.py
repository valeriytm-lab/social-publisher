import json
from pathlib import Path

import httpx

from app.config import settings
from app.models import PublishResult
from app.publishers.base import BasePublisher

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


class YouTubePublisher(BasePublisher):
    def __init__(self) -> None:
        self.client_id = settings.youtube_client_id
        self.client_secret = settings.youtube_client_secret
        self.refresh_token = settings.youtube_refresh_token

    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    async def _get_access_token(self, client: httpx.AsyncClient) -> str | None:
        resp = await client.post(
            TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token,
                "grant_type": "refresh_token",
            },
        )
        data = resp.json()
        return data.get("access_token")

    async def publish(
        self,
        text: str,
        images: list[Path] | None = None,
        video: Path | None = None,
        **kwargs: object,
    ) -> PublishResult:
        if not self.is_configured():
            return PublishResult(
                platform="youtube",
                success=False,
                message="YouTube не настроен. Укажите client_id, client_secret и refresh_token.",
            )

        if not video:
            return PublishResult(
                platform="youtube",
                success=False,
                message="YouTube требует видеофайл для публикации.",
            )

        title = str(kwargs.get("youtube_title", "")) or "Без названия"
        description = str(kwargs.get("youtube_description", "")) or text
        tags = kwargs.get("youtube_tags", [])
        if not isinstance(tags, list):
            tags = []
        privacy = str(kwargs.get("youtube_privacy", "public"))

        try:
            async with httpx.AsyncClient(timeout=300) as client:
                access_token = await self._get_access_token(client)
                if not access_token:
                    return PublishResult(
                        platform="youtube",
                        success=False,
                        message="Не удалось получить access token для YouTube.",
                    )

                return await self._upload_video(
                    client, access_token, video, title, description, tags, privacy
                )
        except httpx.HTTPError as e:
            return PublishResult(
                platform="youtube", success=False, message=f"Ошибка HTTP: {e}"
            )

    async def _upload_video(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        video: Path,
        title: str,
        description: str,
        tags: list[str],
        privacy: str,
    ) -> PublishResult:
        metadata = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22",
            },
            "status": {"privacyStatus": privacy},
        }

        # Resumable upload: init
        init_resp = await client.post(
            f"{UPLOAD_URL}?uploadType=resumable&part=snippet,status",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": "video/*",
                "X-Upload-Content-Length": str(video.stat().st_size),
            },
            content=json.dumps(metadata),
        )

        if init_resp.status_code != 200:
            return PublishResult(
                platform="youtube",
                success=False,
                message=f"Ошибка инициализации загрузки: {init_resp.status_code} {init_resp.text}",
            )

        upload_url = init_resp.headers.get("Location")
        if not upload_url:
            return PublishResult(
                platform="youtube",
                success=False,
                message="Не получен URL для загрузки видео.",
            )

        # Upload the video file
        with open(video, "rb") as f:
            upload_resp = await client.put(
                upload_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "video/*",
                },
                content=f.read(),
            )

        if upload_resp.status_code in (200, 201):
            data = upload_resp.json()
            video_id = data.get("id", "")
            return PublishResult(
                platform="youtube",
                success=True,
                message="Видео опубликовано на YouTube.",
                url=f"https://www.youtube.com/watch?v={video_id}",
            )

        return PublishResult(
            platform="youtube",
            success=False,
            message=f"Ошибка загрузки видео: {upload_resp.status_code} {upload_resp.text}",
        )
