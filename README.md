# SiteVisit — Backend

Django 5.2 + Django REST Framework. Gestión de visitas técnicas a sitios de telecomunicaciones.

## Stack

| Componente | Tecnología |
|---|---|
| Framework | Django 5.2 |
| API | Django REST Framework + SimpleJWT |
| Base de datos | PostgreSQL 17 |
| Cache / Sesiones | Redis 7 |
| CSS (portal web) | Tailwind CSS v4.2 + DaisyUI v5.5 |
| Archivos estáticos | Whitenoise + nginx |
| Seguridad | django-axes, django-csp, HSTS |
| Importación masiva | django-import-export v4 (CSV / XLSX) |
| Reverse proxy | Nginx + Let's Encrypt |

---

## Quick Start (desarrollo)

```bash
# 1. Instalar dependencias Python y Tailwind
make install

# 2. Generar .env (PostgreSQL, SECRET_KEY, etc.)
make setup

# 3. Levantar PostgreSQL + Redis en Docker
make dev-up

# 4. Crear superusuario
make superuser

# 5. Levantar servidor (migrate + tailwind watch + runserver)
make dev
```

- Admin Django: `http://localhost:8000/admin/`
- Portal manager: `http://localhost:8000/manager/`
- API: `http://localhost:8000/api/v1/`

---

## Apps

### `users/`
Modelo `User(AbstractUser)` con login por email, 4 roles y 2 empresas.

**Roles:**
| Rol | Capacidades |
|-----|------------|
| `technician` | Operar app Flutter (visitas, fotos, GPS) |
| `manager` | Aprobar/rechazar visitas y activaciones de **su empresa** |
| `super_manager` | Igual que manager pero sobre **todas las empresas** |
| `viewer` | Solo lectura: dashboard |

**Device binding:** Los técnicos vinculan un único dispositivo (fingerprint SHA256). El manager aprueba antes de permitir login con tokens JWT. Managers y viewers no requieren device binding.

**Importación masiva:** Admin Django → botón "Importar" → CSV/XLSX con columnas `nombre`, `rut`, `empresa`, `cargo`.

### `sites/`
Catálogo de sitios de telecomunicaciones (`Site`): código, nombre, dirección, coordenadas, empresa.

### `visits/`
Máquina de estados de la visita:

```
pendiente → aprobada → en_camino → llegada → trabajando → completada
```

Cada transición puede registrar un punto GPS (`VisitTrackingPoint`) y fotos (`VisitPhoto`).

### `dashboard/`
`GET /api/v1/dashboard/stats/` — métricas agregadas: total, por estado, por empresa (super_manager/viewer), top técnicos, duración media.

### `home/`
`SiteSetting` — paleta de colores por empresa almacenada en BD. Context processor que inyecta el tema en todos los templates.

---

## Flujo de activación de dispositivo

```
1. Técnico: POST /api/token/  →  401 device_not_registered (sin UserDevice)
2. Técnico: POST /api/v1/users/{id}/activate/  →  UserDevice(is_active=False) + 202
3. Manager: aprueba en portal web o POST /api/v1/users/{id}/approve/
4. Técnico: POST /api/token/  →  200 con tokens JWT
```

---

## Portal web manager

Vistas Django bajo `/manager/` (autenticación por sesión, no JWT):

| URL | Descripción |
|-----|-------------|
| `/manager/visits/` | Visitas filtradas por estado, botones Aprobar/Rechazar |
| `/manager/visits/{pk}/` | Detalle: fotos, GPS timeline, duración |
| `/manager/activations/` | Técnicos pendientes con info del dispositivo |

---

## Tema dinámico

`GET /api/v1/theme/?company=wom` devuelve la paleta activa:
1. Busca `SiteSetting` en BD
2. Fallback a `theme.json` en la raíz del monorepo (paleta PTI/Phoenix Tower)
3. WOM siempre tiene `primary = #E6007E` (magenta corporativo)

---

## Despliegue en VPS

```bash
# Primera vez
make setup
make nginx         # instala config nginx (NO repetir después de certbot)
sudo certbot --nginx -d tudominio.com
make deploy

# Deploys posteriores
make deploy        # git pull + rebuild automático
```

---

## Comandos disponibles

| Comando | Descripción |
|---|---|
| `make setup` | Wizard interactivo — genera `.env` |
| `make install` | Instala dependencias Python y Tailwind |
| `make dev-up` | Levanta PostgreSQL + Redis (Docker) |
| `make dev-down` | Detiene contenedores de desarrollo |
| `make dev-check` | Verifica estado del entorno |
| `make dev` | migrate + tailwind start + runserver |
| `make migrate` | Aplica migraciones |
| `make migrations` | Genera migraciones (`makemigrations`) |
| `make superuser` | Crea superusuario |
| `make shell` | Django shell |
| `make collect` | collectstatic |
| `make db-shell` | Abre psql o indica sqlite3 |
| `make nginx` | Instala config nginx (**solo primera vez**) |
| `make deploy` | Despliega en VPS |

---

## Estructura

```
backend/
├── core/               ← settings, urls, ThemeView
├── home/               ← SiteSetting, context processor
├── users/              ← User, UserDevice, ProfilePhoto, JWT, importación
├── sites/              ← Site
├── visits/             ← Visit, VisitPhoto, VisitTrackingPoint
├── dashboard/          ← StatsView
├── templates/
│   └── manager/        ← portal web (base, visits, activations)
├── theme/              ← app Tailwind (static_src/ con npm)
├── static/             ← assets estáticos
├── manage.py
├── requirements.txt
├── Makefile
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Variables de entorno clave

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave secreta Django |
| `DEBUG` | `True` dev / `False` prod |
| `POSTGRES_DB` | Nombre de la base de datos (ausente → SQLite) |
| `POSTGRES_USER` | Usuario PostgreSQL |
| `POSTGRES_PASSWORD` | Contraseña PostgreSQL |
| `REDIS_URL` | URL de Redis (default: `redis://redis:6379/0`) |
| `CORS_ALLOWED_ORIGINS` | Orígenes CORS en producción (CSV) |
| `ALLOWED_HOSTS` | Dominios permitidos (CSV) |
