import json
from unittest.mock import patch

from django.core import mail
from hc.api.models import Channel, Notification
from hc.test import BaseTestCase


class SendTestNotificationTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.channel = Channel(kind="email", project=self.project)
        self.channel.email_verified = True
        self.channel.value = "alice@example.org"
        self.channel.save()

        self.url = f"/integrations/{self.channel.code}/test/"

    def test_it_sends_test_email(self):

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {}, follow=True)
        self.assertRedirects(r, self.channels_url)
        self.assertContains(r, "Test notification sent!")

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to[0], "alice@example.org")
        self.assertTrue("X-Status-Url" in email.extra_headers)
        self.assertTrue("List-Unsubscribe" in email.extra_headers)

        # It should create a notification
        n = Notification.objects.get()
        self.assertEqual(n.channel, self.channel)
        self.assertEqual(n.error, "")

    def test_it_clears_channel_last_error(self):
        self.channel.last_error = "Something went wrong"
        self.channel.save()

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, {})

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.last_error, "")

    def test_it_sets_channel_last_error(self):
        self.channel.email_verified = False
        self.channel.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {}, follow=True)

        self.assertContains(r, "Could not send a test notification")
        self.assertContains(r, "Email not verified")

        self.channel.refresh_from_db()
        self.assertEqual(self.channel.last_error, "Email not verified")

    @patch("hc.api.transports.requests.request")
    def test_it_handles_webhooks_with_no_down_url(self, mock_get):
        mock_get.return_value.status_code = 200

        self.channel.kind = "webhook"
        self.channel.value = json.dumps(
            {
                "method_down": "GET",
                "url_down": "",
                "body_down": "",
                "headers_down": {},
                "method_up": "GET",
                "url_up": "http://example-url",
                "body_up": "",
                "headers_up": {},
            }
        )
        self.channel.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {}, follow=True)
        self.assertRedirects(r, self.channels_url)
        self.assertContains(r, "Test notification sent!")

    def test_it_handles_webhooks_with_no_urls(self):
        self.channel.kind = "webhook"
        self.channel.value = json.dumps(
            {
                "method_down": "GET",
                "url_down": "",
                "body_down": "",
                "headers_down": {},
                "method_up": "GET",
                "url_up": "",
                "body_up": "",
                "headers_up": {},
            }
        )
        self.channel.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {}, follow=True)
        self.assertRedirects(r, self.channels_url)
        self.assertContains(r, "Could not send a test notification")

    def test_it_checks_channel_ownership(self):
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.post(self.url, {}, follow=True)
        self.assertEqual(r.status_code, 404)
