import json
import os

from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView

from core.mixins import PortalAccessRequiredMixin, CompanyScopedQuerysetMixin

from .models import Photo


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get_ct(ct_id):
    return get_object_or_404(ContentType, pk=ct_id)


def _photo_data(photo):
    return {
        'id': photo.pk,
        'url': photo.imagen.url,
        'thumbnail_url': photo.thumbnail_url,
        'descripcion': photo.descripcion or '',
        'exif_lat': photo.exif_lat,
        'exif_lon': photo.exif_lon,
        'exif_datetime': photo.exif_datetime.strftime('%d/%m/%Y %H:%M') if photo.exif_datetime else None,
        'orden': photo.orden,
    }


# ── Per-object endpoints ────────────────────────────────────────────────────────

class ListPhotosView(PortalAccessRequiredMixin, View):
    """GET → JSON list of photos attached to a specific object."""

    def get(self, request, ct_id, object_id):
        ct     = _get_ct(ct_id)
        photos = Photo.objects.filter(content_type=ct, object_id=object_id)
        etapa  = request.GET.get('etapa', '')
        if etapa:
            photos = photos.filter(etapa=etapa)
        return JsonResponse({'success': True, 'photos': [_photo_data(p) for p in photos]})


@method_decorator(csrf_exempt, name='dispatch')
class UploadPhotosView(PortalAccessRequiredMixin, View):
    """POST to upload one or more photos attached to an object."""

    def post(self, request, ct_id, object_id):
        ct    = _get_ct(ct_id)
        etapa = request.POST.get('etapa', '')
        files = request.FILES.getlist('photos')

        if not files:
            return JsonResponse({'success': False, 'message': 'No se recibieron archivos'}, status=400)

        created = []
        for file in files:
            if not file.content_type.startswith('image/'):
                continue
            photo = Photo.objects.create(
                content_type=ct,
                object_id=object_id,
                app=ct.app_label,
                etapa=etapa,
                imagen=file,
                descripcion=request.POST.get('descripcion', ''),
            )
            photo.refresh_from_db()
            created.append(_photo_data(photo))

        if not created:
            return JsonResponse({'success': False, 'message': 'No se procesaron imágenes válidas'}, status=400)

        return JsonResponse({
            'success': True,
            'photos': created,
            'message': f'Se subieron {len(created)} foto(s)',
        })


@method_decorator(csrf_exempt, name='dispatch')
class UpdatePhotoView(PortalAccessRequiredMixin, View):
    """POST JSON {photo_id, descripcion} to update description."""

    def post(self, request, ct_id, object_id):
        ct = _get_ct(ct_id)
        try:
            data       = json.loads(request.body)
            photo_id   = data.get('photo_id')
            descripcion = data.get('descripcion', '')
            photo = get_object_or_404(Photo, pk=photo_id, content_type=ct, object_id=object_id)
            photo.descripcion = descripcion
            photo.save(update_fields=['descripcion', 'updated_at'])
            return JsonResponse({'success': True, 'message': 'Descripción actualizada'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class ReorderPhotosView(PortalAccessRequiredMixin, View):
    """POST JSON {orden: [id, id, ...]} to set display order."""

    def post(self, request, ct_id, object_id):
        ct = _get_ct(ct_id)
        try:
            data  = json.loads(request.body)
            orden = data.get('orden', [])
            for idx, photo_id in enumerate(orden):
                Photo.objects.filter(pk=photo_id, content_type=ct, object_id=object_id).update(orden=idx)
            return JsonResponse({'success': True, 'message': 'Orden actualizado'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)


@method_decorator(csrf_exempt, name='dispatch')
class DeletePhotoView(PortalAccessRequiredMixin, View):
    """POST to delete one photo."""

    def post(self, request, ct_id, object_id, photo_id):
        ct    = _get_ct(ct_id)
        photo = get_object_or_404(Photo, pk=photo_id, content_type=ct, object_id=object_id)
        photo.delete()
        return JsonResponse({'success': True, 'message': 'Foto eliminada'})


# ── Gallery (muestra VisitPhoto — fotos subidas desde la app móvil) ──────────────

class PhotoGalleryView(PortalAccessRequiredMixin, CompanyScopedQuerysetMixin, ListView):
    context_object_name = 'photos'
    template_name       = 'manager/photos/gallery.html'
    paginate_by         = 60

    def get_queryset(self):
        from visits.models import Visit, VisitPhoto
        from users.models import User

        qs = VisitPhoto.objects.select_related(
            'visit', 'visit__technician', 'visit__site',
        ).order_by('-uploaded_at')

        qs = self.apply_company_filter(qs, 'visit__technician__company')

        paso   = self.request.GET.get('paso', '')
        site_q = self.request.GET.get('site', '').strip()

        tech_id = self.request.GET.get('tech', '').strip()
        if tech_id.isdigit():
            qs = qs.filter(visit__technician_id=int(tech_id))

        _LLEGADA_TYPES  = ['llegada', 'vehiculo']
        _SERVICIO_TYPES = [f'trabajo_{i}' for i in range(1, 11)]

        if site_q:
            from django.db.models import Q
            qs = qs.filter(
                Q(visit__site__code__icontains=site_q) |
                Q(visit__site__operator_code__icontains=site_q) |
                Q(visit__site__name__icontains=site_q) |
                Q(visit__technician__first_name__icontains=site_q) |
                Q(visit__technician__last_name__icontains=site_q)
            )
        if paso == 'llegada':
            qs = qs.filter(photo_type__in=_LLEGADA_TYPES)
        elif paso == 'servicio':
            qs = qs.filter(photo_type__in=_SERVICIO_TYPES)

        return qs

    def get_context_data(self, **kwargs):
        from users.models import User
        context = super().get_context_data(**kwargs)
        context['paso_filter'] = self.request.GET.get('paso', '')
        context['site_filter'] = self.request.GET.get('site', '')
        tech_id = self.request.GET.get('tech', '').strip()
        context['tech_filter'] = tech_id
        context['tech_name']   = ''
        if tech_id.isdigit():
            try:
                t = User.objects.get(pk=int(tech_id))
                context['tech_name'] = t.get_full_name() or t.email
            except User.DoesNotExist:
                pass
        paginator = context.get('paginator')
        context['total_count'] = paginator.count if paginator else len(context.get('photos', []))
        context['shown_count'] = len(context.get('photos', []))
        context['pasos'] = [
            ('llegada',  'Llegada'),
            ('servicio', 'Servicio'),
        ]
        context.update(self.company_context())
        return context


# ── Bulk operations ──────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class BulkDeletePhotosView(PortalAccessRequiredMixin, View):

    def post(self, request):
        data = json.loads(request.body)
        ids  = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
        if not ids:
            return JsonResponse({'success': False, 'message': 'No se seleccionaron fotos'}, status=400)
        photos = Photo.objects.filter(pk__in=ids)
        count  = photos.count()
        # delete() triggers signal → files removed
        photos.delete()
        return JsonResponse({'success': True, 'message': f'{count} foto(s) eliminada(s)'})


@method_decorator(csrf_exempt, name='dispatch')
class BulkDownloadPhotosView(PortalAccessRequiredMixin, View):

    def post(self, request):
        import io
        import zipfile

        data = json.loads(request.body)
        ids  = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
        if not ids:
            return JsonResponse({'success': False, 'message': 'No se seleccionaron fotos'}, status=400)

        photos     = list(Photo.objects.filter(pk__in=ids))
        buffer     = io.BytesIO()
        seen_names = {}

        with zipfile.ZipFile(buffer, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for photo in photos:
                try:
                    path = photo.imagen.path
                    if not os.path.exists(path):
                        continue
                    filename = os.path.basename(path)
                    if filename in seen_names:
                        seen_names[filename] += 1
                        name, ext = os.path.splitext(filename)
                        filename  = f'{name}_{seen_names[filename]}{ext}'
                    else:
                        seen_names[filename] = 0
                    zf.write(path, filename)
                except Exception:
                    pass

        buffer.seek(0)
        response = StreamingHttpResponse(
            iter([buffer.read()]),
            content_type='application/zip',
        )
        response['Content-Disposition'] = 'attachment; filename="fotos.zip"'
        return response


@method_decorator(csrf_exempt, name='dispatch')
class CompressPhotosView(PortalAccessRequiredMixin, View):

    def post(self, request):
        from PIL import Image

        data    = json.loads(request.body)
        ids     = [int(i) for i in data.get('ids', []) if str(i).isdigit()]
        quality = max(10, min(int(data.get('quality', 70)), 95))

        if not ids:
            return JsonResponse({'success': False, 'message': 'No se seleccionaron fotos'}, status=400)

        compressed  = 0
        saved_bytes = 0

        for photo in Photo.objects.filter(pk__in=ids):
            try:
                path = photo.imagen.path
                if not path.lower().endswith(('.jpg', '.jpeg')):
                    continue
                original = os.path.getsize(path)
                with Image.open(path) as img:
                    exif = img.info.get('exif', b'')
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    img.save(path, quality=quality, optimize=True, exif=exif)
                new_size    = os.path.getsize(path)
                saved_bytes += max(0, original - new_size)
                Photo.objects.filter(pk=photo.pk).update(file_size=new_size)
                compressed += 1
            except Exception:
                pass

        saved_kb = saved_bytes // 1024
        return JsonResponse({
            'success': True,
            'message': f'{compressed} foto(s) comprimida(s). Ahorro: {saved_kb} KB',
            'saved_bytes': saved_bytes,
        })
