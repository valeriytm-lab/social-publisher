from pydantic import BaseModel


class PublishRequest(BaseModel):
    text: str = ""
    platforms: list[str] = ["telegram", "facebook_page", "facebook_group", "youtube"]
    youtube_title: str = ""
    youtube_description: str = ""
    youtube_tags: list[str] = []
    youtube_privacy: str = "public"


class PublishResult(BaseModel):
    platform: str
    success: bool
    message: str
    url: str | None = None
