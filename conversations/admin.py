
from django.contrib import admin
from .models import Conversation, ConversationMember


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "type",
        "name",
        "created_by",
        "created_at",
    )

    list_filter = ("type", "created_at")
    search_fields = ("name",)


@admin.register(ConversationMember)
class ConversationMemberAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "conversation",
        "user",
        "role",
        "joined_at",
    )

    list_filter = ("role", "joined_at")
    search_fields = ("user__username", "conversation__name")
