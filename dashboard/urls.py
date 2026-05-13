from django.urls import path

from dashboard.views import MapDataView, StatsView

urlpatterns = [
    path('stats/', StatsView.as_view()),
    path('map-data/', MapDataView.as_view()),
]
