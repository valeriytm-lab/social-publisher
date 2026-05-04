import asyncio
import shutil
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import PublishRequest, PublishResult
from app.publishers.facebook import FacebookPublisher
from app.publishers.telegram import TelegramPublisher
from app.publishers.youtube import YouTubePublisher

app = FastAPI(title="Social Publisher", version="1.0.0")

UPLOAD_DIR = Path(settings.upload_dir)
UPLOAD_DIR.mkdir(exist_ok=True)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html_path = STATIC_DIR / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/api/status")
async def status() -> dict[str, object]:
    telegram = TelegramPublisher()
    fb_page = FacebookPublisher(target="page")
    fb_group = FacebookPublisher(target="group")
    youtube = YouTubePublisher()

    return {
        "platforms": {
            "telegram": telegram.is_configured(),
            "facebook_page": fb_page.is_configured(),
            "facebook_group": fb_group.is_configured(),
            "youtube": youtube.is_configured(),
        }
    }


@app.post("/api/publish")
async def publish(
    text: str = Form(""),
    platforms: str = Form("telegram,facebook_page,facebook_group,youtube"),
    youtube_title: str = Form(""),
    youtube_description: str = Form(""),
    youtube_tags: str = Form(""),
    youtube_privacy: str = Form("public"),
    images: list[UploadFile] = File(default=[]),  # noqa: B008
    video: UploadFile | None = File(default=None),  # noqa: B008
) -> dict[str, list[PublishResult]]:
    platform_list = [p.strip() for p in platforms.split(",") if p.strip()]

    req = PublishRequest(
        text=text,
        platforms=platform_list,
        youtube_title=youtube_title,
        youtube_description=youtube_description,
        youtube_tags=[t.strip() for t in youtube_tags.split(",") if t.strip()],
        youtube_privacy=youtube_privacy,
    )

    # Save uploaded files
    saved_images: list[Path] = []
    saved_video: Path | None = None

    for img in images:
        if img.filename and img.size and img.size > 0:
            img_path = UPLOAD_DIR / img.filename
            with open(img_path, "wb") as f:
                shutil.copyfileobj(img.file, f)
            saved_images.append(img_path)

    if video and video.filename and video.size and video.size > 0:
        video_path = UPLOAD_DIR / video.filename
        with open(video_path, "wb") as f:
            shutil.copyfileobj(video.file, f)
        saved_video = video_path

    # Publish to selected platforms
    tasks = []
    publishers: dict[str, TelegramPublisher | FacebookPublisher | YouTubePublisher] = {}

    if "telegram" in req.platforms:
        publishers["telegram"] = TelegramPublisher()
    if "facebook_page" in req.platforms:
        publishers["facebook_page"] = FacebookPublisher(target="page")
    if "facebook_group" in req.platforms:
        publishers["facebook_group"] = FacebookPublisher(target="group")
    if "youtube" in req.platforms:
        publishers["youtube"] = YouTubePublisher()

    for name, publisher in publishers.items():
        extra_kwargs: dict[str, object] = {}
        if name == "youtube":
            extra_kwargs = {
                "youtube_title": req.youtube_title,
                "youtube_description": req.youtube_description,
                "youtube_tags": req.youtube_tags,
                "youtube_privacy": req.youtube_privacy,
            }
        tasks.append(
            publisher.publish(
                text=req.text,
                images=saved_images if saved_images else None,
                video=saved_video,
                **extra_kwargs,
            )
        )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    publish_results: list[PublishResult] = []
    platform_names = list(publishers.keys())
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            publish_results.append(
                PublishResult(
                    platform=platform_names[i],
                    success=False,
                    message=f"Ошибка: {result}",
                )
            )
        else:
            publish_results.append(result)

    # Cleanup uploaded files
    for img_path in saved_images:
        img_path.unlink(missing_ok=True)
    if saved_video:
        saved_video.unlink(missing_ok=True)

    return {"results": publish_results}
