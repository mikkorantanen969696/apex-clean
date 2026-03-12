# Apex Clean — Telegram Mini-CRM (aiogram 3 / PostgreSQL / Redis)

Telegram-бот для управления клининговым бизнесом (ADMIN / MANAGER / CLEANER) с публикацией заявок в супергруппу с темами (forum topics).

## Стек

- Python 3.11
- aiogram 3.x (polling по умолчанию)
- PostgreSQL + SQLAlchemy (async) + Alembic
- Redis (FSM + rate-limit авторизации)
- reportlab (PDF), qrcode

## Быстрый старт (Docker)

1) Создайте `.env` на основе `.env.example`.
2) Запустите инфраструктуру:

```bash
docker compose up -d --build
```

3) Примените миграции:

```bash
docker compose exec bot alembic upgrade head
```

4) Откройте бота и выполните `/start`.

## Настройка супергруппы с темами

1) Создайте супергруппу с включенными темами (Forum).
2) Узнайте `SUPERGROUP_ID` и задайте в `.env`.
3) Для каждого города создайте тему и сохраните `thread_id`:

- Добавить город: `/add_city Москва`
- Привязать тему: `/set_topic Москва 123`

## Управление пользователями (ADMIN)

- Создать менеджера: `/add_manager ФИО`
- Создать клинера: `/add_cleaner ФИО`
- Деактивировать: `/del_manager` / `/del_cleaner`
- Разрешенные города клинера: `/set_cleaner_cities 42 Москва,Казань`

Пользователь заходит в бота и вводит выданный пароль — роль закрепляется за его `telegram_id`.

## Основные сценарии

- Менеджер: создаёт заявку через диалог → бот публикует в тему города → клинер берет заказ.
- Клинер: принимает заказ → загружает минимум 2 фото ДО и 2 фото ПОСЛЕ → завершает заказ.
- Менеджер: может выгрузить PDF счет: `/invoice 123`.

## Структура

См. `project/`:

- `project/bot/*` — handlers / FSM / keyboards / middlewares
- `project/services/*` — бизнес-логика (auth / order / storage / pdf)
- `project/database/*` — модели + миграции

## Документация

- `INSTALL.md`
- `DEPLOY.md`
- `ADMIN_GUIDE.md`
- `MANAGER_GUIDE.md`
- `CLEANER_GUIDE.md`
