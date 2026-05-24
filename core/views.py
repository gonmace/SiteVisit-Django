from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from home.context_processors import _load_palette as _resolve_palette


class ThemeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, version=None):
        company = request.query_params.get('company', 'default')
        return Response(_resolve_palette(company))
