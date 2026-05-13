from rest_framework.routers import DefaultRouter

from visits import views

router = DefaultRouter()
router.register('', views.VisitViewSet, basename='visit')
urlpatterns = router.urls
