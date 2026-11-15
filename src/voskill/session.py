from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from collections.abc import Callable

from .auth_errors import AuthenticationUnavailable
from .authentication import PortalPrincipal


class InvalidSession(ValueError):
    pass


class SessionCodec:
    def __init__(
        self,
        secret: str | bytes,
        *,
        max_age_seconds: int = 1800,
        clock: Callable[[], float] = time.time,
    ) -> None:
        secret_bytes = secret.encode("utf-8") if isinstance(secret, str) else secret
        if len(secret_bytes) < 32:
            raise ValueError("Session signing secret must contain at least 32 bytes")
        if not 60 <= max_age_seconds <= 86400:
            raise ValueError("Session max age must be between 60 and 86400 seconds")
        self._secret = secret_bytes
        self.max_age_seconds = max_age_seconds
        self._clock = clock

    @classmethod
    def from_environment(cls) -> SessionCodec:
        secret = os.environ.get("VOSKILL_SESSION_SECRET", "")
        if len(secret.encode("utf-8")) < 32:
            raise AuthenticationUnavailable("Session signing secret is missing or too short")
        try:
            max_age = int(os.environ.get("VOSKILL_SESSION_MAX_AGE", "1800"))
            return cls(secret, max_age_seconds=max_age)
        except ValueError as error:
            raise AuthenticationUnavailable("Session max age configuration is invalid") from error

    def encode(self, principal: PortalPrincipal) -> str:
        now = int(self._clock())
        payload = json.dumps(
            {
                "actor_id": principal.actor_id,
                "can_view": principal.can_view,
                "can_edit": principal.can_edit,
                "expires_at": now + self.max_age_seconds,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        encoded_payload = base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")
        signature = hmac.new(self._secret, encoded_payload.encode("ascii"), hashlib.sha256).digest()
        encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
        return f"{encoded_payload}.{encoded_signature}"

    def decode(self, token: str) -> PortalPrincipal:
        try:
            encoded_payload, encoded_signature = token.split(".", maxsplit=1)
            signature = _decode_urlsafe(encoded_signature)
            expected = hmac.new(self._secret, encoded_payload.encode("ascii"), hashlib.sha256).digest()
            if not hmac.compare_digest(signature, expected):
                raise InvalidSession("Invalid session signature")
            payload = json.loads(_decode_urlsafe(encoded_payload))
            actor_id = payload["actor_id"]
            can_view = payload["can_view"]
            can_edit = payload["can_edit"]
            expires_at = payload["expires_at"]
            if (
                not isinstance(actor_id, str)
                or not actor_id
                or actor_id != actor_id.strip().upper()
                or not isinstance(can_view, bool)
                or not isinstance(can_edit, bool)
                or not can_view
                or (can_edit and not can_view)
                or type(expires_at) is not int
                or expires_at <= int(self._clock())
                or expires_at > int(self._clock()) + self.max_age_seconds
            ):
                raise InvalidSession("Invalid or expired session")
        except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            if isinstance(error, InvalidSession):
                raise
            raise InvalidSession("Invalid session") from error

        return PortalPrincipal(actor_id, "", None, can_view, can_edit)


def _decode_urlsafe(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
