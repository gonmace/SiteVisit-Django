from datetime import date, timedelta

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from sites.models import Site
from users.models import User
from visits.models import Visit


def _visits_for_user(user):
    qs = Visit.objects.all()
    if user.role == User.Role.MANAGER:
        qs = qs.filter(technician__company=user.company)
    return qs


def _avg_work_duration_minutes(qs):
    """Returns average work duration in minutes for completed visits, or None."""
    result = qs.filter(
        status=Visit.Status.COMPLETADA,
        hora_inicio_trabajos__isnull=False,
        hora_fin_trabajos__isnull=False,
    ).annotate(
        duration=ExpressionWrapper(
            F('hora_fin_trabajos') - F('hora_inicio_trabajos'),
            output_field=DurationField(),
        )
    ).aggregate(avg=Avg('duration'))['avg']
    if result is None:
        return None
    return round(result.total_seconds() / 60, 1)


class StatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, version=None):
        user = request.user
        allowed = (User.Role.MANAGER, User.Role.SUPER_MANAGER, User.Role.VIEWER)
        if user.role not in allowed:
            return Response({'detail': 'forbidden'}, status=403)

        qs = _visits_for_user(user)
        by_status = {s: qs.filter(status=s).count() for s in Visit.Status.values}
        avg_duration = _avg_work_duration_minutes(qs)

        # Top technicians by visit count
        top_techs = list(
            qs.values('technician__email', 'technician__first_name', 'technician__last_name')
              .annotate(count=Count('id'))
              .order_by('-count')[:10]
        )

        stats = {
            'total':        qs.count(),
            'by_status':    by_status,
            'avg_duration': avg_duration,
            'top_techs':    top_techs,
        }

        if user.role in (User.Role.SUPER_MANAGER, User.Role.VIEWER):
            stats['by_company'] = {
                c: qs.filter(technician__company=c).count()
                for c in User.Company.values
            }

        return Response(stats)


class MapDataView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, version=None):
        user = request.user
        allowed = (User.Role.MANAGER, User.Role.SUPER_MANAGER, User.Role.VIEWER)
        if user.role not in allowed:
            return Response({'detail': 'forbidden'}, status=403)

        qs = _visits_for_user(user)

        # Empresa: solo super_manager/viewer pueden filtrar; MANAGER queda forzado a la suya
        company = request.query_params.get('company', 'all')
        if user.role == User.Role.MANAGER:
            company = user.company
            qs = qs.filter(site__company=company)
        elif company and company != 'all':
            qs = qs.filter(site__company=company)

        # Estados (csv)
        status_param = request.query_params.get('status', '')
        if status_param:
            statuses = [s for s in status_param.split(',') if s in Visit.Status.values]
            if statuses:
                qs = qs.filter(status__in=statuses)

        # Rango de fechas (default: últimos 7 días)
        today = timezone.localdate()
        date_from_str = request.query_params.get('date_from', '')
        date_to_str   = request.query_params.get('date_to', '')

        if date_from_str:
            try:
                qs = qs.filter(scheduled_date__gte=date.fromisoformat(date_from_str))
            except ValueError:
                pass
        else:
            qs = qs.filter(scheduled_date__gte=today - timedelta(days=29))

        if date_to_str:
            try:
                qs = qs.filter(scheduled_date__lte=date.fromisoformat(date_to_str))
            except ValueError:
                pass
        else:
            if not date_from_str:
                qs = qs.filter(scheduled_date__lte=today + timedelta(days=14))

        # Técnico
        technician_id = request.query_params.get('technician', '')
        if technician_id:
            try:
                qs = qs.filter(technician_id=int(technician_id))
            except (ValueError, TypeError):
                pass

        # Sitio (código parcial)
        site_code = request.query_params.get('site_code', '').strip()
        if site_code:
            qs = qs.filter(site__code__icontains=site_code)

        # Datos de visitas con info de sitio y técnico
        visits_qs = list(
            qs.select_related('technician', 'site')
              .values(
                  'id', 'status', 'scheduled_date',
                  'site_id', 'site__code', 'site__latitude', 'site__longitude', 'site__company',
                  'technician__first_name', 'technician__last_name', 'technician_id',
              )
              .annotate(tracking_count=Count('tracking_points'))
        )

        # Conteo de visitas por sitio
        site_visit_count = {}
        for v in visits_qs:
            site_visit_count[v['site_id']] = site_visit_count.get(v['site_id'], 0) + 1

        # Sitios únicos con visitas en el filtro
        site_ids = list(site_visit_count.keys())
        sites = [
            {
                'id': s['id'],
                'code': s['code'],
                'name': s['name'],
                'lat': s['latitude'],
                'lng': s['longitude'],
                'company': s['company'],
                'visit_count': site_visit_count.get(s['id'], 0),
            }
            for s in Site.objects.filter(id__in=site_ids).values(
                'id', 'code', 'name', 'latitude', 'longitude', 'company'
            )
        ]

        status_display = dict(Visit.Status.choices)
        visits_out = [
            {
                'id': v['id'],
                'status': v['status'],
                'status_display': status_display.get(v['status'], v['status']),
                'scheduled_date': str(v['scheduled_date']),
                'site_id': v['site_id'],
                'site_code': v['site__code'],
                'lat': v['site__latitude'],
                'lng': v['site__longitude'],
                'technician_name': f"{v['technician__first_name']} {v['technician__last_name']}".strip(),
                'technician_id': v['technician_id'],
                'tracking_count': v['tracking_count'],
            }
            for v in visits_qs
        ]

        return Response({'sites': sites, 'visits': visits_out})
