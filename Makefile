# ── Configuración inicial ──────────────────────────────────────────────────────
setup:
	bash setup.sh

# ── Docker de desarrollo (Redis + PostgreSQL + n8n opcionales) ─────────────────
# Windows (PowerShell/cmd): recetas POSIX vía bash (Git for Windows). No usar UID=/GID=
# en la línea de comando: en bash UID es de solo lectura; el compose activo no lo necesita.
ifeq ($(OS),Windows_NT)
  # Progra~1 evita espacios en "Program Files"; si Git está en otro sitio, instálalo ahí o ajusta SHELL.
  GIT_BASH := $(wildcard C:/Progra~1/Git/bin/bash.exe)
  ifeq ($(GIT_BASH),)
    GIT_BASH := $(wildcard C:/Progra~2/Git/bin/bash.exe)
  endif
  ifneq ($(GIT_BASH),)
    SHELL := $(GIT_BASH)
    .SHELLFLAGS := -c
  endif
endif

# Mismos perfiles que dev-up (--profile postgres, n8n si aplica) para bajar postgres y redes.
compose-dev-profiles-cmd := set -a && ([ -f .env ] && . ./.env || true) && set +a; \
	PROFILES="--profile postgres"; \
	[ -n "$${N8N_DOMAIN}" ] && { PROFILES="$$PROFILES --profile n8n"; }; \
	[ "$${N8N_MCP_ENABLED}" = "true" ] && [ -n "$${N8N_DOMAIN}" ] && PROFILES="$$PROFILES --profile n8n-mcp"

dev-up:
	@[ -f .env ] || { echo "Error: .env no encontrado. Ejecuta 'make setup' primero."; exit 1; }
	@$(compose-dev-profiles-cmd); \
	[ -n "$${N8N_DOMAIN}" ] && mkdir -p volumes/n8n; \
	docker compose -f docker-compose.dev.yml $$PROFILES up -d

dev-down:
	@$(compose-dev-profiles-cmd); \
	docker compose -f docker-compose.dev.yml $$PROFILES down --remove-orphans

dev-logs:
	@$(compose-dev-profiles-cmd); \
	docker compose -f docker-compose.dev.yml $$PROFILES logs -f

dev-check:
	@echo "Verificando entorno de desarrollo..."
	@[ -f .env ] && echo "  ✓ .env existe" || echo "  ✗ .env no encontrado — ejecuta: make setup"
	@command -v python >/dev/null 2>&1 && echo "  ✓ Python disponible" || echo "  ✗ Python no encontrado"
	@command -v docker >/dev/null 2>&1 && echo "  ✓ Docker disponible" || echo "  ✗ Docker no encontrado"
	@docker compose -f docker-compose.dev.yml ps 2>/dev/null | grep -q "Up" \
		&& echo "  ✓ Contenedores activos" \
		|| echo "  ✗ Contenedores detenidos — ejecuta: make dev-up"
	@set -a && [ -f .env ] && . ./.env; set +a; \
	python -c "import os,redis; u=os.environ.get('REDIS_URL','redis://127.0.0.1:6379/0'); redis.from_url(u).ping()" 2>/dev/null \
		&& echo "  ✓ Redis accesible (REDIS_URL)" \
		|| { \
			python -c "import redis" 2>/dev/null \
				&& echo "  ✗ Redis no accesible — ¿REDIS_URL/puerto coincide con make dev-up?" \
				|| echo "  ✗ Redis no accesible — paquete 'redis' no instalado (ejecuta: make install)"; \
		}

# ── n8n (no utilizado por el momento) ─────────────────────────────────────────
# n8n-export:
# 	bash docker/n8n-export.sh
#
# n8n-update:
# 	@[ -f .env ] || { echo "Error: .env no encontrado."; exit 1; }
# 	@set -a && . ./.env && set +a; \
# 	[ -n "$${N8N_DOMAIN}" ] || { echo "Error: N8N_DOMAIN no definido en .env"; exit 1; }; \
# 	echo "▶ Descargando nueva imagen de n8n..."; \
# 	docker build -t $${PROJECT_NAME}_n8n:latest -f docker/n8n.Dockerfile .; \
# 	echo "▶ Reiniciando contenedor n8n..."; \
# 	docker compose --profile n8n up -d --no-deps n8n; \
# 	echo "✓ n8n actualizado."

# ── Django local ──────────────────────────────────────────────────────────────
install:
	pip install -r requirements-dev.txt
	python manage.py tailwind install
	@echo ""
	@[ -f .env ] || echo "  Siguiente paso: ejecuta 'make setup' para generar el .env"

# Tailwind en background + runserver con django-browser-reload.
# Python/templates: recarga automática. CSS: refrescar manualmente tras Tailwind recompilar.
dev:
	python manage.py migrate
	python manage.py tailwind start &
	python manage.py runserver 8010

tailwind:
	python manage.py tailwind start

# ── Comandos Django (dev: directo | prod: dentro del container) ───────────────
# $(shell ...) en Windows usa cmd; no ejecutar sintaxis POSIX ahí.
ifeq ($(OS),Windows_NT)
MANAGE := python manage.py
else
MANAGE := $(shell [ -f .env ] && . ./.env && [ "$${DEBUG}" = "False" ] && echo "docker compose exec django python manage.py" || echo "python manage.py")
endif

migrate:
	$(MANAGE) migrate

migrations:
	$(MANAGE) makemigrations

shell:
	$(MANAGE) shell

superuser:
	$(MANAGE) createsuperuser

test-users:
	$(MANAGE) create_test_users

seed:
	$(MANAGE) seed_demo_data

seed-reset:
	$(MANAGE) seed_demo_data --reset

flush-demo:
	bash flush_demo.sh

demo-reset:
	$(MANAGE) reset_demo_world

demo-reset-force:
	$(MANAGE) reset_demo_world --yes

collect:
	$(MANAGE) collectstatic --noinput

# ── Base de datos (dev) ────────────────────────────────────────────────────────
db-shell:
	@[ -f .env ] && . ./.env; \
	if [ -n "$${POSTGRES_DB}" ]; then \
		docker compose -f docker-compose.dev.yml exec postgres psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}; \
	else \
		echo "Modo SQLite — usa: sqlite3 db.sqlite3"; \
	fi

db-reset:
	@[ -f db.sqlite3 ] && rm db.sqlite3 && echo "SQLite eliminado." || true
	python manage.py migrate

# ── Producción ────────────────────────────────────────────────────────────────
deploy:
	bash deploy.sh

nginx:
	bash nginx-deploy.sh

check-ports:
	bash check-ports.sh

logs:
	docker compose logs -f django

down:
	docker compose down

.PHONY: setup dev-up dev-down dev-logs dev-check install dev tailwind \
        migrate migrations shell superuser test-users seed seed-reset flush-demo \
        collect db-shell db-reset deploy nginx check-ports logs down
