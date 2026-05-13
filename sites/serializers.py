from rest_framework import serializers

from sites.models import Site


class SiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Site
        fields = ['id', 'code', 'operator_code', 'name', 'latitude', 'longitude', 'company', 'is_active']
