from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(SIGNAL_CLI_ENABLED=True)
class AddSignalTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_signal/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Get a Signal message")

    def test_it_creates_channel(self):
        form = {
            "label": "My Phone",
            "phone": "+1234567890",
            "down": "true",
            "up": "true",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "signal")
        self.assertEqual(c.phone_number, "+1234567890")
        self.assertEqual(c.name, "My Phone")
        self.assertTrue(c.signal_notify_down)
        self.assertTrue(c.signal_notify_up)
        self.assertEqual(c.project, self.project)

    def test_it_obeys_up_down_flags(self):
        form = {"label": "My Phone", "phone": "+1234567890"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertFalse(c.signal_notify_down)
        self.assertFalse(c.signal_notify_up)

    @override_settings(SIGNAL_CLI_ENABLED=False)
    def test_it_handles_disabled_integration(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_requires_rw_access(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)
