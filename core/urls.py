from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.sitemaps.views import sitemap
from rest_framework_simplejwt.views import TokenRefreshView
from home.sitemaps import StaticViewSitemap
from users.views import CustomTokenObtainPairView
from core.views import ThemeView

sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(
        template_name='robots.txt',
        content_type='text/plain',
        extra_context={'ADMIN_URL': settings.ADMIN_URL},
    )),
    # PWA: servidos desde la raíz (scope '/' del service worker, sin hash de whitenoise)
    path('sw.js', TemplateView.as_view(
        template_name='sw.js',
        content_type='application/javascript',
    ), name='service_worker'),
    path('manifest.json', TemplateView.as_view(
        template_name='manifest.json',
        content_type='application/manifest+json',
    ), name='pwa_manifest'),
    path('api/token/', CustomTokenObtainPairView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
    path('api/v1/users/', include('users.urls')),
    path('api/v1/sites/', include('sites.urls')),
    path('api/v1/visits/', include('visits.urls')),
    path('api/v1/dashboard/', include('dashboard.urls')),
    path('api/v1/theme/', ThemeView.as_view()),
    path('manager/', include('core.manager_urls')),
    path('', include('home.urls')),
]

if settings.DEBUG:
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [path('__reload__/', include('django_browser_reload.urls'))]
