# Серверы

## Добавить сервер

```bash
sshine add <имя> -h <хост> [опции]
```

| Опция | Описание |
|---|---|
| `-h`, `--host` | Хост или IP-адрес *(обязательно)* |
| `-P`, `--port` | SSH-порт (по умолчанию: `22`) |
| `-u`, `--user` | Пользователь (по умолчанию: `root`) |
| `-p`, `--password` | Запросить пароль интерактивно |
| `--key <имя/путь>` | Использовать существующий ключ |
| `--keygen [m=метод] [n=имя]` | Сгенерировать новый ключ |
| `-g`, `--group` | Группа (создаётся автоматически) |
| `--tag <тег>` | Тег (можно указывать несколько раз) |
| `-t`, `--template` | Шаблон инициализации (запустится после добавления) |

### Примеры

```bash
# С паролем
sshine add vps1 -h 1.2.3.4 -p

# С генерацией ed25519-ключа
sshine add prod -h prod.example.com --keygen m=ed25519 n=prod-key

# С существующим ключом
sshine add staging -h 10.0.0.5 --key ~/.ssh/id_rsa

# С группой, тегами и шаблоном
sshine add web01 -h 192.168.1.10 --keygen -g production --tag web --tag nginx -t lamp

# RSA, другой пользователь
sshine add legacy -h old.server.ru --keygen m=rsa n=legacy-rsa -u deploy
```

## Опция `--keygen`

Генерирует пару ключей и сохраняет в `~/.sshine/keys/`.

```
--keygen                       → ed25519, имя = имя сервера
--keygen m=rsa                 → rsa
--keygen n=mykey               → файлы: mykey / mykey.pub
--keygen m=ecdsa n=ec-key      → ecdsa, файлы: ec-key / ec-key.pub
```

Поддерживаемые методы: `ed25519` (по умолчанию), `rsa`, `ecdsa`.

## Удалить сервер

```bash
sshine rm <имя>
sshine rm <имя> -y    # без подтверждения
```

Вместе с сервером автоматически удаляется связанный секрет из хранилища.

---

← [Назад к содержанию](./readme.md)
