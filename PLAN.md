# Plan: Campana de notificaciones + Web Push (PWA) para managers

## Contexto

Los managers/super_managers usan el portal web (`/manager/`) desde escritorio y desde iPhone (Safari/Chrome). Hoy los únicos avisos son badges en el navbar (`pending_visits_count`, `pending_technicians_count`) que solo se ven al recargar la página. Se necesita que, cuando ocurra un evento que requiere su acción, les llegue una notificación nativa al teléfono o al navegador aunque no tengan el portal abierto.

**Alcance acordado con el usuario:**
- Campana en el navbar visible **solo para `super_manager` y superuser** (no managers regulares).
- La campana muestra **historial de notificaciones** (dropdown con leídas/no leídas, badge contador) + botón para **activar push** en ese dispositivo.
- Eventos que notifican (destinatarios: todos los super_managers activos + superusers, excluyendo al actor del evento):
  1. **Visita creada en `PENDIENTE_APROBACION`**.
  2. **Técnico pasa a `PENDING`** (registró su dispositivo desde la app móvil).
- Como los super_managers ven todas las empresas, **no se filtra por empresa** — el servicio se simplifica.
- **PWA completa**: en iOS (16.4+) las push web solo funcionan si el portal está instalado en pantalla de inicio → manifest + service worker + iconos + guía de instalación para iPhone.

**Infraestructura existente relevante:** sin Celery/Channels/PWA. Redis cache disponible. Whitenoise con manifest storage. CSP activo en prod. `SuperManagerRequiredMixin` en `core/mixins.py:34` (permite SUPER_MANAGER y superuser). Objeto JS global `Alert` en `templates/manager/base.html`.

## Decisiones de diseño

| Decisión | Elección |
|---|---|
| Disparo de eventos | **Inline en las vistas** (no signals) — solo 2 puntos, explícitos y trazables; la condición `is_super` vive en la vista |
| Endpoints campana | Bajo `/manager/notifications/` con **sesión Django + CSRF** (no JWT), `SuperManagerRequiredMixin` |
| Envío push | `pywebpush` síncrono dentro de `threading.Thread(daemon=True)` (sin Celery; volumen bajo). La creación de `Notification` en BD sí es síncrona |
| VAPID public key | Inyectada vía context processor (valor público estático) |
| Polling | Solo `unread_count` cada 60s; lista completa al abrir el dropdown |
| sw.js / manifest.json | Servidos **desde la raíz** vía `TemplateView` (templates Django, no static) — scope `/` sin headers extra, y sin hash de whitenoise que rompería las actualizaciones del SW |

## Implementación

### 1. Nueva app `notifications/`

- `python manage.py startapp notifications`, agregar `'notifications'` a `INSTALLED_APPS` en `core/settings.py`.
- **`notifications/models.py`**:
  - `Notification`: `user` FK (related_name `notifications`), `event` (TextChoices: `visit_pending`, `technician_pending`), `title` (120), `body` (255, blank), `url` (255, blank — path relativo), `is_read` (default False), `created_at`. `Meta`: ordering `-created_at`, índices `(user, is_read)` y `(user, -created_at)`.
  - `PushSubscription`: `user` FK (related_name `push_subscriptions`), `endpoint` `TextField(unique=True)` (los endpoints FCM/APNs superan 255 chars), `p256dh`, `auth`, `user_agent` (blank), `created_at`.
- `makemigrations notifications` + `migrate`. Registrar ambos en `notifications/admin.py`.

### 2. Dependencia y claves VAPID

- `requirements.txt`: `pywebpush>=2.0`.
- Generar claves VAPID una sola vez con script `py_vapid` y guardarlas en `.env` (NUNCA commitear ni regenerar — regenerarlas invalida todas las suscripciones):
- `core/settings.py`: `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_ADMIN_EMAIL` vía `config()`.
- Documentar las 3 variables en el setup de `.env` (Makefile `make setup` si aplica).

### 3. `notifications/services.py` — servicio central

```python
def notify_supervisors(*, event, title, body='', url='', exclude_user=None):
    # destinatarios: User.objects.filter(is_active=True).filter(
    #     Q(role=User.Role.SUPER_MANAGER) | Q(is_superuser=True)).distinct()
    # crea Notification con bulk_create
    # lanza threading.Thread(daemon=True) que envía push a sus PushSubscription
    # TODO envuelto en try/except — nunca rompe la request llamante
```

- `_send_one(sub, payload)`: `webpush(...)` con `vapid_claims={'sub': f'mailto:{...}'}` construido **nuevo en cada llamada** (pywebpush muta el dict).
- En `WebPushException` con status 404/410 → borrar la `PushSubscription` (suscripción muerta).
- Al final del thread: `django.db.connection.close()` (no fugar conexiones).
- Invalidar cache `unread_notif_<user_pk>` de los destinatarios al crear notificaciones.

### 4. Hooks en los 2 eventos

- **`visits/web_views.py:291`** (`VisitCreateWebView.post`, tras `Visit.objects.create`), solo si `not is_super`:
  - `notify_supervisors(event=VISIT_PENDING, title=f'Servicio #{visit.pk} pendiente de aprobación', body=f'{technician.get_full_name()} — {site.name} — {scheduled_date}', url=reverse('manager:visit_detail', args=[visit.pk]), exclude_user=request.user)`
- **`users/views.py:140`** (`ActivateView.post`, tras `target_user.save(update_fields=['status'])`):
  - `notify_supervisors(event=TECHNICIAN_PENDING, title='Técnico pendiente de aprobación', body=f'{target_user.get_full_name()} registró su dispositivo.', url=reverse('manager:pending_activations'))`
  - Este endpoint es API anónima (app móvil) — sin `exclude_user`.

### 5. Vistas web + URLs + context processor

- **`notifications/web_views.py`** — todas con `SuperManagerRequiredMixin`, respuestas `JsonResponse`:
  - `NotificationListView (GET)` → `{unread_count, items[últimas 20]}`
  - `NotificationUnreadCountView (GET)` → `{unread_count}` (polling)
  - `NotificationMarkReadView (POST <pk>)`, `NotificationMarkAllReadView (POST)` → `update(is_read=True)` filtrando `user=request.user` + `cache.delete`
  - `PushSubscribeView (POST)` → `update_or_create(endpoint=..., defaults={user, p256dh, auth, user_agent})`
  - `PushUnsubscribeView (POST)` → borra por endpoint+user
- **`core/manager_urls.py`**: 6 rutas bajo `notifications/` (names: `notifications_list`, `notifications_unread_count`, `notification_read`, `notifications_read_all`, `push_subscribe`, `push_unsubscribe`).
- **`notifications/context_processors.py`** → `unread_notifications_count` (cacheado 60s, mismo patrón que `pending_visits_count`) + `vapid_public_key`. Registrar en `TEMPLATES` de `settings.py`.

### 6. PWA: service worker, manifest, iconos

- **`core/urls.py`**: `path('sw.js', TemplateView...)` y `path('manifest.json', TemplateView...)` con content_type correctos.
- **`templates/sw.js`** (con `{% load static %}` para los iconos — whitenoise manifest):
  - `install` → `skipWaiting()`; `activate` → `clients.claim()`
  - `push` → `showNotification(title, {body, icon, badge, data:{url}})`
  - `notificationclick` → focus de ventana `/manager/` existente o `openWindow(url)`
  - Comentario de versión para forzar updates futuros.
- **`templates/manifest.json`**: name "SiteVisit", `start_url: /manager/`, `scope: /`, `display: standalone`, iconos 192/512 con `{% static %}`.
- **Iconos**: generar `static/img/icon-192.png`, `icon-512.png` y `apple-touch-icon.png` (180×180, fondo sólido — iOS no soporta transparencia ni SVG) desde `static/img/favicon.svg`.
- **`templates/manager/base.html` `<head>`**: `<link rel="manifest">`, `<link rel="apple-touch-icon">`, `<meta name="apple-mobile-web-app-capable">`, `mobile-web-app-capable`, `theme-color`.
- CSP: sin cambios (todo same-origin, `'self'` ya cubre).

### 7. UI campana en `templates/manager/base.html`

- Insertar entre theme toggle (línea ~130) y logout (línea ~134), **visible también en mobile** (los super_managers usan iPhone). Envuelta en `{% if request.user.is_superuser or request.user.role == 'super_manager' %}`.
- Dropdown DaisyUI `dropdown-end` con: botón campana estilo idéntico al theme toggle (btn-ghost 9×9 con borde) + `indicator` badge no leídas; cabecera con "Marcar leídas"; `<ul>` lista scrolleable (máx 80vh); pie con botón "Activar notificaciones en este dispositivo" + texto de estado.
- Modal `<dialog id="ios-install-modal">` con guía iOS: Compartir → Añadir a pantalla de inicio → abrir desde el icono.
- **`static/js/notifications.js`** (cargado con `defer`, config vía data-attrs):
  - Feature-detect ANTES de tocar APIs: en iOS no-standalone `Notification`/`PushManager` **no existen** → `typeof Notification === 'undefined'`.
  - `isIOS` + `isStandalone` (`display-mode: standalone` o `navigator.standalone`) → si iOS sin instalar, el botón abre el modal guía.
  - Click "Activar" (gesto de usuario obligatorio en iOS): `Notification.requestPermission()` → `registration.pushManager.subscribe({userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY)})` → POST subscribe con header `X-CSRFToken` → `Alert.success(...)`.
  - Si ya suscrito: estado "Notificaciones activas" + opción desactivar (unsubscribe local + POST unsubscribe).
  - Dropdown al abrir: fetch lista y render; click en item → POST read + navegar a `item.url`.
  - Polling `setInterval(60s)` → fetch unread-count → actualizar badge.
  - Registrar el SW al cargar (`navigator.serviceWorker.register('/sw.js')`) si está soportado.

## Orden de implementación

1. App + modelos + migración + admin (paso 1)
2. pywebpush + claves VAPID + settings (paso 2)
3. `services.py` (paso 3)
4. Vistas/URLs/context processor (paso 5)
5. Hooks en eventos (paso 4)
6. Iconos + sw.js + manifest + meta tags (paso 6)
7. UI campana + JS (paso 7)

## Verificación

**Local (Chrome desktop — localhost es secure context, push funciona sin HTTPS):**
1. `make dev` → login como super_manager. Campana visible solo para super_manager/superuser, ausente para manager regular y viewer; endpoints redirigen si no autorizado.
2. DevTools → Application: SW registrado scope `/`; Manifest sin errores.
3. "Activar notificaciones" → permiso → fila en `PushSubscription` (admin).
4. Crear visita como manager regular → llega push nativo y aparece en la campana del super_manager y del superuser; NO al creador. Click en la push → abre `/manager/visits/<pk>/`.
5. Evento técnico: `POST /api/v1/users/<pk>/activate/` (curl o shell) → push + notificación con link a `/manager/activations/`.
6. Marcar leída / todas → badge actualiza y persiste tras recarga.
7. Borrar suscripción desde DevTools y disparar evento → el 404/410 elimina la fila en BD.

**Producción (iPhone iOS 16.4+, HTTPS):**
1. Safari → `/manager/` → la campana muestra la guía de instalación (no standalone).
2. Añadir a pantalla de inicio → abrir desde icono → "Activar" pide permiso → suscribe.
3. Evento real → notificación llega con la app cerrada; tap abre la PWA en la URL destino.

## Riesgos clave

- **Claves VAPID inmutables**: regenerarlas invalida silenciosamente todas las suscripciones.
- **`vapid_claims` mutado por pywebpush** → dict literal nuevo por llamada.
- **Whitenoise manifest**: iconos referenciados con `{% static %}` en sw.js/manifest templados, nunca rutas hardcodeadas.
- **iOS**: feature-detect antes de usar `Notification`; `requestPermission` solo desde gesto de usuario; iOS puede revocar suscripciones de PWAs sin uso (el cleanup 404/410 lo cubre).
- **Threads + BD**: cerrar conexión al final del thread de envío.
