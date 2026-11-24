from app.core.constants import ACCESS_COOKIE_NAME
from tests.helpers import ClientFactory, LoginUser


async def test_register(create_client: ClientFactory) -> None:
    client = create_client()
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
    assert user.client.cookies.get(ACCESS_COOKIE_NAME)


async def test_logout(login: LoginUser) -> None:
    user = await login(username="ahojda123", email="vojta@example.com")
    client = user.client
    logout = await client.post("/v1/auth/logout")
    assert logout.status_code == 200
    me = await client.get("/v1/users/me")
    assert me.status_code == 401
