from django.db import models
from django.contrib.auth.models import AbstractUser,BaseUserManager


# Create your models here.
import uuid

from django.db import models


class UserManager(BaseUserManager):

    def create_user(self, username, email, password=None, **extra_fields):

        if not email:
            raise ValueError("L'adresse email est obligatoire")

        email = self.normalize_email(email)

        user = self.model(
            username=username,
            email=email,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, username, email, password=None, **extra_fields):

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Un superutilisateur doit avoir is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Un superutilisateur doit avoir is_superuser=True")

        return self.create_user(
            username=username,
            email=email,
            password=password,
            **extra_fields)

class User(AbstractUser):
    username = models.CharField(
        max_length=50,
        unique=True
    )

    email = models.EmailField(
        unique=True
    )

    password = models.CharField(
        max_length=255
    )

    avatar = models.URLField(
        blank=True,
        null=True
    )

    bio = models.TextField(
        max_length=300,
        blank=True
    )

    is_online = models.BooleanField(
        default=False
    )

    last_seen = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.username
