
from django.contrib import admin
from .models import Message, MessageStatus


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation",
        "sender",
        "created_at",
        "is_edited",
        "is_deleted",
    )

    list_filter = ("created_at", "is_edited", "is_deleted")
    search_fields = ("content", "sender__username")


@admin.register(MessageStatus)
class MessageStatusAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "message",
        "user",
        "status",
        "updated_at",
    )

    list_filter = ("status", "updated_at")
    search_fields = ("user__username",)
