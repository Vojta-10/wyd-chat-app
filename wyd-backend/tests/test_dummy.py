from httpx import AsyncClient


async def test_dummy(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
