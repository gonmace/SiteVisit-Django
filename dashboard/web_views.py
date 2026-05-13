from datetime import timedelta
import json

from django.db.models import Count
from django.db.models.functions import ExtractWeekDay
from django.utils import timezone
from django.views.generic import TemplateView

from users.models import User
from visits.models import Visit
from visits.web_views import ManagerRequiredMixin


class DashboardWebView(ManagerRequiredMixin, TemplateView):
    template_name = 'manager/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == User.Role.MANAGER:
            from django.shortcuts import redirect
            return redirect('manager:visits_approval')
        return super().dispatch(request, *args, **kwargs)

    def _qs(self):
        qs = Visit.objects.all()
        if self.request.user.role == User.Role.MANAGER:
            qs = qs.filter(technician__company=self.request.user.company)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = self._qs()
        total = qs.count()

        by_status = {s: qs.filter(status=s).count() for s in Visit.Status.values}

        active = by_status['en_camino'] + by_status['llegada'] + by_status['trabajando']
        completion_rate   = round(by_status['completada'] / total * 100) if total else 0
        cancellation_rate = round(by_status['cancelada']  / total * 100) if total else 0

        avg_duration = None
        completed_qs = qs.filter(
            status=Visit.Status.COMPLETADA,
            hora_inicio_trabajos__isnull=False,
            hora_fin_trabajos__isnull=False,
        )
        if completed_qs.exists():
            total_secs = sum(
                (v.hora_fin_trabajos - v.hora_inicio_trabajos).total_seconds()
                for v in completed_qs
            )
            avg_duration = round(total_secs / completed_qs.count() / 60, 1)

        today = timezone.localdate()

        # KPIs operacionales
        hoy_count     = qs.filter(scheduled_date=today).count()
        semana_count  = qs.filter(scheduled_date__gte=today, scheduled_date__lte=today + timedelta(days=6)).count()
        pendientes_count = by_status.get('pendiente_aprobacion', 0)
        rechazadas_count = by_status.get('rechazada', 0)
        rechazo_rate  = round(rechazadas_count / total * 100) if total else 0

        hoy_completadas = qs.filter(scheduled_date=today, status=Visit.Status.COMPLETADA).count()
        completitud_hoy = round(hoy_completadas / hoy_count * 100) if hoy_count else None

        # Tiempo promedio de aprobación (horas)
        avg_approval_hours = None
        approved_qs = qs.filter(approved_at__isnull=False)
        if approved_qs.exists():
            total_approval_secs = sum(
                (v.approved_at - v.created_at).total_seconds()
                for v in approved_qs.only('approved_at', 'created_at')
            )
            avg_approval_hours = round(total_approval_secs / approved_qs.count() / 3600, 1)

        # Top 10 técnicos
        top_techs = list(
            qs.values('technician__email', 'technician__first_name', 'technician__last_name')
              .annotate(count=Count('id'))
              .order_by('-count')[:10]
        )
        max_tech_count = top_techs[0]['count'] if top_techs else 1

        # Top 5 sitios
        top_sites = list(
            qs.values('site__code', 'site__name', 'site__operator_code')
              .annotate(count=Count('id'))
              .order_by('-count')[:5]
        )
        max_site_count = top_sites[0]['count'] if top_sites else 1

        # Distribución por día de semana (ExtractWeekDay: 1=Dom … 7=Sáb)
        weekday_raw = (
            qs.annotate(wd=ExtractWeekDay('scheduled_date'))
              .values('wd')
              .annotate(count=Count('id'))
        )
        weekday_map = {(row['wd'] - 2) % 7: row['count'] for row in weekday_raw}
        weekday_labels = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
        weekday_data   = [weekday_map.get(i, 0) for i in range(7)]

        trend_ranges = {}

        # 7 y 30 días — agrupado por día
        for days in (7, 30):
            first_day = today - timedelta(days=days - 1)
            raw = (
                qs.filter(scheduled_date__gte=first_day, scheduled_date__lte=today)
                  .values('scheduled_date')
                  .annotate(count=Count('id'))
            )
            day_map = {row['scheduled_date']: row['count'] for row in raw}
            labels, data = [], []
            for i in range(days - 1, -1, -1):
                d = today - timedelta(days=i)
                labels.append(d.strftime('%d/%m'))
                data.append(day_map.get(d, 0))
            trend_ranges[str(days)] = {'labels': labels, 'data': data}

        # 90 días — agrupado por semana (13 semanas)
        weeks = 13
        first_day_90 = today - timedelta(days=weeks * 7 - 1)
        raw_90 = (
            qs.filter(scheduled_date__gte=first_day_90, scheduled_date__lte=today)
              .values('scheduled_date')
              .annotate(count=Count('id'))
        )
        day_map_90 = {row['scheduled_date']: row['count'] for row in raw_90}
        labels_90, data_90 = [], []
        for w in range(weeks - 1, -1, -1):
            week_start = today - timedelta(days=w * 7 + 6)
            count = sum(day_map_90.get(week_start + timedelta(days=d), 0) for d in range(7))
            labels_90.append(week_start.strftime('%d/%m'))
            data_90.append(count)
        trend_ranges['90'] = {'labels': labels_90, 'data': data_90}

        # Compatibilidad: exponer el rango por defecto (7d) para el chart inicial
        trend_labels = trend_ranges['7']['labels']
        trend_data   = trend_ranges['7']['data']

        by_company = None
        if self.request.user.role == User.Role.SUPER_MANAGER:
            by_company = {c: qs.filter(technician__company=c).count() for c in User.Company.values}

        # Estadísticas de técnicos
        tech_qs = User.objects.filter(role=User.Role.TECHNICIAN)
        if self.request.user.role == User.Role.MANAGER:
            tech_qs = tech_qs.filter(company=self.request.user.company)
        coord_qs = User.objects.filter(role=User.Role.MANAGER)
        if self.request.user.role == User.Role.MANAGER:
            coord_qs = coord_qs.filter(company=self.request.user.company)
        tech_stats = {
            'total':        tech_qs.count(),
            'active':       tech_qs.filter(status=User.Status.ACTIVE).count(),
            'pending':      tech_qs.filter(status=User.Status.PENDING).count(),
            'inactive':     tech_qs.filter(status=User.Status.INACTIVE).count(),
            'with_device':  tech_qs.filter(device__isnull=False).count(),
            'coordinators': coord_qs.count(),
        }

        # Contexto para filtros del mapa de operaciones
        is_super = self.request.user.role == User.Role.SUPER_MANAGER
        available_techs_qs = User.objects.filter(role=User.Role.TECHNICIAN)
        if self.request.user.role == User.Role.MANAGER:
            available_techs_qs = available_techs_qs.filter(company=self.request.user.company)
        available_technicians = list(
            available_techs_qs.order_by('first_name', 'last_name')
            .values('id', 'first_name', 'last_name', 'email')
        )

        ctx.update({
            'total': total,
            'by_status': by_status,
            'active': active,
            'completion_rate': completion_rate,
            'cancellation_rate': cancellation_rate,
            'avg_duration': avg_duration,
            'hoy_count': hoy_count,
            'semana_count': semana_count,
            'pendientes_count': pendientes_count,
            'rechazadas_count': rechazadas_count,
            'rechazo_rate': rechazo_rate,
            'completitud_hoy': completitud_hoy,
            'hoy_completadas': hoy_completadas,
            'avg_approval_hours': avg_approval_hours,
            'top_techs': top_techs,
            'max_tech_count': max_tech_count,
            'top_sites': top_sites,
            'max_site_count': max_site_count,
            'weekday_labels_json': json.dumps(weekday_labels),
            'weekday_data_json': json.dumps(weekday_data),
            'trend_labels_json': json.dumps(trend_labels),
            'trend_data_json': json.dumps(trend_data),
            'trend_ranges_json': json.dumps(trend_ranges),
            'by_company': by_company,
            'tech_stats': tech_stats,
            'is_super_manager': is_super,
            'available_technicians': available_technicians,
            'available_statuses': Visit.Status.choices,
            'map_date_from': (today - timedelta(days=29)).isoformat(),
            'map_date_to': (today + timedelta(days=14)).isoformat(),
        })
        return ctx
