# ClosedClub project rules

These instructions apply to the entire repository and are mandatory for every AI agent and contributor.

## Product

- ClosedClub is a Telegram Web App for a private investment community.
- The current product flow has three screens: landing page, membership application, and submission confirmation.
- The Telegram bot must answer `/start` and `/help` with a button that opens the Web App. `/admin` only explains that the admin panel is not available yet.
- The application fields are first name, last name, occupation, monthly income, and city.
- The stack is React, FastAPI, PostgreSQL, Caddy, and Docker Compose.
- Do not add an admin panel until it is explicitly requested.

## Architecture invariants

- Everything application-specific runs in Docker containers. Do not install Node.js, Python, PostgreSQL, Caddy, or app packages directly on the VPS.
- Caddy is the only public application entry point. Frontend, backend, and database ports must not be published on the host.
- PostgreSQL data must live in its named Docker volume.
- Secrets belong only in the untracked `.env` or an external secret store. Never commit credentials, bot tokens, VPN profiles, SSH keys, or production database passwords.
- Telegram updates use the authenticated FastAPI webhook. Keep the webhook secret validation and the Web App launch button intact.
- The normal deployment is exactly: `git pull` followed by `docker compose up -d --build`. Do not reboot the VPS for an application deployment.
- Preserve existing VPS services and port ownership. The project currently publishes only HTTPS on port 443 because host nginx/ISPmanager owns port 80.

## ClosedClub server rule: не тупи с VPS и VPN

1. Не трогай WireGuard, KVN, DNS, systemd или network, если задача не про VPN. Деплой приложения — `git pull` плюс `docker compose up -d --build`, без рестартов KVN.
2. `wg-quick@KVN active` не значит «работает». Проверка только так: `wg show KVN latest-handshakes`; `curl ifconfig.me` должен показывать адрес, отличный от IP сервера; `curl -I api.telegram.org` должен отвечать; публичные адреса и `/api/health` должны давать `200`; новый SSH-сеанс должен держаться.
3. Никаких циклов `restart VPN -> wait -> rollback -> restart again`. Максимум один контролируемый эксперимент, затем остановиться и дать диагноз.
4. Если VPN действительно нужно менять: сначала показать план, поставить автоматический rollback на 10 минут, выполнить один общий SSH-блок и отменить rollback только после проверки egress, Telegram API, нового SSH и HTTPS.
5. Не ломать split-routing: ответы на входящие соединения 22, 80 и 443 возвращаются через `eth0`, исходящий серверный трафик идёт через KVN.
6. Ошибки `docker pull` или build сначала диагностировать как DNS/registry/network-проблему, а не как поломку приложения. Логи смотреть через `tail`, без вывода огромных простыней.
7. Финальный DoD: контейнеры подняты; PostgreSQL здоров; `/api/health` отвечает `200`; тестовая заявка создаётся в PostgreSQL; публичный HTTPS отвечает `200`; Telegram API доступен через существующий маршрут/VPN; новый SSH-сеанс работает.
8. Отчёт короткий: причина, что сделано, доказательство. Не писать «готово», пока smoke-тест не пройден.

## Application rules

- Validate all application input in FastAPI; never trust client-side validation alone.
- Do not expose a public endpoint that lists applications or personal data.
- Every application must carry server-validated Telegram `initData`; store the verified Telegram user ID so the bot can contact the applicant later.
- Do not log form bodies or database credentials.
- Keep the UI mobile-first and usable inside Telegram's WebView.
- Schema changes must remain backward-compatible or receive an explicit migration.
- Before claiming completion, run the smoke test in `scripts/verify.sh` and visually test all three screens.
