# sshine

> Open-source утилита для управления SSH-серверами.  
> Храни серверы, ключи и секреты в одном месте. Подключайся одной командой.

```
sshine add prod -h 1.2.3.4 --keygen -g production --tag web
sshine connect prod
```

---

## Содержание

| | |
|---|---|
| [Установка](./installation.md) | Требования, `uv sync`, первый запуск |
| [Хранилища](./storage.md) | `keyring` и `sshine-keychain`, миграция, архитектура |
| [Серверы](./servers.md) | `add`, `rm`, ключи, пароли, группы, теги |
| [Просмотр](./listing.md) | `list`, `tree`, фильтрация |
| [Шаблоны](./templates.md) | Формат `.inittmp`, действия, Jinja2 |
| [Бэкапы](./backups.md) | `backup`, `restore`, шифрование |
| [Справочник команд](./reference.md) | Все команды и флаги |

---

## Быстрый старт

```bash
# 1. Инициализация
sshine init

# 2. Добавить сервер
sshine add prod -h 1.2.3.4 --keygen m=ed25519 n=prod-key -g production

# 3. Подключиться
sshine connect prod

# 4. Посмотреть все серверы
sshine list
sshine tree
```

---

## Сообщество

Вопросы, идеи, обсуждение — в Telegram-канале:

**[t.me/sshine_talks](https://t.me/sshine_talks)**
