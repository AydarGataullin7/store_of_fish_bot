# Fish Bot

Телеграм-бот для интернет-магазина рыбы на основе FSM. Работает с Strapi CMS по API.

## Что умеет

- Показывает товары с картинками
- Добавляет товары в корзину
- Показывает корзину с итоговой суммой
- Удаляет товары из корзины
- Запрашивает email и сохраняет клиента в Strapi

## Технологии

- Python 3.10+
- python-telegram-bot 13.15
- Redis — хранение состояний (FSM)
- requests — HTTP-запросы к Strapi API

## Установка

```bash
pip install -r requirements.txt
```
Создайте `.env` по образцу `.env.example`.

Запуск

```bash
python bot.py
```
## Переменные окружения

| Переменная | Описание | Пример |
|------------|----------|--------|
| `TELEGRAM_TOKEN` | Токен бота от @BotFather | `123456:ABC...` |
| `STRAPI_TOKEN` | API-токен из Strapi | `Bearer 12ab...` |
| `DATABASE_HOST` | Адрес Redis | `localhost` |
| `DATABASE_PORT` | Порт Redis | `6379` |
| `DATABASE_PASSWORD` | Пароль Redis (пусто, если нет) | |
