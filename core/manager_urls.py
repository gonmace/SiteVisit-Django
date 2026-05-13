from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from dashboard.web_views import DashboardWebView
from sites.web_views import SiteCreateView, SiteDeleteView, SiteDetailView, SiteImportView, SiteSearchJsonView, SitesListView, SiteUpdateView
from users.web_views import (
    ApproveActivationView,
    CoordinatorCreateView,
    CoordinatorDeleteView,
    CoordinatorsListView,
    CoordinatorToggleStatusView,
    CoordinatorUpdateView,
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
    path('visits/<int:pk>/approve/',     VisitApproveView.as_view(),           name='visit_approve'),
    path('visits/<int:pk>/reject/',      VisitRejectView.as_view(),            name='visit_reject'),

    # Sites
    path('sites/',                     SitesListView.as_view(),      name='sites_list'),
    path('sites/search/',              SiteSearchJsonView.as_view(), name='sites_search'),
    path('sites/new/',                 SiteCreateView.as_view(),     name='site_create'),
    path('sites/<int:pk>/',            SiteDetailView.as_view(),     name='site_detail'),
    path('sites/import/',              SiteImportView.as_view(),  name='site_import'),
    path('sites/<int:pk>/edit/',       SiteUpdateView.as_view(),  name='site_edit'),
    path('sites/<int:pk>/delete/',     SiteDeleteView.as_view(),  name='site_delete'),

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
]
