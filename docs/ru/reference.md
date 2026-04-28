# Справочник команд

## Основные

```
sshine init                          Инициализация

sshine add <name>                    Добавить сервер
  -h, --host <host>                    Хост или IP (обязательно)
  -P, --port <port>                    Порт (по умолчанию: 22)
  -u, --user <user>                    Пользователь (по умолчанию: root)
  -p, --password                       Запросить пароль
  --key <name|path>                    Использовать существующий ключ
  --keygen [m=method] [n=name]         Сгенерировать ключ
  -g, --group <group>                  Группа
  --tag <tag>                          Тег (повторяемый)
  -t, --template <name>                Шаблон инициализации

sshine rm <name>                     Удалить сервер
  -y, --yes                            Без подтверждения

sshine connect <name>                Подключиться к серверу
```

## Просмотр

```
sshine list                          Таблица серверов
  -g, --group <group>                  Фильтр по группе
  -t, --tag <tag>                      Фильтр по тегу
  -w, --wide                           Расширенный режим

sshine tree                          Дерево серверов
  -g, --group <group>                  Фильтр по группе
  -t, --tag <tag>                      Фильтр по тегу
```

## Хранилища

```
sshine storage                       Инфо о текущем бэкенде
sshine storage <name>                Инфо о конкретном бэкенде

sshine storage use <backend>         Переключить бэкенд
                                       keyring | sshine-keychain

sshine storage migrate <src> <dst>   Перенести секреты
  --dry-run                            Без изменений (проверка)

sshine storage purge <name>          Удалить все секреты из бэкенда
  -y, --yes                            Без подтверждения
```

## Бэкапы

```
sshine backup                        Создать бэкап
  -o, --output <path>                  Путь к файлу (по умолчанию: ~/.sshine/backups/)
  -p, --passphrase <pass>              Пароль шифрования

sshine restore                       Восстановить из бэкапа
  -i, --input <path>                   Файл (или 'latest')
  -p, --passphrase <pass>              Пароль
  --no-delete                          Не удалять файл после восстановления
  --merge                              Не перезаписывать существующие серверы
```

## Шаблоны

```
sshine template create <name>        Зарегистрировать шаблон
  -i, --input <file>                   Файл .inittmp (обязательно)
  -g, --group <group>                  Группа

sshine template list                 Список шаблонов

sshine template show <name>          Показать тело шаблона

sshine template run <name>           Запустить шаблон
  --server <name>                      Сервер (обязательно)
  --var <key=value>                    Переопределить переменную (повторяемый)
  --dry-run                            Показать шаги без выполнения

sshine template delete <name>        Удалить шаблон
  -y, --yes                            Без подтверждения
```

---

← [Назад к содержанию](./readme.md)
