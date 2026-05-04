from abc import ABC, abstractmethod
from pathlib import Path

from app.models import PublishResult


class BasePublisher(ABC):
    @abstractmethod
    async def publish(
        self,
        text: str,
        images: list[Path] | None = None,
        video: Path | None = None,
        **kwargs: object,
    ) -> PublishResult:
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        ...
