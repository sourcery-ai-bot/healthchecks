from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase


class AddVictorOpsTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_victorops/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "incident management platform")

    def test_it_works(self):
        form = {"value": "http://example.org"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "victorops")
        self.assertEqual(c.value, "http://example.org")
        self.assertEqual(c.project, self.project)

    def test_it_rejects_bad_url(self):
        form = {"value": "not an URL"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertContains(r, "Enter a valid URL")

    def test_it_requires_rw_access(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    @override_settings(VICTOROPS_ENABLED=False)
    def test_it_handles_disabled_integration(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
