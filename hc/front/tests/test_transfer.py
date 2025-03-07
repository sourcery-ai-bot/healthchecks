from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class TransferTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.check = Check.objects.create(project=self.bobs_project)
        self.url = f"/checks/{self.check.code}/transfer/"

    def test_it_serves_form(self):
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Transfer to Another Project")

    def test_it_works(self):
        self.client.login(username="bob@example.org", password="password")
        payload = {"project": self.project.code}
        r = self.client.post(self.url, payload, follow=True)
        self.assertRedirects(r, f"/checks/{self.check.code}/details/")
        self.assertContains(r, "Check transferred successfully")

        check = Check.objects.get()
        self.assertEqual(check.project, self.project)

    def test_it_obeys_check_limit(self):
        # Alice's projects cannot accept checks due to limits:
        self.profile.check_limit = 0
        self.profile.save()

        self.client.login(username="bob@example.org", password="password")
        payload = {"project": self.project.code}
        r = self.client.post(self.url, payload)
        self.assertEqual(r.status_code, 400)

    def test_it_reassigns_channels(self):
        alices_mail = Channel.objects.create(kind="email", project=self.project)

        bobs_mail = Channel.objects.create(kind="email", project=self.bobs_project)

        self.check.channel_set.add(bobs_mail)

        self.client.login(username="bob@example.org", password="password")
        payload = {"project": self.project.code}
        self.client.post(self.url, payload)

        # alices_mail should be the only assigned channel:
        self.assertEqual(self.check.channel_set.get(), alices_mail)

    def test_it_checks_check_ownership(self):
        self.client.login(username="charlie@example.org", password="password")

        # Charlie tries to transfer Alice's check into his project
        payload = {"project": self.charlies_project.code}
        r = self.client.post(self.url, payload)
        self.assertEqual(r.status_code, 404)

    def test_it_checks_project_access(self):
        self.client.login(username="alice@example.org", password="password")

        # Alice tries to transfer her check into Charlie's project
        payload = {"project": self.charlies_project.code}
        r = self.client.post(self.url, payload)
        self.assertEqual(r.status_code, 404)

    def test_it_requires_rw_access(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        payload = {"project": self.project.code}

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, payload)
        self.assertEqual(r.status_code, 403)
