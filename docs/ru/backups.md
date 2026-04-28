# Бэкапы

## Создать бэкап

```bash
sshine backup                           # → ~/.sshine/backups/sshine-<дата>.ssb
sshine backup -o /path/to/backup.ssb   # указать путь
sshine backup -p "my passphrase"       # задать пароль заранее (иначе — запрос)
```

Бэкап содержит: все серверы, группы, теги, шаблоны и **все секреты** (пароли, passphrase ключей).

### Шифрование

Файл бэкапа (`.ssb`) шифруется AES-256-GCM. Ключ выводится из passphrase через scrypt — **не** привязан к железу. Бэкап можно восстановить на любом устройстве.

> Passphrase обязателен: без него все секреты окажутся доступны любому, кто получит файл.

### Проверка целостности

После создания sshine выводит SHA-256 fingerprint файла. Сохрани его для верификации.

---

## Восстановить из бэкапа

```bash
sshine restore                             # из последнего бэкапа в ~/.sshine/backups/
sshine restore -i /path/to/backup.ssb     # из конкретного файла
sshine restore -i backup.ssb -p "pass"    # задать пароль сразу
sshine restore --no-delete                # не удалять файл после восстановления
sshine restore --merge                    # не перезаписывать существующие серверы
```

После успешного восстановления sshine предложит удалить файл бэкапа.  
`--no-delete` отменяет удаление без запроса.

---

## Перенос на новую машину

```bash
# На старой машине
sshine backup -o transfer.ssb

# Скопировать файл на новую машину (scp, флешка, и т.д.)

# На новой машине
sshine init
sshine restore -i transfer.ssb
```

---

← [Назад к содержанию](./readme.md)
