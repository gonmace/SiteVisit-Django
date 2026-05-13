from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from sites.models import Site


@admin.register(Site)
class SiteAdmin(ImportExportModelAdmin):
    list_display  = ['code', 'operator_code', 'name', 'company', 'is_active', 'created_at']
    list_filter   = ['company', 'is_active']
    search_fields = ['code', 'operator_code', 'name']
    ordering      = ['code']
