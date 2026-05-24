from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from sites.models import Site
from sites.serializers import SiteSerializer
from users.models import User


class SiteViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class   = SiteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields   = ['company', 'is_active']
    search_fields      = ['code', 'name', 'operator_code']

    def get_queryset(self):
        user = self.request.user
        qs = Site.objects.all()
        if user.role in (User.Role.SUPER_MANAGER, User.Role.VIEWER):
            return qs
        return qs.filter(company=user.company)
