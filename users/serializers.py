from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from users.models import User, UserDevice


class UserSerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'role', 'company', 'rut', 'cargo', 'phone',
            'status', 'photo_url',
        ]
        read_only_fields = ['id', 'status']

    def get_photo_url(self, obj):
        request = self.context.get('request')
        try:
            if obj.profile_photo and obj.profile_photo.image:
                url = obj.profile_photo.image.url
                return request.build_absolute_uri(url) if request else url
        except Exception:
            pass
        return None


class TechnicianSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'company', 'rut', 'email', 'cargo']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'company', 'cargo', 'phone', 'rut']

    def validate_company(self, value):
        if value not in [c.value for c in User.Company]:
            raise serializers.ValidationError('Empresa no válida. Use WOM o PTI.')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        username = validated_data['email'].split('@')[0]
        user = User(**validated_data, username=username, status=User.Status.INACTIVE,
                    role=User.Role.TECHNICIAN)
        user.set_password(password)
        user.save()
        return user


class ClaimTechnicianSerializer(serializers.Serializer):
    password   = serializers.CharField(write_only=True, min_length=8)
    company    = serializers.ChoiceField(choices=User.Company.choices, required=False)
    rut        = serializers.CharField(max_length=20, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name  = serializers.CharField(max_length=150, required=False, allow_blank=True)
    cargo      = serializers.CharField(max_length=64, required=False, allow_blank=True)
    phone      = serializers.CharField(max_length=20, required=False, allow_blank=True)


class ActivateSerializer(serializers.Serializer):
    email              = serializers.EmailField()
    password           = serializers.CharField()
    device_fingerprint = serializers.CharField(max_length=64)
    android_id         = serializers.CharField(max_length=64, required=False, allow_blank=True)
    manufacturer       = serializers.CharField(max_length=64, required=False, allow_blank=True)
    model              = serializers.CharField(max_length=64, required=False, allow_blank=True)
    os_version         = serializers.CharField(max_length=20, required=False, allow_blank=True)
    image              = serializers.ImageField(required=False)
    taken_at           = serializers.DateTimeField(required=False)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    device_fingerprint = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        # Technicians with INACTIVE status have is_active=False, which causes
        # super().validate() to fail with a generic 401 before device checks run.
        # Pre-check: if credentials are valid but status is INACTIVE, return device_not_registered.
        email    = attrs.get(self.username_field, '')
        password = attrs.get('password', '')
        try:
            candidate = User.objects.get(email=email)
            if (candidate.role == User.Role.TECHNICIAN
                    and candidate.status == User.Status.INACTIVE
                    and candidate.check_password(password)):
                raise AuthenticationFailed(
                    {'detail': 'device_not_registered', 'user_id': candidate.id}
                )
        except User.DoesNotExist:
            pass

        data = super().validate(attrs)
        user = self.user

        if user.role == User.Role.TECHNICIAN:
            fingerprint = attrs.get('device_fingerprint', '').strip()

            try:
                device = user.device
            except UserDevice.DoesNotExist:
                raise AuthenticationFailed(
                    {'detail': 'device_not_registered', 'user_id': user.id}
                )

            if user.status == User.Status.PENDING:
                raise PermissionDenied({'detail': 'pending_manager_approval', 'user_id': user.id})

            if device.fingerprint != fingerprint:
                raise PermissionDenied({'detail': 'device_unauthorized'})

        data['role']    = user.role
        data['user_id'] = user.id
        data['company'] = user.company
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role']    = user.role
        token['company'] = user.company
        return token
