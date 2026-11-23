from httpx import AsyncClient

from tests.helpers import LoginUser


async def test_register(client: AsyncClient) -> None:
    created_user = await client.post(
        url="/v1/auth/register",
        json={
            "email": "vojta@example.com",
            "password": "vojtavojta123",
            "username": "Vojtaskos123",
        },
    )
    assert created_user.status_code == 201
    data = created_user.json()
    assert data.keys() == {"id", "created_at", "username"}
    assert data["username"] == "Vojtaskos123"


async def test_login(login: LoginUser) -> None:
    user = await login(
        username="ahojda123", password="secret123123", email="vojta@example.com"
    )
    assert user.username == "ahojda123"
    assert user.cookie
