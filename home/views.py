from django.contrib.auth import logout
from django.shortcuts import redirect

from users.models import User


def index(request):
    if not request.user.is_authenticated:
        return redirect('manager:login')
    if request.user.role in (User.Role.MANAGER, User.Role.SUPER_MANAGER):
        return redirect('manager:visits_approval')
    # Authenticated but wrong role: log out to avoid redirect loop
    logout(request)
    return redirect('manager:login')
