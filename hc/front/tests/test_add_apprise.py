from hc.api.models import Channel
from hc.test import BaseTestCase
from django.test.utils import override_settings


@override_settings(APPRISE_ENABLED=True)
class AddAppriseTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_apprise/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Integration Settings", status_code=200)

    def test_it_works(self):
        form = {"url": "json://example.org"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "apprise")
        self.assertEqual(c.value, "json://example.org")
        self.assertEqual(c.project, self.project)

    @override_settings(APPRISE_ENABLED=False)
    def test_it_requires_client_id(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_requires_rw_access(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)
