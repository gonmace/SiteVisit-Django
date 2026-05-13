import json
import os

from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class ThemeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, version=None):
        company = request.query_params.get('company', 'default')
        return Response(_resolve_palette(company))


def _resolve_palette(company: str) -> dict:
    try:
        from home.models import SiteSetting
        setting = (
            SiteSetting.objects.filter(slug=company).first()
            or SiteSetting.objects.filter(slug='default').first()
        )
        if setting:
            return setting.to_dict()
    except Exception:
        pass

    theme_path = os.path.join(os.path.dirname(settings.BASE_DIR), 'theme.json')
    try:
        with open(theme_path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'primary': '#F15A22', 'secondary': '#1C2B4A', 'accent': '#FF8C00'}
