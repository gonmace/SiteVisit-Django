from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticated

from sites.models import Site
from sites.serializers import SiteSerializer
from users.permissions import IsPortalOrTechnician


class SiteViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class   = SiteSerializer
    permission_classes = [IsAuthenticated, IsPortalOrTechnician]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields   = ['company', 'is_active']
    search_fields      = ['code', 'name', 'operator_code']
    pagination_class   = None

    def get_queryset(self):
        return Site.objects.all()
