# ClosedClub Telegram Web App

ClosedClub — закрытое инвестиционное сообщество. Текущая версия содержит Telegram-бота с кнопкой запуска, мобильный лендинг, форму заявки и экран подтверждения. Каждая заявка подписывается Telegram `initData`, проверяется FastAPI и сохраняется в PostgreSQL вместе с Telegram user ID. Админки и публичного API для чтения заявок пока нет.

## Состав

- `frontend/` — React + Vite, три маршрута: `/`, `/apply`, `/success`;
- `backend/` — FastAPI, Telegram webhook, SQLAlchemy и Alembic;
- PostgreSQL — отдельный контейнер с именованным volume;
- Caddy — единственная публичная точка входа, HTTPS и reverse proxy;
- Docker Compose — сборка и запуск всей системы.

```text
Internet :443 -> Caddy -> React/Nginx :8080
                       -> FastAPI :8000 -> PostgreSQL :5432
Telegram /start -------> FastAPI webhook -> sendMessage + Web App button
```

Frontend, backend и PostgreSQL не публикуют порты на VPS. Данные базы сохраняются в volume `telegram-community-postgres-data`. Сертификаты Caddy сохраняются в существующих volumes.

## Конфигурация

Скопируйте пример и замените значения:

```sh
cp .env.example .env
chmod 600 .env
```

Обязательные переменные:

- `SITE_ADDRESS` — домен или текущий публичный IP;
- `TELEGRAM_WEBHOOK_ADDRESS` — DNS-имя для Telegram webhook, указывающее на VPS;
- `ACME_EMAIL` — email для ACME;
- `POSTGRES_DB` и `POSTGRES_USER` — имя базы и пользователь;
- `POSTGRES_PASSWORD` — длинный случайный пароль, который не коммитится;
- `TELEGRAM_BOT_TOKEN` — актуальный токен бота для серверной проверки Telegram `initData`;
- `TELEGRAM_WEBHOOK_SECRET` — случайная строка из 32–256 латинских букв, цифр, `_` и `-`.

## Деплой

На VPS нужны только Docker Engine и Compose plugin. Node.js, Python, PostgreSQL и Caddy вручную не устанавливаются.

```sh
git pull
docker compose up -d --build
./scripts/verify.sh
```

Скрипт проверки ждёт healthchecks, проверяет публичный HTTPS, `/api/health`, защиту Telegram webhook, создаёт временную заявку через API, подтверждает её наличие в PostgreSQL, удаляет тестовую запись и проверяет доступность Telegram API.

## Подключение Telegram-бота

После деплоя запустите с компьютера, которому доступен `api.telegram.org`:

```sh
python scripts/configure_bot.py \
  --web-app-url https://109.172.6.81/ \
  --webhook-url https://109-172-6-81.sslip.io/api/telegram/webhook
```

Если на машине несколько сетевых маршрутов, можно явно выбрать исходящий адрес: `--source-address 192.168.1.8`.

Скрипт безопасно запросит токен и webhook secret без вывода на экран, затем настроит имя `ClosedClub`, команды `/start` и `/help`, постоянную кнопку меню и HTTPS webhook. Для webhook используется DNS-имя, потому что Telegram ожидает HTTPS-хост с подходящим сертификатом; Web App при этом может оставаться на текущем IP. FastAPI проверяет заголовок `X-Telegram-Bot-Api-Secret-Token`; на `/start` Telegram получает сообщение с кнопкой «Открыть ClosedClub».

Ответ `sendMessage` передаётся прямо в HTTP-ответе webhook, поэтому стартовый экран работает без исходящего запроса VPS к Bot API. Для будущих отложенных уведомлений и произвольных сообщений серверу всё равно потребуется рабочий egress к `api.telegram.org`.

## API

`GET /api/health` возвращает состояние API и базы.

`POST /api/applications` принимает заголовок `X-Telegram-Init-Data` из Telegram Web App и тело:

```json
{
  "first_name": "Александр",
  "last_name": "Иванов",
  "occupation": "Предприниматель",
  "monthly_income": 500000,
  "city": "Москва"
}
```

Backend проверяет подпись и срок действия `initData`, сохраняет `telegram_user_id` для будущего ответа через бота и ограничивает число заявок от одного пользователя. Эндпоинта для чтения заявок нет. Миграции выполняются одноразовым контейнером `migrate` перед запуском backend.

## Правила сервера

Обязательные проектные и VPS-правила находятся в `AGENTS.md`; `CLAUDE.md` направляет Claude к тому же источнику. Деплой приложения не даёт разрешения менять VPN, KVN, DNS, systemd, маршруты или перезагружать VPS.

Порт 80 намеренно не публикуется этим Compose-проектом, поскольку он занят существующим nginx/ISPmanager. Для IP используется краткосрочный ACME-профиль; Caddy обновляет сертификат автоматически.
