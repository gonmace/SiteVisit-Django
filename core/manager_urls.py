from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path

from dashboard.web_views import DashboardWebView
from home.web_views import AppReleaseView
from notifications.web_views import (
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
    NotificationUnreadCountView,
    PushSubscribeView,
    PushUnsubscribeView,
)
from sites.web_views import SiteCreateView, SiteDeleteView, SiteDetailView, SiteExportView, SiteImportView, SiteSearchJsonView, SiteTemplateView, SitesListView, SiteUpdateView
from users.web_views import (
    ApproveActivationView,
    CoordinatorCreateView,
    CoordinatorDeleteView,
    CoordinatorsListView,
    CoordinatorToggleStatusView,
    CoordinatorUpdateView,
    ManagerCreateView,
    ManagerDeleteView,
    ManagersListView,
    ManagerToggleStatusView,
    ManagerUpdateView,
    PendingActivationsView,
    RejectActivationView,
    TechnicianCreateView,
    TechnicianDeleteView,
    TechnicianImportView,
    TechnicianResetDeviceView,
    TechnicianToggleStatusView,
    TechnicianUpdateView,
    UsersListView,
)
from visits.web_views import (
    VisitApproveView,
    VisitCancelView,
    VisitCreateWebView,
    VisitDeleteView,
    VisitDetailWebView,
    VisitPhotoBulkDeleteView,
    VisitPhotoBulkDownloadView,
    VisitRejectView,
    VisitsApprovalView,
    VisitUpdateWebView,
)

app_name = 'manager'

urlpatterns = [
    path('',        DashboardWebView.as_view(), name='dashboard'),

    path('login/',  LoginView.as_view(
                        template_name='manager/login.html',
                        redirect_authenticated_user=True,
                    ), name='login'),
    path('logout/', LogoutView.as_view(next_page='manager:login'), name='logout'),

    # Visits
    path('visits/',                      VisitsApprovalView.as_view(),     name='visits_approval'),
    path('visits/new/',                  VisitCreateWebView.as_view(),     name='visit_create'),
    path('visits/<int:pk>/',             VisitDetailWebView.as_view(),         name='visit_detail'),
    path('visits/<int:pk>/edit/',        VisitUpdateWebView.as_view(),         name='visit_edit'),
    path('visits/<int:pk>/cancel/',       VisitCancelView.as_view(),            name='visit_cancel'),
    path('visits/<int:pk>/delete/',       VisitDeleteView.as_view(),            name='visit_delete'),
    path('visits/<int:pk>/approve/',           VisitApproveView.as_view(),            name='visit_approve'),
    path('visits/<int:pk>/reject/',            VisitRejectView.as_view(),             name='visit_reject'),
    path('visits/photos/bulk-download/',       VisitPhotoBulkDownloadView.as_view(),  name='visit_photo_bulk_download'),
    path('visits/photos/bulk-delete/',         VisitPhotoBulkDeleteView.as_view(),    name='visit_photo_bulk_delete'),

    # Sites
    path('sites/',                     SitesListView.as_view(),      name='sites_list'),
    path('sites/search/',              SiteSearchJsonView.as_view(), name='sites_search'),
    path('sites/new/',                 SiteCreateView.as_view(),     name='site_create'),
    path('sites/<int:pk>/',            SiteDetailView.as_view(),     name='site_detail'),
    path('sites/import/',              SiteImportView.as_view(),    name='site_import'),
    path('sites/export/',              SiteExportView.as_view(),    name='site_export'),
    path('sites/template/',            SiteTemplateView.as_view(),  name='site_template'),
    path('sites/<int:pk>/edit/',       SiteUpdateView.as_view(),  name='site_edit'),
    path('sites/<int:pk>/delete/',     SiteDeleteView.as_view(),  name='site_delete'),

    # Managers (solo superusuario)
    path('managers/',                    ManagersListView.as_view(),       name='managers_list'),
    path('managers/new/',                ManagerCreateView.as_view(),      name='manager_create'),
    path('managers/<int:pk>/edit/',      ManagerUpdateView.as_view(),      name='manager_edit'),
    path('managers/<int:pk>/delete/',    ManagerDeleteView.as_view(),      name='manager_delete'),
    path('managers/<int:pk>/toggle/',    ManagerToggleStatusView.as_view(),name='manager_toggle'),

    # Coordinators
    path('coordinators/',                   CoordinatorsListView.as_view(),       name='coordinators_list'),
    path('coordinators/new/',               CoordinatorCreateView.as_view(),      name='coordinator_create'),
    path('coordinators/<int:pk>/edit/',     CoordinatorUpdateView.as_view(),      name='coordinator_edit'),
    path('coordinators/<int:pk>/delete/',   CoordinatorDeleteView.as_view(),      name='coordinator_delete'),
    path('coordinators/<int:pk>/toggle/',   CoordinatorToggleStatusView.as_view(),name='coordinator_toggle'),

    # Technicians
    path('users/',                     UsersListView.as_view(),         name='users_list'),
    path('users/new/',                 TechnicianCreateView.as_view(),  name='technician_create'),
    path('users/import/',              TechnicianImportView.as_view(),  name='technician_import'),
    path('users/<int:pk>/edit/',       TechnicianUpdateView.as_view(),  name='technician_edit'),
    path('users/<int:pk>/reset-device/', TechnicianResetDeviceView.as_view(),  name='technician_reset_device'),
    path('users/<int:pk>/toggle/',       TechnicianToggleStatusView.as_view(), name='technician_toggle'),
    path('users/<int:pk>/delete/',     TechnicianDeleteView.as_view(),  name='technician_delete'),

    # Activations
    path('activations/',                  PendingActivationsView.as_view(),  name='pending_activations'),
    path('activations/<int:pk>/approve/', ApproveActivationView.as_view(),   name='approve_activation'),
    path('activations/<int:pk>/reject/',  RejectActivationView.as_view(),    name='reject_activation'),

    # Notifications (solo super_manager / superuser)
    path('notifications/',                 NotificationListView.as_view(),        name='notifications_list'),
    path('notifications/unread-count/',    NotificationUnreadCountView.as_view(), name='notifications_unread_count'),
    path('notifications/<int:pk>/read/',   NotificationMarkReadView.as_view(),    name='notification_read'),
    path('notifications/read-all/',        NotificationMarkAllReadView.as_view(), name='notifications_read_all'),
    path('notifications/subscribe/',       PushSubscribeView.as_view(),           name='push_subscribe'),
    path('notifications/unsubscribe/',     PushUnsubscribeView.as_view(),         name='push_unsubscribe'),

    # Photos
    path('photos/', include('photos.urls', namespace='photos')),

    # App release
    path('app-release/', AppReleaseView.as_view(), name='app_release'),
]
