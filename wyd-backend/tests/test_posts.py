from typing import Literal, assert_never

import httpx
from pytest import Subtests, mark

from app.core.constants import AllowedPostsVisibility
from tests.helpers import ClientFactory, LoginUser, UserResponse


@mark.parametrize(
    "block_direction",
    [
        ("owner_blocked"),
        ("blocked_owner"),
    ],
)
@mark.parametrize(
    "visibility_setting, expected_status_code_get, expected_status_code_patch_delete",
    [("everybody", 200, 403), ("logged-in", 404, 403), ("nobody", 404, 404)],
)
async def test_posts_methods(
    subtests: Subtests,
    login: LoginUser,
    create_client: ClientFactory,
    block_direction: str,
    visibility_setting: AllowedPostsVisibility,
    expected_status_code_get: int,
    expected_status_code_patch_delete: int,
) -> None:
    # User Creations
    owner = await login(username="Owner123", email="owner@example.com")
    stranger = await login(username="Stranger123", email="stranger@example.com")
    blocked_user = await login(username="Blocked123", email="blocked@example.com")
    anonymous = create_client()

    # Post visibility setting
    visibility_body = {"visibility": visibility_setting}
    update_visibility = await owner.client.patch(
        "/v1/users/me/profile", json=visibility_body
    )
    assert update_visibility.status_code == 200
    assert update_visibility.json()["visibility"] == visibility_setting
    # Post Creation
    post = await owner.client.post("/v1/posts/", json={"description": "Ahoj123"})
    assert post.status_code == 201
    post_id = post.json()["id"]
    # Block
    if block_direction == "owner_blocked":
        block = await owner.client.put(f"/v1/users/{blocked_user.username}/block")
        assert block.status_code == 204
    else:
        block = await blocked_user.client.put(f"/v1/users/{owner.username}/block")
        assert block.status_code == 204

    table_data: list[
        tuple[
            UserResponse | httpx.AsyncClient,
            str,
            int,
            Literal["unchanged", "changed", "deleted"],
        ]
    ] = [
        (
            stranger,
            "GET",
            expected_status_code_get if visibility_setting == "nobody" else 200,
            "unchanged",
        ),
        (stranger, "PATCH", expected_status_code_patch_delete, "unchanged"),
        (stranger, "DELETE", expected_status_code_patch_delete, "unchanged"),
        (blocked_user, "GET", 404, "unchanged"),
        (blocked_user, "PATCH", 404, "unchanged"),
        (blocked_user, "DELETE", 404, "unchanged"),
        (anonymous, "GET", expected_status_code_get, "unchanged"),
        (anonymous, "PATCH", 401, "unchanged"),
        (anonymous, "DELETE", 401, "unchanged"),
        (owner, "GET", 200, "unchanged"),
        (owner, "PATCH", 200, "changed"),
        (owner, "DELETE", 204, "deleted"),
    ]

    for client, method, expected_status_code, outcome in table_data:
        with subtests.test(
            msg=f"{
                client.username if isinstance(client, UserResponse) else 'anonymous'
            } {method}",
        ):
            body = None
            if method == "PATCH":
                body = {"description": "ahojda123"}
            if isinstance(client, UserResponse):
                response = await client.client.request(
                    method=method, url=f"/v1/posts/{post_id}", json=body
                )
            else:
                response = await client.request(
                    method=method, url=f"/v1/posts/{post_id}", json=body
                )
            assert response.status_code == expected_status_code

            if method == "PATCH" or method == "DELETE":
                refetch = await owner.client.request(
                    method="GET", url=f"/v1/posts/{post_id}"
                )
                if outcome == "unchanged":
                    assert refetch.json() == post.json()
                elif outcome == "changed":
                    assert body
                    assert refetch.json()["description"] == body["description"]
                elif outcome == "deleted":
                    assert refetch.status_code == 404
                else:
                    assert_never(outcome)
