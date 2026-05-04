# Social Publisher

Веб-приложение для одновременной публикации контента (текст, фото, видео) в:

- **Telegram** — через Bot API
- **Facebook** — страница и группа через Graph API
- **YouTube** — загрузка видео через YouTube Data API v3

## Быстрый старт

### 1. Установка

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### 2. Настройка

Скопируйте `.env.example` в `.env` и заполните токены:

```bash
cp .env.example .env
```

#### Telegram

1. Создайте бота через [@BotFather](https://t.me/BotFather) → получите `TELEGRAM_BOT_TOKEN`
2. Добавьте бота в канал/группу
3. Узнайте `TELEGRAM_CHAT_ID` (ID канала или группы)

#### Facebook

1. Создайте приложение на [Facebook Developers](https://developers.facebook.com/)
2. Получите Page Access Token через [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
3. Нужны разрешения: `pages_manage_posts`, `pages_read_engagement`, `publish_to_groups`

#### YouTube

1. Создайте проект в [Google Cloud Console](https://console.cloud.google.com/)
2. Включите YouTube Data API v3
3. Создайте OAuth 2.0 Client ID (тип: Web application)
4. Получите refresh token через OAuth 2.0 flow

### 3. Запуск

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Откройте http://localhost:8000

## API

### `GET /api/status`

Возвращает статус настройки каждой платформы.

### `POST /api/publish`

Публикует контент. Принимает `multipart/form-data`:

| Поле | Тип | Описание |
|------|-----|----------|
| `text` | string | Текст поста |
| `platforms` | string | Через запятую: `telegram,facebook_page,facebook_group,youtube` |
| `images` | file[] | Изображения (можно несколько) |
| `video` | file | Видеофайл |
| `youtube_title` | string | Название видео для YouTube |
| `youtube_description` | string | Описание для YouTube |
| `youtube_tags` | string | Теги через запятую |
| `youtube_privacy` | string | `public`, `unlisted`, `private` |

## Технологии

- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) + [httpx](https://www.python-httpx.org/)
- **Frontend**: Vanilla HTML/CSS/JS
- **APIs**: Telegram Bot API, Facebook Graph API v21.0, YouTube Data API v3
