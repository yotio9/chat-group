
from django.db import models
from django.conf import settings
from django.db.models import Q


class Conversation(models.Model):

    class ConversationType(models.TextChoices):
        PRIVATE = "private", "Privée"
        GROUP = "group", "Groupe"

    type = models.CharField(
        max_length=10,
        choices=ConversationType.choices,
        default=ConversationType.PRIVATE,
    )

    name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    private_pair_key = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        editable=False,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_conversations"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["private_pair_key"],
                condition=Q(
                    type="private",
                    private_pair_key__isnull=False,
                ),
                name="unique_private_conversation_pair",
            ),
        ]

    def __str__(self):
        if self.type == self.ConversationType.GROUP:
            return self.name or f"Groupe #{self.id}"

        return f"Conversation privée #{self.id}"


class ConversationMember(models.Model):

    class MemberRole(models.TextChoices):
        MEMBER = "member", "Membre"
        ADMIN = "admin", "Administrateur"

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="members"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversation_memberships"
    )

    role = models.CharField(
        max_length=10,
        choices=MemberRole.choices,
        default=MemberRole.MEMBER
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"],
                name="unique_conversation_member"
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.conversation}"
