from django.db import IntegrityError
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from users.models import ProfilePhoto, User, UserDevice
from users.permissions import IsManager, IsSameCompanyOrSuperManager
from users.serializers import (
    ActivateSerializer,
    ClaimTechnicianSerializer,
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    TechnicianSearchSerializer,
    UserSerializer,
)
from users.throttles import ActivationRateThrottle, LoginRateThrottle


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [IsAuthenticated, IsManager]

    def perform_create(self, serializer):
        serializer.save()


class PublicRegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = []

    def perform_create(self, serializer):
        serializer.save()


class SearchTechniciansView(generics.ListAPIView):
    serializer_class = TechnicianSearchSerializer
    permission_classes = []
    pagination_class = None

    def get_queryset(self):
        email = self.request.query_params.get('email', '').strip()
        if email:
            return User.objects.filter(role=User.Role.TECHNICIAN, email__iexact=email)[:1]

        q = self.request.query_params.get('q', '').strip()
        if not q:
            return User.objects.none()
        terms = q.split()
        qs = User.objects.filter(role=User.Role.TECHNICIAN)
        for term in terms:
            qs = qs.filter(
                Q(first_name__icontains=term) | Q(last_name__icontains=term)
            )
        return qs[:20]


class ClaimTechnicianView(APIView):
    permission_classes = []

    def post(self, request, pk):
        try:
            user = User.objects.get(pk=pk, role=User.Role.TECHNICIAN)
        except User.DoesNotExist:
            return Response({'detail': 'not_found'}, status=status.HTTP_404_NOT_FOUND)

        if hasattr(user, 'device'):
            return Response({'detail': 'already_activated'}, status=status.HTTP_409_CONFLICT)

        serializer = ClaimTechnicianSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user.set_password(data['password'])
        if data.get('company'):
            user.company = data['company']
        if data.get('rut'):
            user.rut = data['rut']
        if data.get('first_name'):
            user.first_name = data['first_name']
        if data.get('last_name'):
            user.last_name = data['last_name']
        if data.get('cargo'):
            user.cargo = data['cargo']
        if data.get('phone'):
            user.phone = data['phone']
        try:
            user.save()
        except IntegrityError:
            return Response(
                {'detail': 'rut_duplicate'},
                status=status.HTTP_409_CONFLICT,
            )

        return Response({
            'detail': 'claimed',
            'user_id': user.id,
            'email': user.email,
            'status': user.status,
        })


class ActivateView(APIView):
    permission_classes = []
    throttle_classes = [ActivationRateThrottle]

    def post(self, request, pk):
        serializer = ActivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            target_user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'not_found'}, status=status.HTTP_404_NOT_FOUND)

        if target_user.email != data['email'] or not target_user.check_password(data['password']):
            return Response({'detail': 'invalid_credentials'}, status=status.HTTP_401_UNAUTHORIZED)

        if hasattr(target_user, 'device'):
            return Response({'detail': 'device_already_registered'}, status=status.HTTP_409_CONFLICT)

        device = UserDevice.objects.create(
            user=target_user,
            fingerprint=data['device_fingerprint'],
            android_id=data.get('android_id', ''),
            manufacturer=data.get('manufacturer', ''),
            model=data.get('model', ''),
            os_version=data.get('os_version', ''),
            is_active=False,
        )
        target_user.status = User.Status.PENDING
        target_user.save(update_fields=['status'])

        if 'image' in data:
            ProfilePhoto.objects.update_or_create(
                user=target_user,
                defaults={
                    'image':    data['image'],
                    'taken_at': data.get('taken_at'),
                },
            )

        return Response({'detail': 'pending_manager_approval'}, status=status.HTTP_202_ACCEPTED)


class PendingUsersView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsManager]

    def get_queryset(self):
        qs = User.objects.filter(status=User.Status.PENDING)
        if self.request.user.role == User.Role.SUPER_MANAGER:
            return qs
        return qs.filter(company=self.request.user.company)


class ApproveUserView(APIView):
    permission_classes = [IsAuthenticated, IsManager, IsSameCompanyOrSuperManager]

    def post(self, request, pk):
        try:
            target_user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'not_found'}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, target_user)

        try:
            device = target_user.device
        except UserDevice.DoesNotExist:
            return Response({'detail': 'no_device'}, status=status.HTTP_400_BAD_REQUEST)

        target_user.status = User.Status.ACTIVE
        target_user.save(update_fields=['status'])
        device.is_active = True
        device.save(update_fields=['is_active'])

        return Response({'detail': 'approved'})


class RejectUserView(APIView):
    permission_classes = [IsAuthenticated, IsManager, IsSameCompanyOrSuperManager]

    def post(self, request, pk):
        try:
            target_user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'detail': 'not_found'}, status=status.HTTP_404_NOT_FOUND)

        self.check_object_permissions(request, target_user)

        UserDevice.objects.filter(user=target_user).delete()

        return Response({'detail': 'rejected'})


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
