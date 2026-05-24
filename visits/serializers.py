from rest_framework import serializers

from visits.models import Visit, VisitPhoto, VisitTrackingPoint


class VisitPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitPhoto
        fields = ['id', 'photo_type', 'image', 'description', 'latitude', 'longitude', 'metadata', 'taken_at', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class TrackingPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitTrackingPoint
        fields = ['id', 'event', 'latitude', 'longitude', 'timestamp', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class VisitBaseSerializer(serializers.ModelSerializer):
    technician_name    = serializers.SerializerMethodField()
    coordinator_name   = serializers.SerializerMethodField()
    site_code          = serializers.SerializerMethodField()
    site_operator_code = serializers.SerializerMethodField()
    site_name          = serializers.SerializerMethodField()

    def get_technician_name(self, obj):
        return obj.technician.get_full_name() or obj.technician.email

    def get_coordinator_name(self, obj):
        if obj.coordinator:
            return obj.coordinator.get_full_name() or obj.coordinator.email
        return ''

    def get_site_code(self, obj):
        return obj.site.code

    def get_site_operator_code(self, obj):
        return obj.site.operator_code or ''

    def get_site_name(self, obj):
        return obj.site.name


class VisitListSerializer(VisitBaseSerializer):
    class Meta:
        model = Visit
        fields = [
            'id', 'technician', 'technician_name',
            'coordinator', 'coordinator_name',
            'site', 'site_code', 'site_operator_code', 'site_name',
            'status', 'reason', 'scheduled_date', 'eta',
            'hora_inicio_trabajos', 'hora_fin_trabajos',
            'approved_at', 'rejected_at',
            'notas', 'created_at',
        ]


class VisitDetailSerializer(VisitBaseSerializer):
    photos          = VisitPhotoSerializer(many=True, read_only=True)
    tracking_points = TrackingPointSerializer(many=True, read_only=True)

    class Meta:
        model = Visit
        fields = [
            'id', 'technician', 'technician_name',
            'coordinator', 'coordinator_name',
            'site', 'site_code', 'site_operator_code', 'site_name',
            'status', 'reason', 'scheduled_date', 'eta',
            'hora_inicio_trabajos', 'hora_fin_trabajos',
            'notas', 'approved_by', 'approved_at', 'rejected_by', 'rejected_at', 'rejection_reason',
            'created_at', 'photos', 'tracking_points',
        ]
        read_only_fields = ['id', 'status', 'coordinator', 'approved_by', 'approved_at',
                            'rejected_by', 'rejected_at', 'created_at']


class VisitStatusSerializer(serializers.Serializer):
    status    = serializers.ChoiceField(choices=Visit.Status.choices)
    latitude  = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)
    timestamp = serializers.DateTimeField(required=False)
    eta       = serializers.TimeField(required=False, allow_null=True)
    notas     = serializers.CharField(required=False, allow_blank=True)
