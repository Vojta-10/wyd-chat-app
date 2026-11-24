from tests.helpers import ClientFactory


async def test_dummy(create_client: ClientFactory) -> None:
    client = create_client()
    response = await client.get("/")
    assert response.status_code == 200
