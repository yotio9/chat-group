from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase


class AuthenticationFlowTests(TestCase):
    def test_valid_login_redirects_to_home(self):
        user = get_user_model().objects.create_user(
            username="testuser",
            email="test@example.com",
            password="A-secure-test-password-42",
        )

        response = self.client.post(
            reverse("connextion"),
            {
                "username": user.username,
                "password": "A-secure-test-password-42",
            },
        )

        self.assertRedirects(response, reverse("home"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_chat_page_redirects_to_login_and_returns_afterward(self):
        response = self.client.get(reverse("espace_chat"))
        self.assertRedirects(
            response,
            f"{reverse('connextion')}?next={reverse('espace_chat')}",
        )

        user = get_user_model().objects.create_user(
            username="chatuser",
            email="chat@example.com",
            ******,
        )
        response = self.client.post(
            reverse("connextion"),
            {
                "username": user.username,
                "password": "A-secure-test-password-42",
                "next": reverse("espace_chat"),
            },
        )

        self.assertRedirects(response, reverse("espace_chat"))
        response = self.client.get(reverse("espace_chat"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "espace_chat.html")

    def test_invalid_login_stays_on_login_page(self):
        response = self.client.post(
            reverse("connextion"),
            {"username": "unknown", "password": "incorrect"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nom d'utilisateur ou mot de passe incorrect.")

    def test_signup_password_can_be_used_to_log_in(self):
        password = "A-secure-test-password-42"
        response = self.client.post(
            reverse("inscription"),
            {
                "username": "newuser",
                "email": "newuser@example.com",
                "password1": password,
                "password2": password,
            },
        )

        self.assertRedirects(response, reverse("inscription"))
        login_response = self.client.post(
            reverse("connextion"),
            {"username": "newuser", "password": password},
        )

        self.assertRedirects(login_response, reverse("home"))
