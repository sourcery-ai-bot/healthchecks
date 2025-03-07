from datetime import datetime, timedelta as td
from unittest.mock import patch

from django.utils import timezone
from hc.api.models import Flip, Check, Ping
from hc.test import BaseTestCase


class DetailsTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.check = Check.objects.create(project=self.project)

        ping = Ping.objects.create(owner=self.check)

        # Older MySQL versions don't store microseconds. This makes sure
        # the ping is older than any notifications we may create later:
        ping.created = "2000-01-01T00:00:00+00:00"
        ping.save()

        self.url = f"/checks/{self.check.code}/details/"

    def test_it_works(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "How To Ping", status_code=200)
        # The page should contain timezone strings
        self.assertContains(r, "Europe/Riga")

    def test_it_checks_ownership(self):
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_shows_cron_expression(self):
        self.check.kind = "cron"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Cron Expression", status_code=200)

    def test_it_allows_cross_team_access(self):
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_it_shows_new_check_notice(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(f"{self.url}?new")
        self.assertContains(r, "Your new check is ready!", status_code=200)

    def test_it_hides_actions_from_readonly_users(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)

        self.assertNotContains(r, "edit-name", status_code=200)
        self.assertNotContains(r, "edit-desc")
        self.assertNotContains(r, "Filtering Rules")
        self.assertNotContains(r, "pause-btn")
        self.assertNotContains(r, "Change Schedule")
        self.assertNotContains(r, "Create a Copy&hellip;")
        self.assertNotContains(r, "transfer-btn")
        self.assertNotContains(r, "details-remove-check")

    def test_it_hides_resume_action_from_readonly_users(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.check.status = "paused"
        self.check.manual_resume = True
        self.check.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)

        self.assertNotContains(r, "resume-btn", status_code=200)

    def test_crontab_example_guesses_schedules(self):
        self.client.login(username="alice@example.org", password="password")

        pairs = [
            (td(minutes=1), "* * * * *"),
            (td(minutes=12), "*/12 * * * *"),
            (td(hours=1), "0 * * * *"),
            (td(hours=6), "0 */6 * * *"),
            (td(days=1), "0 0 * * *"),
        ]

        for timeout, expression in pairs:
            self.check.timeout = timeout
            self.check.save()

            r = self.client.get(self.url)
            self.assertContains(r, f"{expression} /your/command.sh")
            self.assertNotContains(r, 'FIXME: replace "* * * * *"')

    def test_crontab_example_handles_unsupported_timeout_values(self):
        self.client.login(username="alice@example.org", password="password")

        self.check.timeout = td(minutes=13)
        self.check.save()

        r = self.client.get(self.url)
        self.assertContains(r, "* * * * * /your/command.sh")
        self.assertContains(r, 'FIXME: replace "* * * * *"')

    @patch("hc.lib.date.timezone.now")
    def test_it_calculates_downtime_summary(self, mock_now):
        mock_now.return_value = datetime(2020, 2, 1, tzinfo=timezone.utc)

        self.check.created = datetime(2019, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        self.check.save()

        # going down on Jan 15, at 12:00
        f1 = Flip(owner=self.check)
        f1.created = datetime(2020, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        f1.old_status = "up"
        f1.new_status = "down"
        f1.save()

        # back up on Jan 15, at 13:00
        f2 = Flip(owner=self.check)
        f2.created = datetime(2020, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
        f2.old_status = "down"
        f2.new_status = "up"
        f2.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Feb. 2020")
        self.assertContains(r, "Jan. 2020")
        self.assertContains(r, "Dec. 2019")

        # The summary for Jan. 2020 should be "1 downtime, 1 hour total"
        self.assertContains(r, "1 downtime, 1 hour total", html=True)

    @patch("hc.lib.date.timezone.now")
    def test_it_handles_months_when_check_did_not_exist(self, mock_now):
        mock_now.return_value = datetime(2020, 2, 1, tzinfo=timezone.utc)

        self.check.created = datetime(2020, 1, 10, 0, 0, 0, tzinfo=timezone.utc)
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Feb. 2020")
        self.assertContains(r, "Jan. 2020")
        self.assertContains(r, "Dec. 2019")

        # The summary for Dec. 2019 should be "–"
        self.assertContains(r, "<td>–</td>", html=True)
