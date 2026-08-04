"""Clerk JWT authentication for DRF (Issue 8.1).

The Expo app obtains a session JWT from Clerk and sends it as a Bearer token.
We verify it server-side against the instance's public JWKS (RS256) — no shared
secret involved — check the issuer, then resolve the `sub` claim (Clerk user id)
to a local UserProfile, creating it on first sight (bootstrap-on-first-request,
so no separate registration endpoint or webhook is needed for MVP).

Structure mirrors ComplianceAI's DRF authentication class; the signing-key
lookup goes through `get_signing_key()` so tests can substitute a local RSA key
without network access.
"""

from functools import lru_cache

import jwt
from django.conf import settings
from rest_framework import authentication, exceptions

from .models import UserProfile, UserSettings

ALGORITHM = "RS256"


@lru_cache(maxsize=1)
def _jwks_client() -> jwt.PyJWKClient:
    if not settings.CLERK_JWKS_URL:
        raise exceptions.AuthenticationFailed("Clerk is not configured (CLERK_JWKS_URL unset).")
    return jwt.PyJWKClient(settings.CLERK_JWKS_URL, cache_keys=True, lifespan=3600)


def get_signing_key(token: str):
    """Resolve the RS256 public key for this token from the Clerk JWKS."""
    return _jwks_client().get_signing_key_from_jwt(token).key


class ClerkJWTAuthentication(authentication.BaseAuthentication):
    """Verify a Clerk-issued Bearer token and resolve it to a UserProfile."""

    def authenticate_header(self, request):
        # Advertise the scheme so DRF returns 401 (not 403) on missing/invalid
        # credentials — the app keys off 401 to send the user to login.
        return "Bearer"

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.removeprefix("Bearer ").strip()
        try:
            key = get_signing_key(token)
            claims = jwt.decode(
                token,
                key,
                algorithms=[ALGORITHM],
                issuer=settings.CLERK_ISSUER or None,
                options={"require": ["exp", "iat", "sub"], "verify_iss": bool(settings.CLERK_ISSUER)},
                leeway=60,
            )
        except exceptions.AuthenticationFailed:
            raise
        except jwt.PyJWTError as exc:
            raise exceptions.AuthenticationFailed(f"Invalid session token: {exc}") from exc

        # Clerk claim templates render absent values as JSON null — coerce to ""
        # so not-null text columns don't reject the bootstrap row.
        email = claims.get("email") or ""
        name = claims.get("name") or ""
        profile, created = UserProfile.objects.get_or_create(
            auth_id=claims["sub"],
            defaults={
                "email": email,
                "display_name": name,
                "avatar_initial": (name or email or "?")[:1].upper(),
            },
        )
        if created:
            UserSettings.objects.create(user=profile)

        return (profile, token)
