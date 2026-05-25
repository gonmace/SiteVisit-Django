from django.contrib import admin

from visits.models import Visit, VisitPhoto, VisitTrackingPoint


class VisitPhotoInline(admin.TabularInline):
    model  = VisitPhoto
    extra  = 0
    fields = ['photo_type', 'image', 'latitude', 'longitude', 'taken_at']
    readonly_fields = ['uploaded_at']


class TrackingPointInline(admin.TabularInline):
    model  = VisitTrackingPoint
    extra  = 0
    fields = ['event', 'latitude', 'longitude', 'timestamp']
    readonly_fields = ['uploaded_at']


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display    = ['id', 'coordinator', 'technician', 'site', 'status', 'scheduled_date', 'created_at']
    list_filter     = ['status', 'site__company', 'scheduled_date']
    search_fields   = ['technician__email', 'coordinator__email', 'site__code', 'site__name']
    raw_id_fields   = ['technician', 'site', 'coordinator', 'approved_by', 'rejected_by', 'cancelled_by']
    readonly_fields = ['created_at', 'hora_inicio_trabajos', 'hora_fin_trabajos',
                       'approved_at', 'rejected_at', 'cancelled_at']
    inlines         = [VisitPhotoInline, TrackingPointInline]


@admin.register(VisitPhoto)
class VisitPhotoAdmin(admin.ModelAdmin):
    list_display  = ['visit', 'photo_type', 'taken_at', 'uploaded_at']
    list_filter   = ['photo_type']
    raw_id_fields = ['visit']


@admin.register(VisitTrackingPoint)
class VisitTrackingPointAdmin(admin.ModelAdmin):
    list_display  = ['visit', 'event', 'latitude', 'longitude', 'timestamp']
    list_filter   = ['event']
    raw_id_fields = ['visit']
