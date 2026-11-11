from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from conversations.models import Conversation, ConversationMember
from .models import Message


class MessageAccessTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.yann = User.objects.create_user(
            username="yann",
            email="yann@example.test",
            password="test-password-42",
        )
        self.paul = User.objects.create_user(
            username="paul",
            email="paul@example.test",
            password="test-password-42",
        )
        self.sarah = User.objects.create_user(
            username="sarah",
            email="sarah@example.test",
            password="test-password-42",
        )
        self.private_conversation = Conversation.objects.create(
            type=Conversation.ConversationType.PRIVATE,
            created_by=self.yann,
        )
        ConversationMember.objects.create(
            conversation=self.private_conversation,
            user=self.yann,
        )
        ConversationMember.objects.create(
            conversation=self.private_conversation,
            user=self.paul,
        )
        self.other_conversation = Conversation.objects.create(
            type=Conversation.ConversationType.PRIVATE,
            created_by=self.paul,
        )
        ConversationMember.objects.create(
            conversation=self.other_conversation,
            user=self.paul,
        )
        ConversationMember.objects.create(
            conversation=self.other_conversation,
            user=self.sarah,
        )
        Message.objects.create(
            conversation=self.private_conversation,
            sender=self.paul,
            content="Message privé",
        )
        Message.objects.create(
            conversation=self.other_conversation,
            sender=self.sarah,
            content="Message séparé",
        )
        self.client.force_login(self.yann)

    def test_message_history_contains_only_selected_conversation(self):
        response = self.client.get(
            reverse("get_messages", args=[self.private_conversation.pk])
        )

        self.assertEqual(response.status_code, 200)
        messages = response.json()["messages"]
        self.assertEqual([message["content"] for message in messages], ["Message privé"])
        self.assertNotIn(
            "Message séparé",
            [message["content"] for message in messages],
        )

    def test_non_member_cannot_read_or_send_to_conversation(self):
        read_response = self.client.get(
            reverse("get_messages", args=[self.other_conversation.pk])
        )
        send_response = self.client.post(
            reverse("send_message", args=[self.other_conversation.pk]),
            data='{"content":"intrusion"}',
            content_type="application/json",
        )

        self.assertEqual(read_response.status_code, 404)
        self.assertEqual(send_response.status_code, 404)
        self.assertFalse(
            Message.objects.filter(content="intrusion").exists()
        )

    def test_group_messages_are_limited_to_group_members(self):
        group = Conversation.objects.create(
            type=Conversation.ConversationType.GROUP,
            name="Equipe",
            created_by=self.yann,
        )
        ConversationMember.objects.create(conversation=group, user=self.yann)
        ConversationMember.objects.create(conversation=group, user=self.paul)
        Message.objects.create(
            conversation=group,
            sender=self.paul,
            content="Message du groupe",
        )

        response = self.client.get(reverse("get_messages", args=[group.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [message["content"] for message in response.json()["messages"]],
            ["Message du groupe"],
        )

    def test_sending_a_message_requires_csrf_and_persists_to_selected_conversation(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.yann)
        url = reverse("send_message", args=[self.private_conversation.pk])

        rejected = client.post(
            url,
            data='{"content":"Sans CSRF"}',
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 403)

        page = client.get(reverse("espace_chat"))
        self.assertEqual(page.status_code, 200)
        csrf_token = page.cookies["csrftoken"].value
        response = client.post(
            url,
            data='{"content":"Nouveau message"}',
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["success"])
        self.assertTrue(
            Message.objects.filter(
                conversation=self.private_conversation,
                content="Nouveau message",
                sender=self.yann,
            ).exists()
        )
