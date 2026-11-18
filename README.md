# Keitaro Wrapper

Обёртка над Keitaro Admin API для тестового задания Adrobot.

## Возможности

1. **Создаватор кампаний** — принимает название, гео-код и ID оффера, создаёт кампанию с двумя потоками:
   - поток с фильтром страны → редирект на Google;
   - поток с выбранным оффером.
   Если ID не заданы в `.env`: домен — первый из API, группа и источник — первая запись, в имени которой есть `fortest`, иначе тоже первая.
2. **Редактор офферов** — `Fetch Streams`, add/remove/bring back, pin весов, локальный черновик, `Push to Keitaro` / `Cancel`.

Стек: **FastAPI + SQLAlchemy + Alembic** (backend), **React + Vite** (frontend), SQLite.

## Требования

- Python 3.11+
- Node.js 18+
- API-ключ Keitaro Admin API (в админке: ключи API пользователя)

## Быстрый старт

### 1. Переменные окружения

```bash
cp .env.example .env
```

Заполните в `.env`:

```env
KEITARO_BASE_URL=https://tlgk.host
KEITARO_API_KEY=ваш_ключ

# необязательно. Пусто: домен — первый из API,
# группа и источник — имя содержит fortest, иначе первый в списке
KEITARO_DOMAIN_ID=
KEITARO_GROUP_ID=
KEITARO_TRAFFIC_SOURCE_ID=
```

### 2. Backend

```bash
cd backend
python -m venv .venv

# Windows Git Bash / bash
source .venv/Scripts/activate

# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Проверка: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Откройте [http://127.0.0.1:5173](http://127.0.0.1:5173).

## Миграции

Миграции лежат в `backend/alembic/versions`.

```bash
cd backend
source .venv/Scripts/activate
alembic upgrade head
```

Локальная БД по умолчанию: `backend/keitaro_wrapper.db` (пути относительно cwd при запуске uvicorn из `backend`).

## API (кратко)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/campaigns` | Создать кампанию `{name, geo, offer_id}` |
| GET | `/api/campaigns` | Список кампаний из Keitaro |
| POST | `/api/campaigns/{id}/streams/fetch` | Забрать потоки в локальный черновик |
| POST | `/api/campaigns/streams/{id}/offers` | Добавить оффер |
| DELETE | `/api/campaigns/streams/{id}/offers/{offer_id}` | Удалить (локально) |
| POST | `/api/campaigns/streams/{id}/offers/{offer_id}/bring-back` | Вернуть оффер |
| POST | `/api/campaigns/streams/{id}/offers/{offer_id}/pin` | Pin/unpin веса |
| POST | `/api/campaigns/streams/{id}/push` | Опубликовать в Keitaro |
| POST | `/api/campaigns/streams/{id}/cancel` | Откатить черновик |
| GET | `/api/meta/offers?q=` | Поиск офферов |

## Логика редактора

- Потоки без офферов показываются как пустые оболочки, фильтры и редирект не разбираются.
- Правки сначала локальные (жёлтый блок, пока не опубликован).
- Повторный Fetch не затирает грязный черновик. Такой поток остаётся жёлтым, на экране есть пометка. Чтобы забрать Keitaro заново, сначала Push или Cancel.
- Поток, которого больше нет в Keitaro, из локальной базы убирается.
- При add/remove/bring back доли незакреплённых офферов делятся так, чтобы сумма активных была 100%. Pin не меняется и не сжимается. Если закреплённые доли не оставляют сумму 100%, действие отклоняется.
- Долю pin меняют в поле и подтверждают Enter или уходом из поля.
- `Push` отправляет список офферов и долей, остальные поля потока берёт как есть из Keitaro. Сумма должна быть 100%.
- `Cancel` возвращает состояние к последнему опубликованному снимку.

## Замечания

- Cloudflare на трекере может резать запросы без браузерного `User-Agent` — клиент уже отправляет Chrome UA.
- Секреты не коммитьте: `.env` в `.gitignore`.
