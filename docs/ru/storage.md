# Хранилища

sshine использует два слоя хранения:

- **`sshine.db`** — обычная SQLite-база. Хранит метаданные серверов: хост, порт, юзер, группы, теги, ссылку на секрет. Не шифруется, легко переносится.
- **Бэкенд секретов** — пароли и passphrase ключей. Хранятся отдельно, `sshine.db` держит лишь ключ к значению (`auth_ref`).

## Бэкенды

| Бэкенд | Описание |
|---|---|
| `keyring` | Системный кейринг ОС. **По умолчанию.** |
| `sshine-keychain` | Собственное AES-256-GCM хранилище в `~/.sshine/keychain.db`, привязанное к железу (HWID). |

**Когда использовать `sshine-keychain`:** в Docker-контейнерах, headless-серверах или там, где системный кейринг недоступен.

> **Важно:** `keychain.db` привязан к железу и не переносится напрямую между машинами. Для переноса используй [`sshine backup/restore`](./backups.md).

## Команды

### Информация

```bash
# Текущий бэкенд
sshine storage

# Конкретный бэкенд
sshine storage keyring
sshine storage sshine-keychain
```

### Переключить бэкенд

```bash
sshine storage use sshine-keychain
sshine storage use keyring
```

При переключении sshine предложит мигрировать секреты из старого бэкенда.

### Миграция вручную

```bash
# Перенести все секреты
sshine storage migrate keyring sshine-keychain

# Посмотреть что будет перенесено, без изменений
sshine storage migrate keyring sshine-keychain --dry-run
```

> Бэкенд `keyring` не умеет перечислять свои записи — миграция работает через список `auth_ref` из `sshine.db`. Все секреты связанных серверов будут перенесены.

### Очистить бэкенд

```bash
sshine storage purge sshine-keychain
sshine storage purge keyring
```

Удаляет все секреты из указанного бэкенда. Запрашивает подтверждение.

---

← [Назад к содержанию](./readme.md)
