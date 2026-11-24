from uuid import uuid7

import pytest
from httpx import AsyncClient

from tests.helpers import LoginUser


@pytest.mark.parametrize(
    "schema_field",
    [
        ({"is_active": True}),
        ({"email": "tadeas@example.com"}),
        ({"id": str(uuid7())}),
        ({"hashed_password": "secret123123abc"}),
    ],
)
async def test_user_patch_mass_assignment(
    client: AsyncClient,
    login: LoginUser,
    schema_field: dict[str, str | bool],
) -> None:
    await login(username="vojta123", email="vojta@example.com")

    user_before_patch = await client.get("/v1/users/me")
    assert user_before_patch.status_code == 200

    patched_user = await client.patch(
        "/v1/users/me", json={"username": "ahojda123", **schema_field}
    )
    assert patched_user.status_code == 422
    user_after_patch = await client.get("/v1/users/me")
    assert user_after_patch.status_code == 200

    assert user_before_patch.json() == user_after_patch.json()
