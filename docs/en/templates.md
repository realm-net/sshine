# Init Templates

Templates are YAML scripts for automating server setup.  
The concept mirrors GitHub Actions: a list of named steps with typed actions.

## Managing Templates

```bash
# Register a template from a file
sshine template create <name> -i <file.inittmp>
sshine template create lamp -i templates/lamp.inittmp -g web

# List all templates
sshine template list

# Inspect a template (syntax-highlighted YAML)
sshine template show lamp

# Run a template on a server
sshine template run lamp --server web01
sshine template run lamp --server web01 --var php_version=8.2 --var deploy_user=www
sshine template run lamp --server web01 --dry-run   # preview steps without executing

# Delete a template
sshine template delete lamp
```

---

## File Format (`.inittmp`)

```yaml
name: my-template          # Template name (overridable via CLI)
description: "..."         # Optional

vars:                      # Variables with default values
  deploy_user: deployer
  php_version: "8.3"

steps:
  - name: Step label       # Shown in progress output
    action: <action>       # Action type (see below)
    if: "{{ condition }}"  # Execution condition (optional)
    # ... action-specific parameters
```

---

## Variables

Variables are declared in the `vars` block and used in any string field via `{{ name }}`.

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

### Built-in Variables

Always available without declaration:

| Variable | Value |
|---|---|
| `{{ server_name }}` | Server name (as in sshine) |
| `{{ server_host }}` | Server hostname |
| `{{ server_user }}` | SSH user |
| `{{ server_port }}` | SSH port |

### Overriding via CLI

```bash
sshine template run lamp --server prod \
  --var deploy_user=www-data \
  --var php_version=8.2
```

---

## Jinja2

For conditionals, loops, and filters, sshine uses [Jinja2](https://jinja.palletsprojects.com/).

Jinja2 is an **optional dependency**. Simple `{{ variable }}` substitution works without it.  
If a template contains `{% %}` blocks and Jinja2 is not installed, sshine prints:

```
This template uses Jinja2 syntax ({% %} blocks).
Install it:  uv add jinja2
```

**Install:**
```bash
uv add jinja2
```

---

### Conditionals: `{% if %}`

#### Step-level `if:` — skip a step entirely

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

Values that evaluate to **false**: `false`, `"false"`, `"0"`, empty string. Everything else is **true**.

#### Inline `{% if %}` inside `run:`

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

### Loops: `{% for %}`

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

### Filters

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

Useful filters:

| Filter | Example | Result |
|---|---|---|
| `upper` | `{{ name \| upper }}` | `MY-APP` |
| `lower` | `{{ name \| lower }}` | `my-app` |
| `replace(a, b)` | `{{ s \| replace('-', '_') }}` | `my_app` |
| `default(val)` | `{{ x \| default('none') }}` | `none` if `x` is empty |
| `trim` | `{{ s \| trim }}` | strips surrounding whitespace |
| `int` | `{{ n \| int * 2 }}` | numeric expression |
| `length` | `{{ list \| length }}` | item count |

---

### Expressions in `{{ }}`

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

## Built-in Actions Reference

### `shell` — Run a shell command

```yaml
- name: Update system
  action: shell
  run: apt-get update -qq
  sudo: true          # run via sudo (default: false)
```

Supports multiline with `|`:

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

### `user.create` — Create a system user

```yaml
- name: Create deploy user
  action: user.create
  username: "{{ deploy_user }}"
  shell: /bin/bash
  sudo: true
```

Idempotent — skips if the user already exists.

---

### `ssh.keygen` — Generate an SSH key pair and authorise it

```yaml
- name: Generate deploy key
  action: ssh.keygen
  method: ed25519
  name: "deploy-{{ server_name }}"
  user: "{{ deploy_user }}"
```

Generates the key pair locally → saves to `~/.sshine/keys/` → uploads the public key to `~<user>/.ssh/authorized_keys` on the server.

---

### `ssh.authorize` — Authorise an existing key

```yaml
- name: Authorise CI key
  action: ssh.authorize
  key: ci-deploy      # name from ~/.sshine/keys/ or path to .pub file
  user: deployer
```

---

### `package.install` — Install packages

```yaml
- name: Install packages
  action: package.install
  packages:
    - nginx
    - "php{{ php_version }}-fpm"
    - redis-server
  manager: apt        # apt | yum | dnf | brew (auto-detected if omitted)
```

---

### `docker.install` — Install Docker

```yaml
- name: Install Docker
  action: docker.install
  compose: true       # also install docker-compose-plugin
```

---

## Full Example

```yaml
name: lamp-production
description: LAMP stack for a production server

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

  - name: Install LAMP stack
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

  - name: Configure firewall
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
# or later:
sshine template run lamp --server web01 --var php_version=8.2
```

---

← [Back to contents](./readme.md)
