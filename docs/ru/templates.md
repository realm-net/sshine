# Шаблоны инициализации

Шаблоны — это YAML-сценарии для автоматической настройки серверов.  
Концепция похожа на GitHub Actions: список именованных шагов с типизированными действиями.

## Управление шаблонами

```bash
# Зарегистрировать шаблон из файла
sshine template create <имя> -i <файл.inittmp>
sshine template create lamp -i templates/lamp.inittmp -g web

# Список всех шаблонов
sshine template list

# Просмотр тела шаблона (с подсветкой синтаксиса)
sshine template show lamp

# Запустить шаблон на сервере
sshine template run lamp --server web01
sshine template run lamp --server web01 --var php_version=8.2 --var deploy_user=www
sshine template run lamp --server web01 --dry-run   # показать шаги без выполнения

# Удалить шаблон
sshine template delete lamp
```

---

## Формат файла `.inittmp`

```yaml
name: my-template          # Название (можно переопределить через CLI)
description: "Описание"    # Опционально

vars:                      # Переменные с дефолтными значениями
  deploy_user: deployer
  php_version: "8.3"

steps:
  - name: Название шага    # Отображается в прогрессе
    action: <действие>     # Тип действия
    if: "{{ condition }}"  # Условие выполнения (опционально)
    # ... параметры действия
```

---

## Переменные

Объявляются в блоке `vars`, используются в любом строковом поле через `{{ имя }}`.

```yaml
vars:
  deploy_user: deployer
  domain: example.com

steps:
  - name: Create user
    action: user.create
    username: "{{ deploy_user }}"

  - name: Clone repo
    action: shell
    run: "git clone https://{{ domain }}/repo /var/www/app"
```

### Встроенные переменные

Всегда доступны без объявления:

| Переменная | Значение |
|---|---|
| `{{ server_name }}` | Имя сервера (как в sshine) |
| `{{ server_host }}` | Хост |
| `{{ server_user }}` | SSH-пользователь |
| `{{ server_port }}` | SSH-порт |

### Переопределение через CLI

```bash
sshine template run lamp --server prod \
  --var deploy_user=www-data \
  --var php_version=8.2
```

---

## Jinja2

Для условий, циклов и фильтров используется [Jinja2](https://jinja.palletsprojects.com/).

Jinja2 — **опциональная зависимость**. Простые `{{ переменная }}` работают без неё.  
Если шаблон содержит `{% %}` блоки, а Jinja2 не установлен, sshine выведет:

```
This template uses Jinja2 syntax ({% %} blocks).
Install it:  uv add jinja2
```

**Установка:**
```bash
uv add jinja2
```

---

### Условия: `{% if %}`

#### Поле `if:` — пропустить шаг целиком

```yaml
vars:
  env: production
  install_docker: "true"

steps:
  - name: Install Docker
    action: docker.install
    if: "{{ install_docker == 'true' }}"

  - name: Harden firewall
    action: shell
    run: ufw enable && ufw allow ssh
    sudo: true
    if: "{{ env == 'production' }}"

  - name: Dev tools
    action: package.install
    packages: [vim, htop, tmux]
    if: "{{ env != 'production' }}"
```

Значения, дающие **false**: `false`, `"false"`, `"0"`, пустая строка. Всё остальное — **true**.

#### Встроенный `{% if %}` внутри `run:`

```yaml
steps:
  - name: Conditional setup
    action: shell
    sudo: true
    run: |
      {% if server_user == 'root' %}
      echo "Root access — full setup"
      {% else %}
      echo "Non-root: {{ server_user }}, using sudo"
      {% endif %}
```

---

### Циклы: `{% for %}`

```yaml
vars:
  services: "nginx,php8.3-fpm,mysql"

steps:
  - name: Restart services
    action: shell
    sudo: true
    run: |
      {% for svc in services.split(',') %}
      systemctl restart {{ svc }}
      {% endfor %}
```

---

### Фильтры

```yaml
vars:
  app_name: my-application
  branch: feature/new-ui

steps:
  - name: Create directory
    action: shell
    # my-application → my_application
    run: "mkdir -p /var/www/{{ app_name | replace('-', '_') }}"

  - name: Deploy info
    action: shell
    run: |
      echo "App: {{ app_name | upper }}"
      echo "Branch: {{ branch | replace('/', '-') }}"
```

Полезные фильтры:

| Фильтр | Пример | Результат |
|---|---|---|
| `upper` | `{{ name \| upper }}` | `MY-APP` |
| `lower` | `{{ name \| lower }}` | `my-app` |
| `replace(a, b)` | `{{ s \| replace('-', '_') }}` | `my_app` |
| `default(val)` | `{{ x \| default('none') }}` | `none` если `x` пусто |
| `trim` | `{{ s \| trim }}` | без пробелов по краям |
| `int` | `{{ n \| int * 2 }}` | числовое выражение |
| `length` | `{{ list \| length }}` | количество элементов |

---

### Выражения в `{{ }}`

```yaml
vars:
  php_version: "8.3"
  workers: "4"

steps:
  - name: Configure PHP-FPM
    action: shell
    sudo: true
    run: |
      echo "pm.max_children = {{ workers | int * 2 }}" \
        >> /etc/php/{{ php_version }}/fpm/pool.d/www.conf
      echo "PHP major: {{ php_version.split('.')[0] }}"
```

---

## Встроенные действия

### `shell` — выполнить команду

```yaml
- name: Update system
  action: shell
  run: apt-get update -qq
  sudo: true
```

Поддерживает многострочные команды (`|`):

```yaml
- name: Configure
  action: shell
  sudo: true
  run: |
    systemctl enable nginx
    systemctl start nginx
    nginx -t
```

---

### `user.create` — создать пользователя

```yaml
- name: Create deploy user
  action: user.create
  username: "{{ deploy_user }}"
  shell: /bin/bash
  sudo: true
```

Идемпотентно — не падает, если пользователь уже есть.

---

### `ssh.keygen` — сгенерировать ключ и авторизовать его

```yaml
- name: Generate deploy key
  action: ssh.keygen
  method: ed25519
  name: "deploy-{{ server_name }}"
  user: "{{ deploy_user }}"
```

Генерирует пару ключей локально → сохраняет в `~/.sshine/keys/` → загружает публичный ключ в `~<user>/.ssh/authorized_keys` на сервере.

---

### `ssh.authorize` — добавить существующий ключ

```yaml
- name: Authorize CI key
  action: ssh.authorize
  key: ci-deploy       # имя из ~/.sshine/keys/ или путь к .pub
  user: deployer
```

---

### `package.install` — установить пакеты

```yaml
- name: Install packages
  action: package.install
  packages:
    - nginx
    - "php{{ php_version }}-fpm"
    - redis-server
  manager: apt         # apt | yum | dnf | brew (auto-detect если не задан)
```

---

### `docker.install` — установить Docker

```yaml
- name: Install Docker
  action: docker.install
  compose: true        # также установить docker-compose-plugin
```

---

## Полный пример

```yaml
name: lamp-production
description: LAMP-стек для production

vars:
  deploy_user: www-data
  php_version: "8.3"
  domain: example.com

steps:
  - name: Update & upgrade
    action: shell
    run: apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
    sudo: true

  - name: Create deploy user
    action: user.create
    username: "{{ deploy_user }}"
    shell: /bin/bash
    sudo: true
    if: "{{ deploy_user != 'root' }}"

  - name: Generate deploy key
    action: ssh.keygen
    method: ed25519
    name: "{{ server_name }}-deploy"
    user: "{{ deploy_user }}"
    if: "{{ deploy_user != 'root' }}"

  - name: Install LAMP
    action: package.install
    packages:
      - apache2
      - "php{{ php_version }}"
      - "php{{ php_version }}-fpm"
      - "php{{ php_version }}-mysql"
      - mysql-server

  - name: Enable Apache modules
    action: shell
    sudo: true
    run: |
      a2enmod rewrite proxy_fcgi
      a2enconf "php{{ php_version }}-fpm"
      systemctl reload apache2

  - name: Install Docker
    action: docker.install
    compose: true

  - name: Firewall
    action: shell
    sudo: true
    run: |
      ufw allow ssh
      ufw allow http
      ufw allow https
      {% if env is defined and env == 'production' %}
      ufw --force enable
      {% endif %}

  - name: Enable services
    action: shell
    sudo: true
    run: systemctl enable --now apache2 mysql

  - name: Done
    action: shell
    run: "echo '✓ {{ server_host }} ready (PHP {{ php_version }}, domain: {{ domain }})'"
```

```bash
sshine template create lamp -i lamp-production.inittmp
sshine add web01 -h 1.2.3.4 --keygen -g production -t lamp
# или позже:
sshine template run lamp --server web01 --var php_version=8.2
```

---

← [Назад к содержанию](./readme.md)
