from httpx import AsyncClient


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
