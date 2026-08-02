"""Unit tests for the core app: health endpoint and the provider seam."""

from django.test import TestCase
from rest_framework.test import APIClient

from core.providers.base import Provider, ProviderRegistry, ProviderResult


class HealthEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_ok(self):
        resp = self.client.get("/api/health/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")
        self.assertEqual(resp.json()["service"], "lifepilot-ai")


class ProviderRegistryTests(TestCase):
    def test_mock_is_not_live_by_default(self):
        result = ProviderResult(data={"x": 1})
        self.assertFalse(result.is_live)
        self.assertEqual(result.source, "mock")

    def test_register_and_get(self):
        reg = ProviderRegistry()
        mock = Provider(name="email", fetch=lambda **_: ProviderResult(data=[]))
        reg.register(mock)
        self.assertIs(reg.get("email"), mock)
        self.assertFalse(reg.is_live("email"))
        self.assertEqual(reg.names(), ["email"])

    def test_real_provider_swaps_in_under_same_name(self):
        # P2/P3 registers a live provider under the same name; callers unchanged.
        reg = ProviderRegistry()
        reg.register(Provider(name="email", fetch=lambda **_: ProviderResult(data=[])))
        reg.register(
            Provider(
                name="email",
                fetch=lambda **_: ProviderResult(data=[1], is_live=True, source="gmail"),
                is_live=True,
            )
        )
        self.assertTrue(reg.is_live("email"))
        self.assertEqual(reg.get("email").fetch().source, "gmail")

    def test_unknown_provider_raises(self):
        reg = ProviderRegistry()
        with self.assertRaises(KeyError):
            reg.get("nope")
