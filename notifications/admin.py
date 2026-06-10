from django.contrib import admin

from .models import Notification, PushSubscription


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'title', 'is_read', 'created_at')
    list_filter = ('event', 'is_read')
    search_fields = ('title', 'body', 'user__email')
    readonly_fields = ('created_at',)


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_agent', 'created_at')
    search_fields = ('user__email',)
    readonly_fields = ('created_at',)
