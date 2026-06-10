# CLAUDE.md — Backend SiteVisit

>

## Comandos clave

```bash
# Setup y dev
make setup          # genera .env interactivo (primera vez)
make install        # pip install requirements-dev + tailwind install
make dev-up         # levanta Redis + PostgreSQL en Docker
make dev            # migrate + tailwind watch + runserver (hot reload completo)
make dev-check      # verifica estado del entorno

# Django
make migrate        # aplica migraciones
make migrations     # genera migraciones (makemigrations)
make superuser      # crea superusuario admin
make shell          # Django shell
make collect        # collectstatic

# Producción
make nginx          # configura nginx (SOLO la primera vez — certbot modifica este archivo)
make deploy         # git pull + verifica puertos + rebuild
```

On Windows: `NPM_BIN_PATH = r'C:\Program Files\nodejs\npm.cmd'` en `settings.py` dentro del bloque `if DEBUG:`.

---

## Apps y responsabilidades


| App          | Responsabilidad                                                                      |
| ------------ | ------------------------------------------------------------------------------------ |
| `core/`      | settings, urls, ThemeView (`GET /api/v1/theme/`), `_resolve_palette()`               |
| `home/`      | `SiteSetting` (paleta por empresa en BD), context processor para templates           |
| `users/`     | `User(AbstractUser)`, `UserDevice`, `ProfilePhoto`, JWT custom, importación CSV/XLSX |
| `sites/`     | `Site` (catálogo de sitios telecom)                                                  |
| `visits/`    | `Visit` (máquina de estados), `VisitPhoto`, `VisitTrackingPoint`, API + web views    |
| `dashboard/` | `StatsView` — métricas agregadas para Manager/Viewer                                 |
| `notifications/` | `Notification` (campana del navbar), `PushSubscription` (Web Push), `notify_supervisors()` |


Al agregar una app: `INSTALLED_APPS` + `@source "../../../<app>"` en `theme/static_src/src/styles.css`.

---

## Modelo User

`USERNAME_FIELD = 'email'`. El campo `username` = rut sin guion (requerido por AbstractUser).

Roles: `technician` | `manager` | `super_manager` | `viewer`

Device binding **solo para technician**. Managers/viewers hacen login sin fingerprint de dispositivo.

`rut` tiene `null=True, default=None` — permite múltiples usuarios sin RUT sin violar el unique constraint.

---

## Autenticación JWT

`CustomTokenObtainPairSerializer` en `users/serializers.py`:

- Si `role == technician`: verifica `device_fingerprint` del body
  - Sin `UserDevice` → 401 `device_not_registered`
  - `is_active=False` → 403 `pending_manager_approval`
  - Fingerprint distinto → 403 `device_unauthorized`
- Si otro rol: devuelve tokens directamente (sin device binding)

Claims extra en el token: `role`, `user_id`, `company`.

---

## Importación masiva de usuarios

`users/resources.py` — `UserResource` con `django-import-export` v4+.

**Firma correcta en v4:** `before_save_instance(self, instance, new, **kwargs)` donde `new` es bool.
No usar `row.get(...)` en `before_save_instance` — el parámetro `new` no es el row.
Las contraseñas pendientes se guardan en `self._pending_passwords` (dict keyed por username) en `before_import_row` y se leen en `before_save_instance`.

Formato del archivo CSV/XLSX: columnas `nombre`, `rut`, `empresa` (WOM o PTI), `cargo`.

---

## Stack UI — Portal web

**Toda interfaz del portal usa exclusivamente DaisyUI + Tailwind CSS.**

- Componentes: usar clases DaisyUI (`btn`, `card`, `table`, `modal`, `drawer`, `navbar`, `badge`, `input`, `select`, etc.)
- Utilidades de layout, spacing y tipografía: Tailwind (`flex`, `grid`, `p-*`, `m-*`, `text-*`, `bg-*`, etc.)
- **No escribir CSS custom** salvo para variables o casos que DaisyUI/Tailwind no cubran.
- **No usar Bootstrap, Bulma ni ningún otro framework CSS.**
- Los estilos globales y configuración del tema están en `theme/static_src/src/styles.css` (compilado con `django-tailwind`).
- Para agregar CSS a una nueva app: añadir `@source "../../../<app>"` en ese archivo.

---

## Portal web manager

Rutas en `core/manager_urls.py`, incluidas bajo `/manager/` con `app_name = 'manager'`.

Autenticación: sesión Django (no JWT) — managers ya autenticados en el admin.
`ManagerRequiredMixin`: requiere `role in (MANAGER, SUPER_MANAGER)`, filtra por empresa para MANAGER.

`VisitDetailWebView.get_context_data` calcula `visit_duration` como string "Xh YYm".
**No usar el filtro `timeuntil` de Django para duraciones entre fechas pasadas** — es para fechas futuras.

**Notificaciones (toasts):** El sistema de toasts está documentado en detalle en `TOAST_SYSTEM.md`. Resumen operativo:

- Los Django `messages` del servidor se convierten en toasts automáticamente al cargar la página (`base.html`).
- Para toasts desde JS: usar el objeto global `Alert` definido en `base.html` → `Alert.success(msg)`, `Alert.error(msg)`, `Alert.warning(msg)`, `Alert.info(msg)`.
- **No usar** `alert-*` de DaisyUI en línea ni `window.confirm()` / `window.alert()` nativos.

**Confirmaciones de acción (patrón toast):** Toda acción destructiva o irreversible debe confirmarse con un toast `alert-warning`, nunca con un `<dialog>` modal ni `window.confirm()`. Hay dos funciones globales en `base.html`:

| Función | Cuándo usarla |
|---------|--------------|
| `deleteItem(url, name, rowEl, label, note)` | Eliminar un registro — hace POST AJAX y elimina el elemento del DOM |
| `confirmStatusChange(btn, statusLabel, message, confirmClass)` | Cambiar el estado de un registro — muestra confirmación y hace submit del form |

**`confirmStatusChange` — uso:**
```html
<!-- El botón debe ser type="button" con name/value para que el handler los lea -->
<button type="button" name="status" value="active"
        onclick="confirmStatusChange(this,'Activo','El técnico podrá iniciar sesión.','btn-success')">
  Activo
</button>
```
El handler crea un `<input type="hidden" name="status">` con el valor y hace submit del `closest('form')`. La vista Django añade `messages.success/warning` para el toast de resultado.

**Confirmaciones de cambio de estado — colores del botón confirmar:**

| Estado    | `confirmClass` |
|-----------|---------------|
| Activo    | `btn-success`  |
| Pendiente | `btn-warning`  |
| Inactivo  | `btn-error`    |

**No usar** `alert-*` de DaisyUI para mensajes al usuario. Siempre usar `messages.success/error/warning/info` en las vistas y dejar que el base template los renderice como toasts.

**Estándar de colores de botones** (aplicar en TODOS los templates del portal):


| Acción                          | Clase DaisyUI   | Color        |
| ------------------------------- | --------------- | ------------ |
| Buscar                          | `btn-info`      | Azul         |
| + Agregar / Crear               | `btn-success`   | Verde        |
| Aprobar                         | `btn-success`   | Verde        |
| Guardar / Confirmar formulario  | `btn-success`   | Verde        |
| Importar Excel                  | `btn-secondary` | Gris         |
| Editar (fila de tabla)          | `btn-edit`      | Verde        |
| Ver / Detalle                   | `btn-view`      | Azul         |
| Eliminar / Rechazar (confirmar) | `btn-delete`    | Naranja      |
| Cancelar / Volver               | `btn-ghost`     | Sin color    |


Reglas:

- `btn-error` se reserva para indicadores de estado (badges, iconos), **no** para botones de acción.
- `text-*-content` no es necesario en botones — nuestros estilos usan el color completo como texto sobre fondo semitransparente.
- Los botones de filas de tabla usan `btn-xs`; los de cabecera de página usan `btn-sm h-9 min-h-0`.

---

## Formato numérico

**Estándar del proyecto: punto decimal (`.`), coma como separador de miles (`,`)**
Ejemplo: `1,234,567.89`

Configuración en `core/settings.py`:

- `USE_L10N = False` — desactiva el formato por locale (`LANGUAGE_CODE = 'es'` usaría `,` como decimal)
- `DECIMAL_SEPARATOR = '.'`
- `THOUSAND_SEPARATOR = ','`
- `NUMBER_GROUPING = 3`

**Reglas para templates:**


| Caso                          | Filtro                                                                | Ejemplo resultado |
| ----------------------------- | --------------------------------------------------------------------- | ----------------- |
| Decimal con N decimales       | `{{ value|floatformat:N }}`                                           | `3.141593`        |
| Entero con separador de miles | `{% load humanize %}{{ value|intcomma }}`                             | `1,234,567`       |
| Decimal con miles y decimales | `{{ value|floatformat:2|intcomma }}` — **no** usar; calcular en vista | —                 |
| Coordenadas (lat/lon)         | `{{ value|floatformat:6 }}`                                           | `-33.456789`      |
| Alturas (m)                   | `{{ value|intcomma }}` si >999                                        | `1,234`           |


**No usar** `localize` ni `unlocalize` en templates — `USE_L10N = False` ya establece el comportamiento correcto. No usar `{{ value }}` directo para números grandes; siempre pasar por `|intcomma`.

`django.contrib.humanize` está en `INSTALLED_APPS`. Para usar `intcomma` cargar en el template: `{% load humanize %}`.

---

## Arquitectura del settings.py

Un único `core/settings.py` — comportamiento por variables de entorno:

- Sin `POSTGRES_DB` → SQLite | con `POSTGRES_DB` → PostgreSQL
- `POSTGRES_MODE=host` → contenedores usan `host.docker.internal`
- `DEBUG=True` → axes DB handler, browser-reload, tailwind activo
- `DEBUG=False` → axes cache handler, HSTS, CSP estricto

**Docker Compose profiles:**


| Profile    | Servicio       | Condición                 |
| ---------- | -------------- | ------------------------- |
| `postgres` | PostgreSQL     | `POSTGRES_MODE=container` |
| `n8n`      | n8n            | `N8N_DOMAIN` definido     |
| —          | Redis + Django | Siempre activos           |


---

## Migraciones — orden de dependencias

```
users (0001) → sites (0001) → visits (0001)
```

`visits` usa `migrations.swappable_dependency(settings.AUTH_USER_MODEL)` para el FK al usuario custom.

---

## Tema dinámico

`GET /api/v1/theme/?company=<wom|pti>` → `_resolve_palette(company)`:

1. Busca `SiteSetting` en BD para la empresa
2. Fallback a `theme.json` en la raíz del monorepo
3. Override especial: WOM siempre tiene `primary = #E6007E` (magenta)

Context processor `home.context_processors.theme` inyecta la paleta en todos los templates Django como variables CSS.

---

## Endpoints API


| Endpoint                        | Método   | Rol              |
| ------------------------------- | -------- | ---------------- |
| `/api/token/`                   | POST     | Anon             |
| `/api/token/refresh/`           | POST     | Anon             |
| `/api/v1/users/register/`       | POST     | Manager          |
| `/api/v1/users/{id}/activate/`  | POST     | Auth             |
| `/api/v1/users/pending/`        | GET      | Manager          |
| `/api/v1/users/{id}/approve/`   | POST     | Manager          |
| `/api/v1/users/{id}/reject/`    | POST     | Manager          |
| `/api/v1/users/me/`             | GET      | Auth             |
| `/api/v1/sites/`                | GET      | Auth             |
| `/api/v1/visits/`               | GET/POST | Auth             |
| `/api/v1/visits/{id}/status/`   | POST     | Técnico          |
| `/api/v1/visits/{id}/tracking/` | POST     | Técnico          |
| `/api/v1/visits/{id}/photos/`   | POST     | Técnico          |
| `/api/v1/dashboard/stats/`      | GET      | Manager / Viewer |
| `/api/v1/theme/`                | GET      | Anon             |


---

## Notificaciones (campana + Web Push)

**Solo para `super_manager` y superuser** — los managers regulares NO ven la campana ni reciben push.

- App `notifications/`: modelos `Notification` (historial campana) y `PushSubscription` (un registro por navegador).
- Servicio central: `notifications.services.notify_supervisors(event, title, body, url, exclude_user)` — crea las `Notification` y envía Web Push en un `threading.Thread` daemon (sin Celery). **Nunca lanza excepción.**
- Eventos que notifican (hooks inline, no signals):
  - Visita creada `PENDIENTE_APROBACION` → `visits/web_views.py` (`VisitCreateWebView.post`)
  - Técnico pasa a `PENDING` → `users/views.py` (`ActivateView.post`)
- Endpoints campana bajo `/manager/notifications/` con sesión + `SuperManagerRequiredMixin` (list, unread-count, read, read-all, subscribe, unsubscribe).
- PWA: `/sw.js` y `/manifest.json` servidos desde la raíz vía `TemplateView` (templates `sw.js` y `manifest.json` — **no** mover a static: el hash de whitenoise rompería las actualizaciones del SW). Iconos en `static/img/icon-192.png`, `icon-512.png`, `apple-touch-icon.png`.
- **iOS**: las push solo llegan si el portal está instalado en pantalla de inicio (iOS 16.4+). El botón de la campana muestra la guía de instalación cuando detecta iOS sin standalone.
- Claves VAPID en `.env` (`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_ADMIN_EMAIL`). Generar con `python scripts/generate_vapid.py`. **NUNCA regenerarlas en producción** — invalida todas las suscripciones.
- Trampa pywebpush: `vapid_claims` debe ser un dict nuevo en cada llamada (la librería lo muta).
- JS de la campana: `static/js/notifications.js` (config vía data-attrs de `#notif-bell` en `base.html`). Polling de `unread-count` cada 60s.

---

## Seguridad

- `django-axes`: brute force en login (5 intentos, 1h cooldown, Redis handler en prod)
- Rate limiting DRF: login 5/min, activación 3/día, anon 100/h, auth 1000/h
- CORS: `CORS_ALLOW_ALL_ORIGINS = DEBUG` — en prod configurar `CORS_ALLOWED_ORIGINS`
- JWT rotate + blacklist (`rest_framework_simplejwt.token_blacklist`)
- CSP + HSTS activos en `DEBUG=False`

---

## Criterio de diseño — Portal web (estilo Cupertino/iOS)

Todas las páginas standalone del portal (login, futuras pantallas sin navbar) siguen la estética de iOS/macOS:

**Fondo y superficie**

- Fondo de página: `#F2F2F7` (iOS system background)
- Tarjetas/contenedores: `#ffffff` con `border-radius: 16px` y sombra sutil (`box-shadow: 0 1px 0 rgba(0,0,0,0.06), 0 4px 20px rgba(0,0,0,0.06)`)

**Tipografía**

- Font stack: `-apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", Arial, sans-serif`
- `-webkit-font-smoothing: antialiased` siempre activo
- Títulos: `font-weight: 700`, `letter-spacing: -0.5px`
- Subtítulos/labels: `color: #8e8e93` (iOS secondary label)
- Texto principal: `color: #1c1c1e` (iOS label)

**Inputs agrupados (estilo iOS grouped list)**

- Contenedor: `border-radius: 12px`, `border: 1px solid rgba(0,0,0,0.1)`, sin padding propio
- Cada fila: `height: 48px`, `padding: 0 14px`, `display: flex; align-items: center`
- Separador entre filas: `border-top: 1px solid rgba(0,0,0,0.08)`
- Label de campo: `min-width: 88px`, `font-weight: 500`, `font-size: 14px`
- Input: sin bordes, sin outline, `font-size: 15px`, `background: transparent`
- Placeholder: `color: #c7c7cc` (iOS placeholder)

**Botón primario**

- `height: 50px`, `border-radius: 12px`, `font-weight: 600`, `font-size: 16px`
- Color de fondo: `var(--color-secondary)` (color de empresa del tema)
- Feedback táctil: `opacity: 0.8` en `:active`, `transition: opacity 0.15s`

**Icono de app**

- `72×72px`, `border-radius: 18px` (relación estándar iOS icon corner)
- Fondo `var(--color-secondary)`, texto blanco, iniciales de la app

**Errores**

- Fondo `#fff2f0`, borde `rgba(234,88,12,0.25)`, `border-radius: 10px`, texto `#c0392b`

**Referencia**: `templates/manager/login.html`