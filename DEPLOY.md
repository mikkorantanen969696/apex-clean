# Деплой на VPS (TimeWeb)

## Вариант 1: Docker Compose (рекомендуется)

1) Установите Docker и Docker Compose.
2) Скопируйте проект на сервер.
3) Создайте `.env` (см. `.env.example`).
4) Запустите:

```bash
docker compose up -d --build
docker compose exec bot alembic upgrade head
```

## Важно

- `storage/` монтируется как volume и содержит фото и PDF.
- Для webhook потребуется внешний HTTPS endpoint и reverse-proxy (Nginx/Caddy). В текущем MVP включен polling.
