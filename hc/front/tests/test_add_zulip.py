from django.test.utils import override_settings
from hc.api.models import Channel
from hc.test import BaseTestCase


def _get_payload(**kwargs):
    return {
        "bot_email": "foo@example.org",
        "api_key": "fake-key",
        "site": "https://example.org",
        "mtype": "stream",
        "to": "general",
    } | kwargs


class AddZulipTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_zulip/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "open-source group chat app")

    def test_it_works(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, _get_payload())
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.kind, "zulip")
        self.assertEqual(c.zulip_bot_email, "foo@example.org")
        self.assertEqual(c.zulip_api_key, "fake-key")
        self.assertEqual(c.zulip_type, "stream")
        self.assertEqual(c.zulip_to, "general")

    def test_it_rejects_bad_email(self):
        payload = _get_payload(bot_email="not@an@email")
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertContains(r, "Invalid file format.")

    def test_it_rejects_missing_api_key(self):
        payload = _get_payload(api_key="")
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertContains(r, "Invalid file format.")

    def test_it_rejects_missing_site(self):
        payload = _get_payload(site="")
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertContains(r, "Invalid file format.")

    def test_it_rejects_malformed_site(self):
        payload = _get_payload(site="not-an-url")
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertContains(r, "Invalid file format.")

    def test_it_rejects_bad_mtype(self):
        payload = _get_payload(mtype="this-should-not-work")
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertEqual(r.status_code, 200)

    def test_it_rejects_missing_stream_name(self):
        payload = _get_payload(to="")
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertContains(r, "This field is required.")

    def test_it_requires_rw_access(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    @override_settings(ZULIP_ENABLED=False)
    def test_it_handles_disabled_integration(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
