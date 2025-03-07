from django.contrib.auth.hashers import make_password
from hc.accounts.models import Credential
from hc.test import BaseTestCase


class CheckTokenTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.profile.token = make_password("secret-token", "login")
        self.profile.save()

        self.checks_url = f"/projects/{self.project.code}/checks/"

    def test_it_shows_form(self):
        r = self.client.get("/accounts/check_token/alice/secret-token/")
        self.assertContains(r, "You are about to log in")

    def test_it_redirects(self):
        r = self.client.post("/accounts/check_token/alice/secret-token/")

        self.assertRedirects(r, self.checks_url)

        # After login, token should be blank
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.token, "")

    def test_it_redirects_already_logged_in(self):
        # Login
        self.client.login(username="alice@example.org", password="password")

        # Login again, when already authenticated
        r = self.client.post("/accounts/check_token/alice/secret-token/")

        self.assertRedirects(r, self.checks_url)

    def test_it_redirects_bad_login(self):
        # Login with a bad token
        url = "/accounts/check_token/alice/invalid-token/"
        r = self.client.post(url, follow=True)
        self.assertRedirects(r, "/accounts/login/")
        self.assertContains(r, "incorrect or expired")

    def test_it_handles_next_parameter(self):
        url = f"/accounts/check_token/alice/secret-token/?next={self.channels_url}"
        r = self.client.post(url)
        self.assertRedirects(r, self.channels_url)

    def test_it_ignores_bad_next_parameter(self):
        url = "/accounts/check_token/alice/secret-token/?next=/evil/"
        r = self.client.post(url)
        self.assertRedirects(r, self.checks_url)

    def test_it_redirects_to_webauthn_form(self):
        Credential.objects.create(user=self.alice, name="Alices Key")

        r = self.client.post("/accounts/check_token/alice/secret-token/")
        self.assertRedirects(
            r, "/accounts/login/two_factor/", fetch_redirect_response=False
        )

        # It should not log the user in yet
        self.assertNotIn("_auth_user_id", self.client.session)

        # Instead, it should set 2fa_user_id in the session
        user_id, email, valid_until = self.client.session["2fa_user"]
        self.assertEqual(user_id, self.alice.id)
