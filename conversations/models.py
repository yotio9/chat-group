from django.db import models
from django.conf import settings


class Conversation(models.Model):
    class ConversationType(models.TextChoices):
        PRIVATE = "Private", "Privéé"
        GROUP = "group", "Group"

    type = models.CharField(
        max_length=50,
        choices=ConversationType.choices,
        default=ConversationType.PRIVATE,
        
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    created_by =models.ForeignKey(
        settings.AUTH_
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

    def __str__(self):
        if self.type == self.ConversationType.GROUP:
            return self.name or f"Groupe #{self.id}"

        return f"Conversation privée #{self.id}"

######################@
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
       
    
