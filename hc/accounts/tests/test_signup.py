from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from hc.accounts.models import Profile, Project
from hc.api.models import Channel, Check
from django.conf import settings


class SignupTestCase(TestCase):
    @override_settings(USE_PAYMENTS=False)
    def test_it_sends_link(self):
        form = {"identity": "alice@example.org"}

        r = self.client.post("/accounts/signup/", form)
        self.assertContains(r, "Account created")
        self.assertIn("auto-login", r.cookies)

        # An user should have been created
        user = User.objects.get()

        # A profile should have been created
        profile = Profile.objects.get()
        self.assertEqual(profile.sms_limit, 500)
        self.assertEqual(profile.call_limit, 500)

        # And email sent
        self.assertEqual(len(mail.outbox), 1)
        subject = f"Log in to {settings.SITE_NAME}"
        self.assertEqual(mail.outbox[0].subject, subject)

        # A project should have been created
        project = Project.objects.get()
        self.assertEqual(project.owner, user)
        self.assertEqual(project.badge_key, user.username)

        # And check should be associated with the new user
        check = Check.objects.get()
        self.assertEqual(check.name, "My First Check")
        self.assertEqual(check.project, project)

        # A channel should have been created
        channel = Channel.objects.get()
        self.assertEqual(channel.project, project)

    @override_settings(USE_PAYMENTS=True)
    def test_it_sets_high_limits(self):
        form = {"identity": "alice@example.org"}

        self.client.post("/accounts/signup/", form)

        # A profile should have been created
        profile = Profile.objects.get()
        self.assertEqual(profile.sms_limit, 5)
        self.assertEqual(profile.call_limit, 0)

    @override_settings(REGISTRATION_OPEN=False)
    def test_it_obeys_registration_open(self):
        form = {"identity": "dan@example.org"}

        r = self.client.post("/accounts/signup/", form)
        self.assertEqual(r.status_code, 403)

    def test_it_ignores_case(self):
        form = {"identity": "ALICE@EXAMPLE.ORG"}
        self.client.post("/accounts/signup/", form)

        # There should be exactly one user:
        q = User.objects.filter(email="alice@example.org")
        self.assertTrue(q.exists)

    def test_it_checks_for_existing_users(self):
        alice = User(username="alice", email="alice@example.org")
        alice.save()

        form = {"identity": "alice@example.org"}
        r = self.client.post("/accounts/signup/", form)
        self.assertContains(r, "already exists")

    def test_it_checks_syntax(self):
        form = {"identity": "alice at example org"}
        r = self.client.post("/accounts/signup/", form)
        self.assertContains(r, "Enter a valid email address")

    def test_it_checks_length(self):
        aaa = "a" * 300
        form = {"identity": f"alice+{aaa}@example.org"}
        r = self.client.post("/accounts/signup/", form)
        self.assertContains(r, "Address is too long.")

        self.assertFalse(User.objects.exists())
