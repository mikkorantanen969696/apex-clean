# Установка (локально)

## Требования

- Python 3.11
- PostgreSQL 16+
- Redis 7+

## Установка

```bash
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
```

## Миграции

```bash
alembic upgrade head
```

## Запуск

```bash
python -m project.main
```

По умолчанию используется polling.
