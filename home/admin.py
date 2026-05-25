from django.contrib import admin

from home.models import AppRelease, SiteSetting


@admin.register(AppRelease)
class AppReleaseAdmin(admin.ModelAdmin):
    list_display       = ['__str__', 'version', 'uploaded_at']
    readonly_fields    = ['uploaded_at']
    fields             = ['apk', 'version', 'notes', 'uploaded_at']

    def has_module_perms(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display       = ['name', 'slug', 'primary']
    list_display_links = ['name']
    list_editable      = ['primary']
    search_fields      = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        (None, {
            'fields': ('slug', 'name', 'primary'),
            'description': 'Nombre de la empresa y color primario en hexadecimal (#RRGGBB).',
        }),
        ('Avanzado', {
            'classes': ('collapse',),
            'fields': ('secondary', 'accent', 'logo_url'),
        }),
    )
