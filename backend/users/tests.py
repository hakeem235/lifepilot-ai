"""Unit tests for Clerk JWT auth and /api/me/ (Issue 8.1).

Tokens are signed with a locally-generated RSA key and `get_signing_key` is
patched, so verification logic (RS256, issuer, expiry, claim requirements,
profile bootstrap) is exercised without network access to the Clerk JWKS.
"""

from datetime import datetime, timedelta, timezone
from unittest import mock

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from users.models import UserProfile, UserSettings

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC_KEY = _PRIVATE_KEY.public_key()
ISSUER = "https://sure-alien-36.clerk.accounts.dev"


def make_token(sub="user_test_1", issuer=ISSUER, ttl_minutes=5, **extra):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "iss": issuer,
        "iat": now,
        "exp": now + timedelta(minutes=ttl_minutes),
        **extra,
    }
    return jwt.encode(payload, _PRIVATE_KEY, algorithm="RS256")


@override_settings(CLERK_ISSUER=ISSUER)
@mock.patch("users.authentication.get_signing_key", return_value=_PUBLIC_KEY)
class ClerkAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def auth(self, token):
        return self.client.get("/api/me/", HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_me_rejects_missing_token(self, _key):
        resp = self.client.get("/api/me/")
        self.assertEqual(resp.status_code, 401)

    def test_me_rejects_garbage_token(self, _key):
        resp = self.auth("not-a-jwt")
        self.assertEqual(resp.status_code, 401)

    def test_me_rejects_expired_token(self, _key):
        resp = self.auth(make_token(ttl_minutes=-10))
        self.assertEqual(resp.status_code, 401)

    def test_me_rejects_wrong_issuer(self, _key):
        resp = self.auth(make_token(issuer="https://evil.example.com"))
        self.assertEqual(resp.status_code, 401)

    def test_me_rejects_hs256_signature(self, _key):
        # Alg-confusion guard: an HS256 token signed with a shared string must
        # not pass RS256-only verification.
        now = datetime.now(timezone.utc)
        forged = jwt.encode(
            {"sub": "user_forged", "iss": ISSUER, "iat": now, "exp": now + timedelta(minutes=5)},
            "shared-secret",
            algorithm="HS256",
        )
        resp = self.auth(forged)
        self.assertEqual(resp.status_code, 401)

    def test_valid_token_bootstraps_profile_and_settings(self, _key):
        resp = self.auth(make_token(email="a@b.co", name="Ahmed"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["email"], "a@b.co")
        profile = UserProfile.objects.get(auth_id="user_test_1")
        self.assertEqual(profile.display_name, "Ahmed")
        self.assertEqual(profile.avatar_initial, "A")
        self.assertTrue(UserSettings.objects.filter(user=profile).exists())

    def test_null_claims_bootstrap_cleanly(self, _key):
        # Clerk claim templates emit JSON null for absent values (e.g. a user
        # with no full name). Regression: this must not 500 on the not-null
        # display_name column (caught live in the 8.1 E2E).
        resp = self.auth(make_token(email="noname@b.co", name=None))
        self.assertEqual(resp.status_code, 200)
        profile = UserProfile.objects.get(auth_id="user_test_1")
        self.assertEqual(profile.display_name, "")
        self.assertEqual(profile.avatar_initial, "N")

    def test_repeat_requests_reuse_profile(self, _key):
        self.auth(make_token())
        self.auth(make_token())
        self.assertEqual(UserProfile.objects.filter(auth_id="user_test_1").count(), 1)

    def test_me_patch_updates_theme(self, _key):
        resp = self.client.patch(
            "/api/me/",
            {"theme": "dark"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {make_token()}",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["theme"], "dark")

    def test_health_stays_public(self, _key):
        resp = self.client.get("/api/health/")
        self.assertEqual(resp.status_code, 200)
