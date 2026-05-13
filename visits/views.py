from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import User
from users.permissions import IsTechnician
from visits.models import (
    STATUS_TO_GPS_EVENT,
    TECHNICIAN_TRANSITIONS,
    Visit,
    VisitPhoto,
    VisitTrackingPoint,
)
from visits.serializers import (
    TrackingPointSerializer,
    VisitCreateSerializer,
    VisitDetailSerializer,
    VisitListSerializer,
    VisitPhotoSerializer,
    VisitStatusSerializer,
)


class VisitViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend]
    filterset_fields   = ['status', 'site', 'scheduled_date']

    def get_serializer_class(self):
        if self.action == 'create':
            return VisitCreateSerializer
        if self.action == 'retrieve':
            return VisitDetailSerializer
        return VisitListSerializer

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed('POST', detail='visit_creation_via_web_only')

    def get_queryset(self):
        user = self.request.user
        qs = Visit.objects.select_related('technician', 'site', 'coordinator', 'approved_by', 'rejected_by')
        if user.role == User.Role.TECHNICIAN:
            return qs.filter(technician=user).exclude(
                status__in=[Visit.Status.PENDIENTE_APROBACION, Visit.Status.RECHAZADA]
            )
        if user.role == User.Role.MANAGER:
            return qs.filter(technician__company=user.company)
        return qs  # super_manager, viewer

    def get_permissions(self):
        return [IsAuthenticated()]

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed('PUT')

    def partial_update(self, request, *args, **kwargs):
        raise MethodNotAllowed('PATCH')

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed('DELETE')

    @action(detail=True, methods=['post'], url_path='status')
    def update_status(self, request, pk=None, version=None):
        visit = self.get_object()
        if not IsTechnician().has_permission(request, self):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)

        serializer = VisitStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        new_status = data['status']
        allowed_next = TECHNICIAN_TRANSITIONS.get(visit.status)
        if new_status != allowed_next:
            return Response(
                {'detail': 'invalid_transition', 'allowed': allowed_next},
                status=status.HTTP_400_BAD_REQUEST,
            )

        update_fields = ['status']
        visit.status = new_status

        if new_status == Visit.Status.EN_CAMINO and data.get('eta') is not None:
            visit.eta = data['eta']
            update_fields.append('eta')

        if new_status == Visit.Status.TRABAJANDO:
            visit.hora_inicio_trabajos = data.get('timestamp') or timezone.now()
            update_fields.append('hora_inicio_trabajos')
        elif new_status == Visit.Status.COMPLETADA:
            visit.hora_fin_trabajos = data.get('timestamp') or timezone.now()
            update_fields.append('hora_fin_trabajos')

        visit.save(update_fields=update_fields)

        event = STATUS_TO_GPS_EVENT.get(new_status)
        if event and data.get('latitude') is not None and data.get('longitude') is not None:
            VisitTrackingPoint.objects.create(
                visit=visit,
                event=event,
                latitude=data['latitude'],
                longitude=data['longitude'],
                timestamp=data.get('timestamp') or timezone.now(),
            )

        return Response(VisitDetailSerializer(visit).data)

    @action(detail=True, methods=['patch'], url_path='notas')
    def update_notas(self, request, pk=None, version=None):
        visit = self.get_object()
        if not IsTechnician().has_permission(request, self):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)
        if visit.status != Visit.Status.COMPLETADA:
            return Response({'detail': 'only_completed'}, status=status.HTTP_400_BAD_REQUEST)
        visit.notas = request.data.get('notas', '')
        visit.save(update_fields=['notas'])
        return Response(VisitListSerializer(visit).data)

    @action(detail=True, methods=['post'])
    def tracking(self, request, pk=None, version=None):
        visit = self.get_object()
        if not IsTechnician().has_permission(request, self):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)

        data = request.data if isinstance(request.data, list) else [request.data]
        serializer = TrackingPointSerializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)

        points = VisitTrackingPoint.objects.bulk_create([
            VisitTrackingPoint(visit=visit, **item)
            for item in serializer.validated_data
        ])
        return Response(TrackingPointSerializer(points, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def photos(self, request, pk=None, version=None):
        visit = self.get_object()
        if not IsTechnician().has_permission(request, self):
            return Response({'detail': 'forbidden'}, status=status.HTTP_403_FORBIDDEN)

        files = request.FILES.getlist('image')
        if not files:
            return Response({'detail': 'no_images'}, status=status.HTTP_400_BAD_REQUEST)

        photo_types  = request.POST.getlist('photo_type')
        taken_ats    = request.POST.getlist('taken_at')
        latitudes    = request.POST.getlist('latitude')
        longitudes   = request.POST.getlist('longitude')
        descriptions = request.POST.getlist('description')

        def safe_float(lst, i):
            try:
                return float(lst[i]) if i < len(lst) and lst[i] else None
            except (ValueError, TypeError):
                return None

        created = []
        for i, image in enumerate(files):
            photo = VisitPhoto.objects.create(
                visit=visit,
                image=image,
                photo_type=photo_types[i] if i < len(photo_types) else VisitPhoto.PhotoType.TRABAJO_1,
                description=descriptions[i] if i < len(descriptions) else '',
                taken_at=taken_ats[i] if i < len(taken_ats) and taken_ats[i] else timezone.now(),
                latitude=safe_float(latitudes, i),
                longitude=safe_float(longitudes, i),
            )
            created.append(photo)

        return Response(VisitPhotoSerializer(created, many=True).data, status=status.HTTP_201_CREATED)
