from django.conf import settings
from django.db import models


class Visit(models.Model):
    class Status(models.TextChoices):
        PENDIENTE_APROBACION = 'pendiente_aprobacion', 'Pendiente de aprobación'
        PROGRAMADA           = 'programada',           'Programado'
        EN_CAMINO            = 'en_camino',            'Inicio'
        LLEGADA              = 'llegada',              'Sitio'
        TRABAJANDO           = 'trabajando',           'Servicio'
        FINALIZANDO          = 'finalizando',          'Finalizando'
        COMPLETADA           = 'completada',           'Completado'
        CANCELADA            = 'cancelada',            'Cancelado'
        RECHAZADA            = 'rechazada',            'Rechazada'

    technician           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='visits')
    site                 = models.ForeignKey('sites.Site', on_delete=models.CASCADE, related_name='visits')
    status               = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDIENTE_APROBACION)
    reason               = models.TextField()
    scheduled_date       = models.DateField()
    eta                  = models.TimeField(null=True, blank=True)
    hora_inicio_trabajos = models.DateTimeField(null=True, blank=True)
    hora_fin_trabajos    = models.DateTimeField(null=True, blank=True)
    coordinator          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                             null=True, blank=True, related_name='coordinated_visits')
    approved_by          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                             null=True, blank=True, related_name='approved_visits')
    approved_at          = models.DateTimeField(null=True, blank=True)
    rejected_by                = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                                   null=True, blank=True, related_name='rejected_visits')
    rejected_at                = models.DateTimeField(null=True, blank=True)
    rejection_reason           = models.TextField(blank=True)
    status_before_rejection    = models.CharField(max_length=24, blank=True, default='')
    cancelled_by               = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                                   null=True, blank=True, related_name='cancelled_visits')
    cancelled_at               = models.DateTimeField(null=True, blank=True)
    cancellation_reason        = models.TextField(blank=True)
    status_before_cancellation = models.CharField(max_length=24, blank=True, default='')
    notas                      = models.TextField(blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'visita'
        verbose_name_plural = 'visitas'
        ordering = ['-created_at']

    def __str__(self):
        return f'Visita {self.pk} — {self.technician.email} → {self.site.code}'


# State machine: current_status → next_status (technician-driven)
TECHNICIAN_TRANSITIONS = {
    Visit.Status.PROGRAMADA:  Visit.Status.EN_CAMINO,
    Visit.Status.EN_CAMINO:   Visit.Status.LLEGADA,
    Visit.Status.LLEGADA:     Visit.Status.TRABAJANDO,
    Visit.Status.TRABAJANDO:  Visit.Status.FINALIZANDO,
    Visit.Status.FINALIZANDO: Visit.Status.COMPLETADA,
}

# GPS event created automatically on each transition
STATUS_TO_GPS_EVENT = {
    Visit.Status.EN_CAMINO:   'salida',
    Visit.Status.LLEGADA:     'llegada',
    Visit.Status.TRABAJANDO:  'inicio',
    Visit.Status.FINALIZANDO: 'finalizado',
    Visit.Status.COMPLETADA:  'cierre',
}


class VisitPhoto(models.Model):
    class PhotoType(models.TextChoices):
        VEHICULO   = 'vehiculo',   'Movilidad (frente)'
        ENCARGADO  = 'encargado',  'Encargado'
        TRABAJO_1  = 'trabajo_1',  'Imagen 1'
        TRABAJO_2  = 'trabajo_2',  'Imagen 2'
        TRABAJO_3  = 'trabajo_3',  'Imagen 3'
        TRABAJO_4  = 'trabajo_4',  'Imagen 4'
        TRABAJO_5  = 'trabajo_5',  'Imagen 5'
        TRABAJO_6  = 'trabajo_6',  'Imagen 6'
        TRABAJO_7  = 'trabajo_7',  'Imagen 7'
        TRABAJO_8  = 'trabajo_8',  'Imagen 8'
        TRABAJO_9  = 'trabajo_9',  'Imagen 9'
        TRABAJO_10 = 'trabajo_10', 'Imagen 10'
        LLEGADA    = 'llegada',    'Llegada al sitio'
        CIERRE     = 'cierre',     'Cierre'

    visit        = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='photos')
    photo_type   = models.CharField(max_length=16, choices=PhotoType.choices)
    image        = models.ImageField(upload_to='visits/%Y/%m/')
    description  = models.TextField(blank=True)
    latitude     = models.FloatField(null=True, blank=True)
    longitude    = models.FloatField(null=True, blank=True)
    metadata     = models.JSONField(default=dict)
    taken_at     = models.DateTimeField()
    uploaded_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'foto de visita'
        verbose_name_plural = 'fotos de visitas'


class VisitTrackingPoint(models.Model):
    class Event(models.TextChoices):
        SALIDA      = 'salida',      'Salida'
        LLEGADA     = 'llegada',     'Llegada'
        INICIO      = 'inicio',      'Inicio de trabajos'
        CIERRE      = 'cierre',      'Cierre de Servicio'
        FINALIZADO  = 'finalizado',  'Finalizado'

    visit       = models.ForeignKey(Visit, on_delete=models.CASCADE, related_name='tracking_points')
    event       = models.CharField(max_length=16, choices=Event.choices)
    latitude    = models.FloatField()
    longitude   = models.FloatField()
    timestamp   = models.DateTimeField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'punto de tracking'
        verbose_name_plural = 'puntos de tracking'
        ordering = ['timestamp']
