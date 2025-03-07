from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase


class AddPdTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_pd/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Paste the Integration Key down below")

    def test_it_works(self):
        # Integration key is 32 characters long
        form = {"value": "12345678901234567890123456789012"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "pd")
        self.assertEqual(c.value, "12345678901234567890123456789012")

    def test_it_trims_whitespace(self):
        form = {"value": "   123456   "}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.value, "123456")

    def test_it_requires_rw_access(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    @override_settings(PD_ENABLED=False)
    def test_it_handles_disabled_integration(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
