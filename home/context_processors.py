import json
import os

from django.conf import settings


def theme(request):
    """Inject active theme colors and app download URL into every template context."""
    company = 'default'
    if request.user.is_authenticated and hasattr(request.user, 'company'):
        company = request.user.company or 'default'

    palette = _load_palette(company)
    return {'theme': palette, 'apk_download_url': _get_apk_url()}


def _get_apk_url() -> str:
    try:
        from home.models import AppRelease
        release = AppRelease.objects.only('apk').first()
        if release and release.apk:
            return release.apk.url
    except Exception:
        pass
    return ''


def _load_palette(company: str) -> dict:
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
