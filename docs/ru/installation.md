# Установка

## Требования

- Python ≥ 3.14
- [uv](https://docs.astral.sh/uv/) — менеджер пакетов

## Установка

```bash
git clone https://github.com/your-org/sshine
cd sshine
uv sync
```

После синхронизации `sshine` доступен через `uv run sshine`.  
Чтобы вызывать просто `sshine`, добавь `.venv/Scripts` (Windows) или `.venv/bin` (Unix) в `PATH`.

## Инициализация

```bash
sshine init
```

sshine при первом запуске:

1. Проверяет наличие системного кейринга (Windows Credential Manager, macOS Keychain, Linux Secret Service).
2. Если кейринг недоступен — предлагает `sshine-keychain` (локальное зашифрованное хранилище).
3. Создаёт рабочую директорию `~/.sshine/`.
4. Инициализирует базу данных и конфиг.
5. Проверяет хранилище тестовой записью.
6. Предлагает добавить первый сервер.

## Структура рабочей директории

```
~/.sshine/
├── config.toml       # настройки (бэкенд хранилища, пути)
├── sshine.db         # серверы, группы, теги, шаблоны
├── keychain.db       # зашифрованные секреты (если выбран sshine-keychain)
├── keys/             # SSH-ключи, сгенерированные через --keygen
└── backups/          # файлы бэкапов (.ssb)
```

---

← [Назад к содержанию](./readme.md)
