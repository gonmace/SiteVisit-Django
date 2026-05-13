# PLAN — Mapas Leaflet en Dashboard y Detalle de Visita

## Context

El dashboard del portal manager (`templates/manager/dashboard.html`) y el detalle de visita (`templates/manager/visit_detail.html`) no muestran información geográfica visual. Hoy las coordenadas de sitios y los tracking points de técnicos solo aparecen como texto plano que linkea a Google Maps en una pestaña aparte.

**Objetivo**:

1. **Dashboard** — agregar un mapa con todos los sitios filtrable por: empresa (WOM/PTI), estado de visita, rango de fechas y técnico. Cada sitio que tenga ≥1 visita en el filtro aplicado muestra info al hacer click (visitas recientes, técnico, links al detalle).
2. **Detalle de visita** (`visit_detail.html`) — agregar un mapa **encima** del timeline GPS existente, mostrando el globo del sitio + la ruta del técnico (polyline + marcadores por cada tracking point). El timeline cronológico se conserva (complemento, no reemplazo).

En lenguaje del usuario: cada **"servicio" = una Visita**, cada **"evento" = un `VisitTrackingPoint`**. El mapa de detalle aparece cuando la visita tiene ≥1 tracking point.

---

## Decisiones técnicas

### Stack
- **Leaflet 1.9.x** vía jsDelivr (sigue el patrón del proyecto: 100% CDN, sin npm). Sin build step.
- **Plugin `leaflet.markercluster` 1.5.x** vía jsDelivr para agrupar sitios cuando hay muchos cerca.
- **Tiles**: OpenStreetMap por defecto (gratuito, sin API key). Constante JS para cambiar provider más adelante.
- **Iconos custom**: `L.divIcon` con FontAwesome (ya cargado en `manager/base.html`). El marcador del sitio usa `var(--color-secondary)` y `fa-tower-broadcast`; los iconos de tracking reusan el mapeo `event → icon` que ya existe en el timeline actual.
- **Tema reactivo**: leer CSS vars (`--color-primary`, `--color-secondary`, `--color-info`) con `getComputedStyle(document.documentElement)` + `MutationObserver` sobre `data-theme`. Mismo patrón que Chart.js en `dashboard.html:333-339`.

### Backend
- **Reusar** `DashboardWebView.get_context_data` para inyectar opciones de filtro (empresas, técnicos, estados) — evita un fetch redundante al cargar.
- **Nuevo endpoint API** `GET /api/v1/dashboard/map-data/` que devuelve sitios + visitas filtradas. Filtros como query params. Permisos: igual que `StatsView` (MANAGER, SUPER_MANAGER, VIEWER) + filtro automático por empresa para MANAGER.
- **Para el mapa de `visit_detail`** los datos ya vienen prefetched en `VisitDetailWebView` (`visit.tracking_points.all` y `visit.site.latitude/longitude`) — **no se necesita endpoint nuevo**; se renderizan inline como JSON via `json_script`.

### Filtros del endpoint `map-data`

| Param | Tipo | Comportamiento |
|---|---|---|
| `company` | `wom\|pti\|all` | Si MANAGER, ignorado y forzado a `user.company`. |
| `status` | csv de status (`programada,en_camino,...`) | Si vacío, todos los estados. |
| `date_from` | `YYYY-MM-DD` | Filtra `scheduled_date >= date_from`. |
| `date_to` | `YYYY-MM-DD` | Filtra `scheduled_date <= date_to`. |
| `technician` | id de usuario | Filtra `technician_id`. |

Defaults sin filtros: empresa = `all` (o la del MANAGER), status = todos, fechas = últimos 7 días, técnico = todos.

### Estructura del payload `map-data`

```json
{
  "sites": [
    {"id": 1, "code": "WOM-001", "name": "Cerro Las Bellotas",
     "lat": -33.45, "lng": -70.65, "company": "wom", "visit_count": 3}
  ],
  "visits": [
    {"id": 42, "status": "trabajando", "status_display": "Servicio",
     "scheduled_date": "2026-05-12", "site_id": 1, "site_code": "WOM-001",
     "technician_name": "Juan Pérez", "technician_id": 7, "tracking_count": 4}
  ]
}
```

No envía tracking points completos (pueden ser muchos). El usuario hace click en una visita del popup → se abre `/manager/visits/{id}/` con su propio mapa.

---

## Archivos a crear / modificar

### 1. `templates/manager/base.html` (MODIFICAR)
Agregar `{% block extra_head %}{% endblock %}` justo después del `{% tailwind_css %}` para permitir cargar CSS de Leaflet desde templates hijos. Este bloque no existe hoy y se necesita para Leaflet CSS.

### 2. `dashboard/views.py` (MODIFICAR)
- **Extraer helper** `_visits_for_user(user)` que aplica filtro por rol/empresa (hoy duplicado entre `StatsView` y `DashboardWebView`). Reusar en ambos sitios.
- **Nueva `MapDataView(APIView)`** con misma lógica de permisos que `StatsView`. Implementa filtros descritos arriba.
- Para conteos por sitio: `Site.objects.annotate(visit_count=Count('visits', filter=Q(visits__in=filtered_visits))).filter(visit_count__gt=0)` — esto garantiza que solo aparezcan sitios con visitas en el filtro (cumple "cada servicio que ya tenga por lo menos un evento" semánticamente: solo sitios activos).
- Empresa: filtra sitios por `Site.company` y visitas por `site__company`. MANAGER se fuerza server-side.

### 3. `dashboard/urls.py` (MODIFICAR)
Agregar `path('map-data/', MapDataView.as_view(), name='map_data')`.

### 4. `dashboard/web_views.py` (MODIFICAR)
En `DashboardWebView.get_context_data`, añadir al contexto:
- `available_companies`: `User.Company.choices` (solo si super_manager).
- `available_technicians`: queryset filtrado por empresa con `id, first_name, last_name, email`.
- `available_statuses`: `Visit.Status.choices`.
- `default_date_from`, `default_date_to`: últimos 7 días (`timezone.localdate()`).
- `is_super_manager`: bool.

### 5. `templates/manager/dashboard.html` (MODIFICAR)
Insertar nueva sección **antes** del bloque "Top Técnicos / Top Sitios" titulada **"Mapa de operaciones"**.

Layout:
- Barra de filtros: `flex flex-col md:flex-row gap-2 mb-3` con `select select-bordered select-sm` (empresa, estado, técnico) + 2 `<input type="date" class="input input-bordered input-sm">` + `<button class="btn btn-info btn-sm">Aplicar</button>` + `<button class="btn btn-ghost btn-sm">Limpiar</button>`.
- Contenedor mapa: `<div id="operations-map" class="h-[420px] md:h-[480px] rounded-2xl border border-base-200 overflow-hidden"></div>`.

En `{% block extra_head %}`:
- `<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css">`
- `<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet.markercluster@1.5.3/dist/MarkerCluster.css">`
- `<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css">`

En `{% block extra_scripts %}` (después de Chart.js init):
- `<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>`
- `<script src="https://cdn.jsdelivr.net/npm/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>`
- Script con función `loadMap()`:
  1. Lee filtros del DOM y construye querystring.
  2. `fetch('/api/v1/dashboard/map-data/?<querystring>', { credentials: 'same-origin' })` — usa sesión Django (no JWT) porque el portal manager se autentica por sesión.
  3. Limpia `MarkerClusterGroup`, agrega marcadores nuevos con `divIcon` (color según `company`).
  4. Popup con código de sitio, nombre, conteo de visitas y links a cada visita (`/manager/visits/{id}/`).
  5. `fitBounds` automático si hay marcadores; default a vista Chile (`[-33.45, -70.65]`, zoom 5).
- Listeners en filtros para re-fetch automático on `change`.

**Nota de permisos**: el endpoint `MapDataView` debe aceptar sesión Django además de JWT. Hoy `StatsView` solo usa JWT vía `IsAuthenticated`. Solución: agregar `SessionAuthentication` a `authentication_classes` del `MapDataView`. CSRF: el endpoint es GET, no requiere token CSRF.

### 6. `templates/manager/visit_detail.html` (MODIFICAR)
- En `{% block extra_head %}`: `<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.css">`.
- Justo **antes** de la sección "Tracking GPS" (línea ~210), envuelto en `{% if visit.tracking_points.all %}`:
  ```html
  <div id="visit-map" class="h-[320px] md:h-[400px] rounded-2xl border border-base-200 overflow-hidden mb-4"></div>
  ```
- En `{% block extra_scripts %}`:
  - `<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.4/dist/leaflet.js"></script>`
  - `{{ site_geo|json_script:"visit-site-data" }}`
  - `{{ tracking_points_json|json_script:"visit-tracking-data" }}`
  - Script que monta:
    - Marcador del sitio (`var(--color-secondary)`, `fa-tower-broadcast`).
    - `L.polyline(...)` con puntos en orden cronológico, color `var(--color-primary)`, `weight: 3, opacity: 0.7`.
    - Marcadores numerados (1..N) por cada tracking point con icono según evento (reusar el mapeo del timeline). Popup con timestamp formateado, evento, coordenadas.
    - `fitBounds([site, ...trackingPoints])` con `padding: [20, 20]`.

### 7. `visits/web_views.py` (MODIFICAR)
En `VisitDetailWebView.get_context_data` agregar:
- `site_geo = {'lat': visit.site.latitude, 'lng': visit.site.longitude, 'code': visit.site.code, 'name': visit.site.name}`.
- `tracking_points_json = [{'lat': p.latitude, 'lng': p.longitude, 'event': p.event, 'event_display': p.get_event_display(), 'timestamp': p.timestamp.isoformat()} for p in visit.tracking_points.all()]`.

---

## Patrones existentes a reusar (NO duplicar)

- **Filtro queryset por rol/empresa**: hoy duplicado entre `dashboard/web_views.py:_qs` y `dashboard/views.py:StatsView`. Extraer a helper único `_visits_for_user(user)` en `dashboard/views.py` y consumirlo desde ambos.
- **Theme reactive colors**: patrón de `dashboard.html:333-339` (Chart.js leyendo CSS vars). Replicar idéntico en los scripts del mapa.
- **`confirmAction()`** del base: ya disponible si se necesita confirmación (no se usa en este plan, pero queda como referencia para futuras acciones desde popup).
- **Live-search debounced**: existe en `templates/manager/visit_form.html:53-219` para autocomplete de sitios. **Por ahora con `<select>` estático basta** — si los técnicos pasan de 50, migrar a este patrón.
- **Color de empresa**: WOM = `var(--color-primary)`, PTI = `var(--color-info)`. Definir como constante JS arriba del script del mapa.
- **Acceso a tracking points en serializer**: ya existe `VisitDetailSerializer` con nested `tracking_points` — disponible si se quisiera centralizar lógica en API. Por ahora no se usa porque el contexto Django ya tiene los datos.

---

## Consideraciones de UX / detalles

- **Responsive**: filtros `flex-col` en mobile, `flex-row` en `md+`. Mapa `h-[320px]` en visit_detail mobile, `h-[420px]` en dashboard mobile.
- **Sin datos**: si endpoint devuelve 0 sitios/visitas, overlay `absolute inset-0 grid place-items-center bg-base-100/80` con mensaje "No hay datos para los filtros aplicados".
- **Loading state**: durante el fetch, agregar `opacity-50 pointer-events-none` al contenedor del mapa.
- **Permisos UI**: el selector de empresa solo aparece para `is_super_manager`. MANAGER queda filtrado server-side (defense in depth).
- **Sin migraciones**: no se crea ningún campo nuevo en `Visit` ni `Site`.
- **CSP**: `core/settings.py` ya permite jsDelivr (Toasty, FontAwesome, Chart.js). Leaflet sigue el mismo CDN, no se requiere ajuste. Tiles OSM (`tile.openstreetmap.org`) sí se cargan desde un origin distinto — **verificar `CSP_IMG_SRC`** durante implementación; agregar `tile.openstreetmap.org` y `*.tile.openstreetmap.org` si CSP las bloquea.
- **Errores conocidos a evitar**:
  - Leaflet exige `width/height` definidos en el contenedor antes de `L.map()`. Si se inicializa dentro de un tab oculto, llamar `map.invalidateSize()` al hacerse visible.
  - `MutationObserver` sobre `data-theme` debe re-pintar la polyline y los `divIcon` (cambiarles la clase CSS, no recrear el mapa).

---

## Verificación end-to-end

1. **Setup**: `make dev` (Redis + PostgreSQL + tailwind watch + runserver).
2. **Data de prueba** vía admin Django (`/admin/`):
   - 2-3 sitios con coords reales en Chile.
   - ≥3 visitas en distintos estados, ≥1 con tracking points (crear vía POST `/api/v1/visits/{id}/status/` como técnico, o manual en admin).
3. **Login como `super_manager`** en `/manager/login/` → verificar dashboard:
   - Mapa aparece debajo de los charts existentes.
   - Marcadores en posiciones correctas; cluster cuando hay sitios cercanos.
   - Filtro empresa WOM oculta PTI y viceversa.
   - Filtro estado `trabajando` solo muestra sitios con visitas activas.
   - Rango de fechas (probar `date_from = hoy-30, date_to = hoy`).
   - Filtro técnico restringe correctamente.
   - Click en marcador → popup con conteo + links a visitas.
4. **Login como `manager` (empresa WOM)**:
   - Selector de empresa **no** aparece.
   - Solo se ven sitios y visitas WOM (forzado server-side).
   - **Recordar**: hoy MANAGER se redirige a `visits_approval` (`dashboard/web_views.py:17-21`). Verificar si la decisión es seguir redirigiendo o permitir MANAGER en el dashboard — si se quiere lo segundo, ese `dispatch` debe ajustarse. **Confirmar con el usuario durante implementación.**
5. **Detalle de visita** (`/manager/visits/{id}/`):
   - Visita con tracking: mapa aparece encima del timeline; polyline correcta, marcadores numerados, popups con timestamp/coords.
   - Visita sin tracking: mapa NO se renderiza; el timeline existente ya maneja este caso.
6. **API directa**:
   - `GET /api/v1/dashboard/map-data/?company=wom&status=programada,trabajando` con sesión Django → JSON válido.
   - Sin sesión → 401/403.
   - JWT de TECHNICIAN → 403.
7. **Tema oscuro**: alternar toggle del navbar → marcadores y polyline cambian de color en vivo.
8. **Performance**: con 100+ sitios, `markercluster` agrupa correctamente y render <1s.

---

## Archivos críticos (paths absolutos)

**Modificar**:
- `C:\Users\gonma\Documents\Claude\wom\backend\templates\manager\base.html`
- `C:\Users\gonma\Documents\Claude\wom\backend\templates\manager\dashboard.html`
- `C:\Users\gonma\Documents\Claude\wom\backend\templates\manager\visit_detail.html`
- `C:\Users\gonma\Documents\Claude\wom\backend\dashboard\views.py`
- `C:\Users\gonma\Documents\Claude\wom\backend\dashboard\urls.py`
- `C:\Users\gonma\Documents\Claude\wom\backend\dashboard\web_views.py`
- `C:\Users\gonma\Documents\Claude\wom\backend\visits\web_views.py`

**Solo lectura** (entender patrón existente):
- `C:\Users\gonma\Documents\Claude\wom\backend\sites\models.py`
- `C:\Users\gonma\Documents\Claude\wom\backend\sites\serializers.py`
- `C:\Users\gonma\Documents\Claude\wom\backend\visits\models.py`
- `C:\Users\gonma\Documents\Claude\wom\backend\visits\serializers.py`

**Sin migraciones**: no hay cambios de schema.
