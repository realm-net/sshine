# Просмотр серверов

## Список (таблица)

```bash
sshine list                    # все серверы
sshine list -g production      # фильтр по группе
sshine list -t web             # фильтр по тегу
sshine list -w                 # расширенный режим: ключ, тип авторизации
```

Пример вывода:

```
 Name    Host             Port  User   Group       Tags
─────────────────────────────────────────────────────────
 web01   192.168.1.10     22    root   production  web, nginx
 db01    192.168.1.20     22    root   production  db
 vps1    1.2.3.4          22    user   —           —
```

## Дерево (tree)

```bash
sshine tree                    # все серверы, сгруппированные
sshine tree -g production      # только группа production
sshine tree -t docker          # только серверы с тегом docker
```

Пример вывода:

```
sshine
├── 󰉋 production
│   ├── web01  root@192.168.1.10:22  🗝 key  #web #nginx
│   └── db01   root@192.168.1.20:22  🔑 pw   #db
└── (ungrouped)
    └── vps1   user@1.2.3.4:22  🗝 key
```

Иконки авторизации: `🗝 key` — SSH-ключ, `🔑 pw` — пароль.

---

← [Назад к содержанию](./readme.md)
