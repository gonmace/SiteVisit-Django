# PLAN — Auditoría + Commit + Push + Deploy

## Context

Se realizaron varias mejoras al portal web manager en esta sesión:

1. **Redirect post-creación de visita** → `/manager/visits/?tab=planificados&q=` (en lugar de ir al detalle)
2. **Tiempo transcurrido entre pasos del tracker** en `visit_detail.html` (cálculo en `VisitDetailWebView.get_context_data`)
3. **Tamaño de archivo de cada foto** en la galería (`photo.image.size|filesizeformat`)
4. **Selección múltiple en galería de fotos** con barra flotante para descargar (ZIP) y eliminar (solo `super_manager`)
5. **Estilo sólido en barra de selección**: fondo `bg-neutral` + botones `bg-success` / `bg-error` con `border-0`

El usuario pidió una **auditoría tipo revisión** para garantizar que ningún cambio rompa el frontend (app Android vía API REST + templates web), y luego ejecutar **commit → push → deploy SSH** al servidor de producción.

## Resultado de la auditoría (vía agente Explore)

Los cambios son **seguros para producción**:

- **API móvil (`/api/v1/`) intacta** — usa serializers, no contexto de templates. Cero impacto en la app Android.
- **Ningún otro template** depende de las variables de contexto modificadas (`tracking_steps`).
- **Clases Tailwind/DaisyUI nuevas** (`bg-neutral`, `text-neutral-content`, `bg-success`, `bg-error`, `text-accent`, `ring-accent`, `checkbox-accent`) son válidas en el build actual.
- **Orden de URLs en `core/manager_urls.py`** correcto: `visits/photos/bulk-download/` y `visits/photos/bulk-delete/` están declarados antes del catch-all incluido por `photos/`.
- **No existen tests** en el proyecto que puedan fallar por estos cambios.

### Riesgos conocidos (no bloqueantes)

- `photo.image.size` puede lanzar `FileNotFoundError` si el archivo en disco falta — solo afecta la galería, no rompe la API.
- `csrf_exempt` en las nuevas vistas bulk es innecesario (validan sesión + permisos); limpieza opcional a futuro.
- El ZIP se construye en memoria — OK para volúmenes normales; migrar a streaming real si crece.

---

## Archivos modificados (ya aplicados — no se vuelven a editar)

- `visits/web_views.py` — redirect en `VisitCreateWebView.post`, `tracking_steps` con `elapsed` en `VisitDetailWebView.get_context_data`, `VisitPhotoBulkDownloadView`, `VisitPhotoBulkDeleteView`
- `core/manager_urls.py` — rutas `visit_photo_bulk_download` y `visit_photo_bulk_delete`
- `templates/manager/visit_detail.html` — tracker desktop + móvil usando `tracking_steps` con `step.elapsed`
- `templates/manager/photos/gallery.html` — checkbox en cada card, barra flotante, scripts de selección/descarga/borrado, tamaño de archivo

---

## Plan de ejecución

### 1. Revisión pre-commit
- `git status` para listar archivos modificados/untracked
- `git diff` sobre los 4 archivos clave de esta tarea para verificar que no haya nada inesperado
- Identificar archivos basura a NO incluir (ej. `Sitios_base.xlsx`, `sitiosCF.xlsx`, `PLAN.md`, etc.)

### 2. Staging selectivo
Solo agregar los archivos directamente relacionados con esta entrega:

```
git add visits/web_views.py
git add core/manager_urls.py
git add templates/manager/visit_detail.html
git add templates/manager/photos/gallery.html
```

**No incluir** otros archivos modificados que aparezcan en el `git status` (pertenecen a trabajos previos no relacionados con esta entrega). Si hay duda, consultar al usuario antes de hacer el commit.

### 3. Commit
Mensaje propuesto (estilo del repo, español, con co-author):

```
feat: galeria con seleccion masiva, tiempo entre pasos y redirect post-creacion

- Galeria de fotos: checkbox por foto + barra flotante (descargar ZIP / eliminar)
- Galeria: muestra tamano de archivo de cada imagen
- Detalle de visita: tiempo transcurrido entre pasos del tracker
- Crear visita ahora redirige a /manager/visits/?tab=planificados&q=

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

### 4. Push a `origin/main`
```
git push origin main
```
- Sin `--force`, sin `--no-verify`

### 5. Deploy en producción
Conectar al servidor de producción y ejecutar el deploy:
```
ssh pti@45.90.123.172 -p 38
cd /home/pti/SiteVisit-Django
make deploy
```

`make deploy` (según CLAUDE.md) = `git pull` + verifica puertos + rebuild.

> **Nota**: el comando SSH es interactivo y puede requerir contraseña / fingerprint. Si la sesión actual no permite SSH no-interactivo, indicar al usuario que ejecute manualmente la línea con `! ssh pti@45.90.123.172 -p 38 'cd /home/pti/SiteVisit-Django && make deploy'`.

---

## Verificación post-deploy

1. Abrir el portal web del servidor de producción → login como manager
2. **Crear visita de prueba** → debe redirigir a `/manager/visits/?tab=planificados&q=`
3. **Abrir detalle de una visita con tracking points** → el tracker debe mostrar `+Xh YYm` entre pasos (color accent, alineado derecha)
4. **Ir a `/manager/photos/gallery/`** → verificar:
   - Tamaño de archivo en la esquina inferior derecha de cada card
   - Checkbox visible/clickeable en cada foto
   - Al seleccionar 1+ fotos aparece barra flotante (fondo oscuro `bg-neutral`) con botones sólidos verde (Descargar) y rojo (Eliminar, solo super_manager)
5. **Probar descarga**: seleccionar 2-3 fotos → "Descargar" → debe bajar un `.zip` válido con las imágenes
6. **Probar eliminar** (solo super_manager): seleccionar 1 foto → confirmar el toast warning → debe desaparecer del grid
7. **Smoke test app Android**: pedir a un técnico que abra la app y sincronice — `/api/v1/visits/` debe responder normal
