import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from ...authentication import (
    AuthenticationFailed,
    AuthenticationService,
    AuthenticationUnavailable,
    PortalPrincipal,
)
from ...session import SessionCodec
from ..dependencies import get_authentication_service, get_session_codec, get_session_principal
from ..schemas import AuthenticatedPrincipalResponse, AuthenticationPayload

router = APIRouter(prefix="/auth")
SESSION_COOKIE_NAME = "voskill_session"


def _secure_cookie() -> bool:
    return os.environ.get("VOSKILL_SESSION_COOKIE_SECURE", "1").strip() == "1"


@router.post("/login", status_code=204)
def login(
    payload: AuthenticationPayload,
    response: Response,
    service: Annotated[AuthenticationService, Depends(get_authentication_service)],
    codec: Annotated[SessionCodec | None, Depends(get_session_codec)],
) -> None:
    if codec is None:
        raise HTTPException(
            status_code=503,
            detail={"code": "AUTHENTICATION_UNAVAILABLE"},
        )
    try:
        principal = service.authenticate(payload.username, payload.password)
    except AuthenticationFailed as error:
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS"}) from error
    except AuthenticationUnavailable as error:
        raise HTTPException(
            status_code=503,
            detail={"code": "AUTHENTICATION_UNAVAILABLE"},
        ) from error

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=codec.encode(principal),
        max_age=codec.max_age_seconds,
        path="/",
        secure=_secure_cookie(),
        httponly=True,
        samesite="lax",
    )


@router.get("/me", response_model=AuthenticatedPrincipalResponse)
def current_principal(
    principal: Annotated[PortalPrincipal, Depends(get_session_principal)],
) -> dict[str, object]:
    return {
        "actor_id": principal.actor_id,
        "can_view": principal.can_view,
        "can_edit": principal.can_edit,
    }


@router.post("/logout", status_code=204)
def logout() -> Response:
    response = Response(status_code=204)
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=_secure_cookie(),
        httponly=True,
        samesite="lax",
    )
    return response
