from pytest import mark

from tests.helpers import ClientFactory, LoginUser


async def test_create_new_post_not_logged_in(create_client: ClientFactory) -> None:
    client = create_client()
    response = await client.post("/v1/posts/", json={"description": "Not logged in"})
    assert response.status_code == 401


async def test_create_new_post_extra_field_in_body(login: LoginUser) -> None:
    user = await login(username="Vojta123", email="vojta@example.com")
    response = await user.client.post(
        "/v1/posts/", json={"description": "Extra field", "user_id": "123"}
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "extra_forbidden"


@mark.parametrize(
    "description_value, error_type",
    [
        (None, "string_type"),
        ("", "string_too_short"),
        ("      ", "string_too_short"),
        ("a" * 257, "string_too_long"),
        ("ahoj\rhehe", "value_error"),
    ],
)
async def test_create_new_post_invalid_description(
    login: LoginUser, description_value: str | None, error_type: str
) -> None:
    user = await login(username="Vojta123", email="vojta@example.com")
    response = await user.client.post(
        "/v1/posts/", json={"description": description_value}
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == error_type


async def test_create_new_post_description_missing(login: LoginUser) -> None:
    user = await login(username="Vojta123", email="vojta@example.com")
    response = await user.client.post("/v1/posts/", json={})
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "missing"
    assert response.json()["detail"][0]["loc"] == ["body", "description"]


async def test_create_new_post_new_line_normalize(login: LoginUser) -> None:
    user = await login(username="Vojta123", email="vojta@example.com")
    response = await user.client.post(
        "/v1/posts/", json={"description": "ahoj\nahoj\r\nahoj"}
    )
    assert response.status_code == 201
    assert response.json()["description"] == "ahoj\nahoj\nahoj"


async def test_create_new_post(login: LoginUser) -> None:
    user = await login(username="Vojta123", email="vojta@example.com")
    response = await user.client.post("/v1/posts/", json={"description": "a" * 256})
    assert response.status_code == 201
    post = response.json()
    assert post["description"] == "a" * 256
    assert post["author"]["username"] == user.username
    assert post["author"]["display_name"] == user.username
    assert post["like_count"] == 0
    assert post["is_liked"] is False
