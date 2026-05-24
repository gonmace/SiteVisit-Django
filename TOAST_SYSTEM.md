# Sistema de toasts y modales — Portal Manager

## Dónde vive el JS

Todo el código de toasts y modales está en **`templates/manager/base.html`**, dentro del bloque `<script>` al final del `<body>`.

| Línea | Qué define |
|-------|-----------|
| ~225  | Objeto `Alert` — container, `show()`, `hide()`, `success()`, `error()`, `warning()`, `info()` |
| ~326  | Loop que convierte `messages` de Django en toasts al cargar la página |
| ~418  | `function deleteItem(url, name, rowEl, label, note)` |
| ~460  | `function setupModalForm(url, form, modalId)` |
| ~478  | `function openModalEdit(url, modalId)` |

Las tres funciones se exponen en `window` para que cualquier template pueda llamarlas.

---

## Cómo funcionan los colores

### CSS (styles.css)

Los colores de DaisyUI v5 usan `@layer components`, que tiene baja especificidad. Para garantizar que se apliquen incluso frente al tema personalizado, se sobrescriben con `!important` en `theme/static_src/src/styles.css`:

```css
.alert-success {
  background-color: color-mix(in srgb, var(--color-success) 12%, var(--color-base-100)) !important;
  border-color:     var(--color-success) !important;
  color:            var(--color-success) !important;
}
.alert-error   { /* misma estructura con --color-error   */ }
.alert-warning { /* misma estructura con --color-warning */ }
.alert-info    { /* misma estructura con --color-info    */ }
```

Los valores de `--color-*` cambian automáticamente con el tema (light / dark) definido en el mismo archivo.

### JS — cómo `Alert` elige la clase

```javascript
Alert.success(msg)  // añade class="alert alert-success"
Alert.error(msg)    // añade class="alert alert-error"
Alert.warning(msg)  // añade class="alert alert-warning"
Alert.info(msg)     // añade class="alert alert-info"
```

El container es un `<div class="toast toast-top toast-end z-[9999]">` creado dinámicamente y anclado al `<body>`.

---

## Criterio de uso

### Toasts de resultado

| Situación | Función | Auto-hide |
|-----------|---------|-----------|
| Operación exitosa (guardar, eliminar) | `Alert.success(msg)` | 5 s |
| Error de red / servidor | `Alert.error(msg)` | manual |
| Advertencia o confirmación de eliminación | `Alert.warning(msg)` | manual (el usuario decide) |
| Mensaje informativo | `Alert.info(msg)` | manual |

Los Django `messages` del servidor también se muestran como toasts automáticamente al cargar la página, con `autoHide: 5000` para todos.

**Regla:** nunca usar `alert-*` de DaisyUI en línea ni `confirmAction()` para confirmaciones de eliminación. Toda la UX de feedback usa el sistema de toasts.

### Toast de confirmación de eliminación

`deleteItem(url, name, rowEl, label, note)` muestra un toast `alert-warning` con dos botones:

- **Cancelar** — descarta el toast
- **Eliminar** — hace POST AJAX, elimina el `rowEl` del DOM y muestra `Alert.success()`

```javascript
// Ejemplo de uso en un botón de tabla
deleteItem(
  this.dataset.url,          // URL del endpoint de delete
  this.dataset.name,         // Nombre del elemento (se muestra en el toast)
  this.closest('tr'),        // Elemento DOM a eliminar (tr, [data-row], etc.)
  'coordinador',             // Etiqueta del tipo de entidad
  'Los registros históricos se mantendrán. Esta acción no se puede deshacer.'
)
```

Para tarjetas móviles, el contenedor debe tener `data-row=""` y se usa `this.closest('[data-row]')`.

### Modales de edición AJAX

`openModalEdit(url, modalId)` carga un formulario parcial vía fetch y lo inyecta en el modal:

1. Abre el modal con spinner de carga
2. GET a `url` con header `X-Requested-With: XMLHttpRequest`
3. El servidor devuelve HTML parcial (sin `{% extends %}`)
4. Lee `form.dataset.title` para actualizar el título del modal
5. Llama `setupModalForm(url, form, modalId)` para manejar el submit

`setupModalForm(url, form, modalId)` intercepta el submit del formulario:

- POST con `FormData` y header AJAX
- Si `response.ok` (200) → cierra modal y recarga la página
- Si error (422 validación) → reemplaza el contenido del modal body con el HTML de errores y re-enlaza el submit

#### Convención de IDs del modal

Cada entidad necesita un `<dialog>` con esta estructura:

```html
<dialog id="{entity}-modal" class="modal">
  <div class="modal-box max-w-lg p-0 overflow-hidden">
    <div class="flex items-center justify-between px-6 pt-5 pb-4 border-b border-base-200">
      <h3 id="{entity}-modal-title" class="text-base font-bold text-base-content">Editar</h3>
      <button onclick="document.getElementById('{entity}-modal').close()" class="btn btn-ghost btn-xs btn-circle">✕</button>
    </div>
    <div id="{entity}-modal-body" class="p-6"></div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>
```

Las funciones `openModalEdit` y `setupModalForm` buscan `{modalId}-title` y `{modalId}-body` por convención.

#### Entidades implementadas

| Entidad | modal ID | Partial del form | URL de edición |
|---------|----------|-----------------|----------------|
| Sitio | `site-modal` | `manager/site_form_modal.html` | `manager:site_edit` |
| Coordinador | `coord-modal` | `manager/coordinator_form_modal.html` | `manager:coordinator_edit` |
| Técnico | `tech-modal` | `manager/technician_form_modal.html` | `manager:technician_edit` |

---

## Flujo completo: eliminación

```
Usuario hace clic en ✕
  → deleteItem() crea un toast alert-warning con [Cancelar] [Eliminar]
  → Si Cancelar: toast se descarta con animación
  → Si Eliminar:
      POST /manager/{entity}/{pk}/delete/ (header X-Requested-With: XMLHttpRequest)
      Server devuelve JSON: { "ok": true, "message": "Entidad X eliminada." }
      rowEl.remove()  ← quita la fila/card del DOM sin recargar
      Alert.success(message)  ← toast verde que desaparece en 5 s
```

## Flujo completo: edición

```
Usuario hace clic en ✏
  → openModalEdit(url, modalId) abre el dialog con spinner
  → GET url (header X-Requested-With)
  → Server devuelve HTML del form parcial
  → setupModalForm() enlaza el submit
  → Usuario edita y guarda:
      POST url con FormData
      Si ok → modal.close() + window.location.reload()
      Si 422 → body del modal se reemplaza con form+errores, re-enlace submit
```
