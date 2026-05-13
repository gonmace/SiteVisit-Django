from django.contrib import admin

from home.models import SiteSetting


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
