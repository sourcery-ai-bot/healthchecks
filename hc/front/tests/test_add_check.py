from hc.api.models import Check
from hc.test import BaseTestCase


class AddCheckTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.url = f"/projects/{self.project.code}/checks/add/"
        self.redirect_url = f"/projects/{self.project.code}/checks/"

    def test_it_works(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)

        check = Check.objects.get()
        self.assertEqual(check.project, self.project)

        redirect_url = f"/checks/{check.code}/details/?new"
        self.assertRedirects(r, redirect_url)

    def test_team_access_works(self):
        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.url)

        check = Check.objects.get()
        # Added by bob, but should belong to alice (bob has team access)
        self.assertEqual(check.project, self.project)

    def test_it_rejects_get(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_requires_rw_access(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 403)

    def test_it_obeys_check_limit(self):
        self.profile.check_limit = 0
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 400)
