from pydantic import BaseModel


class PublishRequest(BaseModel):
    text: str = ""
    platforms: list[str] = ["telegram", "facebook_page", "facebook_group", "youtube"]

    # Facebook
    fb_title: str = ""
    fb_description: str = ""
    fb_comment: str = ""

    # YouTube
    youtube_title: str = ""
    youtube_description: str = ""
    youtube_tags: list[str] = []
    youtube_privacy: str = "public"
    youtube_playlist: str = ""
    youtube_made_for_kids: bool = False
    youtube_comment: str = ""


class PublishResult(BaseModel):
    platform: str
    success: bool
    message: str
    url: str | None = None
