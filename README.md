# ProfileMark README

# ProfileMark Bot

Telegram-бот для оценки профилей (0–100 баллов) с OpenAI-вердиктами, топом, сравнением и админ-панелью.

## Возможности

- **Оценить свой профиль** — анимация анализа, разбор по 5 категориям, AI-вердикт
- **Оценить другого** — по @username или пересланному сообщению
- **Топ-10** — общий, по подаркам, по юзернейму, друзья
- **Как считается рейтинг** — справка
- **Single message nav** — все экраны через edit (кроме `/start`)
- **Админ-панель** (`/admin`) — статистика, рассылка, обязательная подписка
- **Цветные кнопки** — primary / success / danger (Telegram Bot API 9.4+)

## Быстрый старт

```bash
cd profilemark
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env        # заполнить BOT_TOKEN, ADMIN_IDS, OPENAI_API_KEY
python run.py
```

## .env

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен от @BotFather |
| `ADMIN_IDS` | ID админов через запятую |
| `OPENAI_API_KEY` | Ключ OpenAI (вердикты; без ключа — fallback-тексты) |
| `OPENAI_MODEL` | Модель, по умолчанию `gpt-4o-mini` |
| `BOT_USERNAME` | Username бота без @ |
| `WELCOME_STICKER_ID` | file_id стикера на /start (опционально) |

## Админ

- `/admin` — панель управления
- **Статистика** — пользователи, оценки, активность по периодам
- **Рассылка** — HTML-сообщение всем пользователям
- **Подписка** — добавление каналов `@channel` или `-100...`

## Стек

- Python 3.11+
- aiogram 3.17
- OpenAI API
- SQLite (aiosqlite)

## Примечание

Бот использует Telegram Bot API (`getUserGifts`, `getChat`) для реальных подарков и описания профиля. Если пользователь скрыл данные в приватности — категория получает 0 баллов.
