from rest_framework.routers import DefaultRouter

from sites import views

router = DefaultRouter()
router.register('', views.SiteViewSet, basename='site')
urlpatterns = router.urls
