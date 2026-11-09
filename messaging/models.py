from django.db import models

from django.conf import settings
from django.db import models


class Message(models.Model):

    conversation = models.ForeignKey(
        "conversations.Conversation",
        on_delete=models.CASCADE,
        related_name="messages"
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_messages"
    )

    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    is_edited = models.BooleanField(default=False)

    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"Message de {self.sender} dans {self.conversation}"
# Create your models here.


class MessageStatus(models.Model):

    class StatusChoices(models.TextChoices):
        SENT = "sent", "Envoyé"
        DELIVERED = "delivered", "Reçu"
        READ = "read", "Lu"

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="statuses"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="message_statuses"
    )

    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.SENT
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user"],
                name="unique_message_status_per_user"
            )
        ]

    def __str__(self):
        return f"{self.message_id} - {self.user} - {self.status}"
