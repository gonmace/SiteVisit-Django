from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from import_export.admin import ImportExportModelAdmin

from users.models import ProfilePhoto, User, UserDevice
from users.resources import UserResource


@admin.register(User)
class UserAdmin(ImportExportModelAdmin, BaseUserAdmin):
    resource_classes = [UserResource]

    list_display  = ['email', 'get_full_name', 'rut', 'cargo', 'company', 'role', 'status', 'is_active']
    list_filter   = ['company', 'role', 'status']
    search_fields = ['email', 'first_name', 'last_name', 'rut']
    ordering      = ['email']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('SiteVisit', {
            'fields': ('role', 'company', 'rut', 'cargo', 'phone', 'status'),
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('SiteVisit', {
            'fields': ('email', 'role', 'company', 'rut', 'cargo', 'phone'),
        }),
    )


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display    = ['user', 'android_id', 'manufacturer', 'model', 'os_version', 'is_active', 'registered_at']
    list_filter     = ['is_active', 'manufacturer']
    search_fields   = ['user__email', 'android_id', 'fingerprint']
    raw_id_fields   = ['user']
    readonly_fields = ['fingerprint', 'android_id', 'manufacturer', 'model', 'os_version', 'registered_at']


@admin.register(ProfilePhoto)
class ProfilePhotoAdmin(admin.ModelAdmin):
    list_display  = ['user', 'taken_at', 'uploaded_at']
    raw_id_fields = ['user']
