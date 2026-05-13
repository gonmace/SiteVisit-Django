from django.urls import path

from users import views

urlpatterns = [
    path('register/', views.RegisterView.as_view()),
    path('public-register/', views.PublicRegisterView.as_view()),
    path('search-technicians/', views.SearchTechniciansView.as_view()),
    path('<int:pk>/activate/', views.ActivateView.as_view()),
    path('<int:pk>/claim/', views.ClaimTechnicianView.as_view()),
    path('<int:pk>/approve/', views.ApproveUserView.as_view()),
    path('<int:pk>/reject/', views.RejectUserView.as_view()),
    path('pending/', views.PendingUsersView.as_view()),
    path('me/', views.MeView.as_view()),
]
