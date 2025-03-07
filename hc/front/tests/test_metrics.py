from django.test.utils import override_settings
from hc.api.models import Check
from hc.test import BaseTestCase


class MetricsTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        self.check = Check(project=self.project, name="Alice Was Here")
        self.check.tags = "foo"
        self.check.save()

        key = "R" * 32
        self.url = f"/projects/{self.project.code}/checks/metrics/{key}"

    def test_it_works(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'name="Alice Was Here"')
        self.assertContains(r, 'tags="foo"')
        self.assertContains(r, 'tag="foo"')
        self.assertContains(r, "hc_checks_total 1")

    def test_it_escapes_newline(self):
        self.check.name = "Line 1\nLine2"
        self.check.tags = "A\\C"
        self.check.save()

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Line 1\\nLine2")
        self.assertContains(r, "A\\\\C")

    def test_it_checks_api_key_length(self):
        r = self.client.get(f"{self.url}R")
        self.assertEqual(r.status_code, 400)

    def test_it_checks_api_key(self):
        url = f'/projects/{self.project.code}/checks/metrics/{"X" * 32}'
        r = self.client.get(url)
        self.assertEqual(r.status_code, 403)

    @override_settings(PROMETHEUS_ENABLED=False)
    def test_it_requires_prometheus_enabled(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
