import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from users.models import User

from .models import Notification, PushSubscription
from .services import notify_supervisors


def _make_user(email, role, **kwargs):
    # User.save() sincroniza is_active con status: sin ACTIVE el usuario queda inactivo.
    kwargs.setdefault('status', User.Status.ACTIVE)
    return User.objects.create_user(
        username=email.split('@')[0],
        email=email,
        password='x',
        role=role,
        **kwargs,
    )


class NotifyServiceTests(TestCase):
    def setUp(self):
        self.super_mgr = _make_user('super@t.cl', User.Role.SUPER_MANAGER)
        self.manager = _make_user('mgr@t.cl', User.Role.MANAGER)
        self.tech = _make_user('tech@t.cl', User.Role.TECHNICIAN)

    def test_solo_super_managers_reciben(self):
        notify_supervisors(
            event=Notification.Event.VISIT_PENDING,
            title='Servicio pendiente',
        )
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(Notification.objects.first().user, self.super_mgr)

    def test_superuser_recibe(self):
        admin = _make_user('admin@t.cl', User.Role.MANAGER, is_superuser=True)
        notify_supervisors(event=Notification.Event.TECHNICIAN_PENDING, title='T')
        recipients = set(Notification.objects.values_list('user_id', flat=True))
        self.assertEqual(recipients, {self.super_mgr.pk, admin.pk})

    def test_exclude_user(self):
        otro = _make_user('super2@t.cl', User.Role.SUPER_MANAGER)
        notify_supervisors(
            event=Notification.Event.VISIT_PENDING,
            title='T',
            exclude_user=self.super_mgr,
        )
        recipients = set(Notification.objects.values_list('user_id', flat=True))
        self.assertEqual(recipients, {otro.pk})

    @patch('notifications.services.threading.Thread')
    def test_lanza_thread_si_hay_suscripciones(self, mock_thread):
        PushSubscription.objects.create(
            user=self.super_mgr, endpoint='https://push.example/abc',
            p256dh='k', auth='a',
        )
        notify_supervisors(event=Notification.Event.VISIT_PENDING, title='T')
        mock_thread.assert_called_once()

    def test_nunca_lanza_excepcion(self):
        # event inválido no debe romper la vista llamante
        try:
            notify_supervisors(event=None, title=None)
        except Exception as exc:  # pragma: no cover
            self.fail(f'notify_supervisors lanzó {exc!r}')


# Storage simple: en tests no hay collectstatic, el manifest de whitenoise no existe.
@override_settings(STORAGES={
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
})
class PwaEndpointsTests(TestCase):
    def test_sw_js(self):
        r = self.client.get('/sw.js')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/javascript')
        self.assertIn(b'showNotification', r.content)

    def test_manifest(self):
        r = self.client.get('/manifest.json')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'"start_url": "/manager/"', r.content)


class BellViewsTests(TestCase):
    def setUp(self):
        self.super_mgr = _make_user('super@t.cl', User.Role.SUPER_MANAGER)
        self.manager = _make_user('mgr@t.cl', User.Role.MANAGER)
        Notification.objects.create(
            user=self.super_mgr,
            event=Notification.Event.VISIT_PENDING,
            title='N1', url='/manager/visits/1/',
        )

    def test_anonimo_redirige_a_login(self):
        r = self.client.get(reverse('manager:notifications_list'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/manager/login/', r['Location'])

    def test_manager_regular_no_accede(self):
        self.client.force_login(self.manager)
        r = self.client.get(reverse('manager:notifications_list'))
        self.assertEqual(r.status_code, 302)  # redirect a visits_approval

    def test_lista_y_unread(self):
        self.client.force_login(self.super_mgr)
        r = self.client.get(reverse('manager:notifications_list'))
        data = r.json()
        self.assertEqual(data['unread_count'], 1)
        self.assertEqual(data['items'][0]['title'], 'N1')

    def test_mark_read_y_read_all(self):
        self.client.force_login(self.super_mgr)
        n = Notification.objects.first()
        r = self.client.post(reverse('manager:notification_read', args=[n.pk]))
        self.assertEqual(r.status_code, 200)
        n.refresh_from_db()
        self.assertTrue(n.is_read)

        Notification.objects.create(
            user=self.super_mgr, event=Notification.Event.VISIT_PENDING, title='N2',
        )
        self.client.post(reverse('manager:notifications_read_all'))
        self.assertFalse(
            Notification.objects.filter(user=self.super_mgr, is_read=False).exists()
        )

    def test_no_marca_notificaciones_ajenas(self):
        otro = _make_user('super2@t.cl', User.Role.SUPER_MANAGER)
        n = Notification.objects.create(
            user=otro, event=Notification.Event.VISIT_PENDING, title='Ajena',
        )
        self.client.force_login(self.super_mgr)
        self.client.post(reverse('manager:notification_read', args=[n.pk]))
        n.refresh_from_db()
        self.assertFalse(n.is_read)

    def test_subscribe_y_unsubscribe(self):
        self.client.force_login(self.super_mgr)
        payload = {
            'endpoint': 'https://push.example/sub1',
            'keys': {'p256dh': 'pk', 'auth': 'ak'},
        }
        r = self.client.post(
            reverse('manager:push_subscribe'),
            json.dumps(payload), content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(PushSubscription.objects.count(), 1)

        # re-suscripción del mismo endpoint = update, no duplica
        self.client.post(
            reverse('manager:push_subscribe'),
            json.dumps(payload), content_type='application/json',
        )
        self.assertEqual(PushSubscription.objects.count(), 1)

        r = self.client.post(
            reverse('manager:push_unsubscribe'),
            json.dumps({'endpoint': payload['endpoint']}),
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(PushSubscription.objects.count(), 0)

    def test_subscribe_payload_invalido(self):
        self.client.force_login(self.super_mgr)
        r = self.client.post(
            reverse('manager:push_subscribe'), 'no-json',
            content_type='application/json',
        )
        self.assertEqual(r.status_code, 400)
