from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display=(
        "username",
        "email",
        "is_online",
        'is_staff',
    )

    search_fields=("username","email")