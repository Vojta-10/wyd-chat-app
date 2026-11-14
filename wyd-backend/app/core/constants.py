from typing import Final, Literal, TypedDict

ISSUER = "wyd api"
ACCESS_TOKEN_AUDIENCE = "access_token"
ACCESS_COOKIE_NAME = "__Host-bearer-token"
AllowedThemes = Literal["light", "dark", "system"]


class CookieOptions(TypedDict):
    secure: bool
    httponly: bool
    samesite: Literal["lax", "strict", "none"]
    path: str


# Shared by set_cookie and delete_cookie so the two can't drift apart.
# __Host- prefix requires: Secure, Path=/, and no Domain.
AUTH_COOKIE_OPTIONS: Final[CookieOptions] = {
    "secure": True,
    "httponly": True,
    "samesite": "strict",
    "path": "/",
}
