import json

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .models import Conversation, ConversationMember


class ConversationAPITests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.yann = User.objects.create_user(
            username="yann",
            email="yann@example.test",
            password="test-password-42",
            first_name="Yann",
        )
        self.paul = User.objects.create_user(
            username="paul",
            email="paul@example.test",
            password="test-password-42",
            first_name="Paul",
        )
        self.sarah = User.objects.create_user(
            username="sarah",
            email="sarah@example.test",
            password="test-password-42",
            first_name="Sarah",
        )
        self.client.force_login(self.yann)

    def post_json(self, url, data):
        return self.client.post(
            url,
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_directory_excludes_current_user_and_private_fields(self):
        response = self.client.get(reverse("user_directory"))

        self.assertEqual(response.status_code, 200)
        users = response.json()["users"]
        self.assertEqual({user["username"] for user in users}, {"paul", "sarah"})
        self.assertTrue(all("email" not in user and "password" not in user for user in users))

    def test_directory_search_matches_username_and_name(self):
        response = self.client.get(reverse("user_directory"), {"q": "Pau"})

        self.assertEqual(
            [user["username"] for user in response.json()["users"]],
            ["paul"],
        )

    def test_private_conversation_is_created_once_and_reused(self):
        url = reverse("start_private_conversation")
        first = self.post_json(url, {"user_id": self.paul.pk})
        second = self.post_json(url, {"user_id": self.paul.pk})

        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["created"])
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.json()["created"])
        self.assertEqual(
            first.json()["conversation"]["id"],
            second.json()["conversation"]["id"],
        )
        self.assertEqual(
            Conversation.objects.filter(type=Conversation.ConversationType.PRIVATE).count(),
            1,
        )
        conversation = Conversation.objects.get()
        pair_key = f"{min(self.yann.pk, self.paul.pk)}:{max(self.yann.pk, self.paul.pk)}"
        self.assertEqual(conversation.private_pair_key, pair_key)
        self.assertSetEqual(
            set(conversation.members.values_list("user_id", flat=True)),
            {self.yann.pk, self.paul.pk},
        )

    def test_existing_private_conversation_is_reused(self):
        conversation = Conversation.objects.create(
            type=Conversation.ConversationType.PRIVATE,
            created_by=self.yann,
        )
        ConversationMember.objects.create(conversation=conversation, user=self.yann)
        ConversationMember.objects.create(conversation=conversation, user=self.paul)

        response = self.post_json(
            reverse("start_private_conversation"),
            {"user_id": self.paul.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["created"])
        self.assertEqual(response.json()["conversation"]["id"], conversation.pk)
        self.assertEqual(conversation.__class__.objects.count(), 1)
        conversation.refresh_from_db()
        pair_key = f"{min(self.yann.pk, self.paul.pk)}:{max(self.yann.pk, self.paul.pk)}"
        self.assertEqual(conversation.private_pair_key, pair_key)

    def test_existing_duplicate_private_rows_are_not_multiplied(self):
        conversations = []
        for _ in range(2):
            conversation = Conversation.objects.create(
                type=Conversation.ConversationType.PRIVATE,
            )
            ConversationMember.objects.create(conversation=conversation, user=self.yann)
            ConversationMember.objects.create(conversation=conversation, user=self.paul)
            conversations.append(conversation)

        response = self.post_json(
            reverse("start_private_conversation"),
            {"user_id": self.paul.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["created"])
        self.assertEqual(response.json()["conversation"]["id"], conversations[0].pk)
        self.assertEqual(Conversation.objects.count(), 2)

    def test_private_conversation_rejects_self_and_unknown_user(self):
        url = reverse("start_private_conversation")

        self_response = self.post_json(url, {"user_id": self.yann.pk})
        missing_user_response = self.post_json(url, {"user_id": 999999})

        self.assertEqual(self_response.status_code, 400)
        self.assertEqual(missing_user_response.status_code, 404)
        self.assertFalse(Conversation.objects.exists())

    def test_private_pair_database_constraint_prevents_duplicate_keys(self):
        pair_key = f"{min(self.yann.pk, self.paul.pk)}:{max(self.yann.pk, self.paul.pk)}"
        Conversation.objects.create(
            type=Conversation.ConversationType.PRIVATE,
            private_pair_key=pair_key,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Conversation.objects.create(
                type=Conversation.ConversationType.PRIVATE,
                private_pair_key=pair_key,
            )

    def test_group_creation_adds_creator_as_admin_and_selected_members(self):
        response = self.post_json(
            reverse("create_group_conversation"),
            {"name": "Projet", "member_ids": [self.paul.pk, self.sarah.pk]},
        )

        self.assertEqual(response.status_code, 201)
        conversation = Conversation.objects.get()
        self.assertEqual(conversation.type, Conversation.ConversationType.GROUP)
        self.assertEqual(conversation.name, "Projet")
        self.assertSetEqual(
            set(conversation.members.values_list("user_id", flat=True)),
            {self.yann.pk, self.paul.pk, self.sarah.pk},
        )
        creator_membership = conversation.members.get(user=self.yann)
        self.assertEqual(creator_membership.role, ConversationMember.MemberRole.ADMIN)
        self.assertEqual(
            set(conversation.members.exclude(user=self.yann).values_list("role", flat=True)),
            {ConversationMember.MemberRole.MEMBER},
        )

    def test_group_creation_rejects_empty_members_and_invalid_user(self):
        url = reverse("create_group_conversation")

        empty_response = self.post_json(url, {"name": "Vide", "member_ids": []})
        invalid_response = self.post_json(url, {"name": "Groupe", "member_ids": [999999]})

        self.assertEqual(empty_response.status_code, 400)
        self.assertEqual(invalid_response.status_code, 404)
        self.assertFalse(Conversation.objects.exists())

    def test_conversation_page_only_lists_current_users_memberships(self):
        own_conversation = Conversation.objects.create()
        ConversationMember.objects.create(conversation=own_conversation, user=self.yann)
        other_conversation = Conversation.objects.create()
        ConversationMember.objects.create(conversation=other_conversation, user=self.paul)

        response = self.client.get(reverse("espace_chat"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-id="{own_conversation.pk}"')
        self.assertNotContains(response, f'data-id="{other_conversation.pk}"')
        self.assertNotContains(response, "yann@example.test")

    def test_conversation_operations_require_authentication(self):
        self.client.logout()

        directory_response = self.client.get(reverse("user_directory"))
        start_response = self.post_json(
            reverse("start_private_conversation"),
            {"user_id": self.paul.pk},
        )

        self.assertEqual(directory_response.status_code, 302)
        self.assertEqual(start_response.status_code, 302)
