from __future__ import annotations

import logging
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from cloth_vision_api.config import Settings
from cloth_vision_api.main import create_app


def image_bytes(color: tuple[int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (256, 256), color).save(buffer, format="PNG")
    return buffer.getvalue()


def make_test_settings(tmp_path) -> Settings:
    return Settings(
        app_env="test",
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        upload_dir=tmp_path / "uploads",
        jwt_secret_key="test-secret-key-with-at-least-32-characters",
    )


def signup(client: TestClient, email: str = "user@example.com") -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": "demo-password",
            "nickname": "tester",
        },
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health_auth_and_item_workflow(tmp_path) -> None:
    app = create_app(make_test_settings(tmp_path))
    with TestClient(app) as client:
        health = client.get("/api/v1/health")
        assert health.json() == {"status": "ok", "environment": "test"}
        headers = signup(client)

        me = client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == "user@example.com"

        closet = client.post(
            "/api/v1/closets",
            json={"name": "내 옷장"},
            headers=headers,
        )
        assert closet.status_code == 201
        closet_id = closet.json()["id"]

        item = client.post(
            f"/api/v1/closets/{closet_id}/items",
            data={"category": "top"},
            files={"image": ("shirt.png", image_bytes((30, 80, 180)), "image/png")},
            headers=headers,
        )
        assert item.status_code == 201
        assert item.json()["status"] == "ready"
        assert item.json()["category"] == "top"
        assert item.json()["color_name"] == "blue"
        assert item.json()["image_url"].endswith(f"/items/{item.json()['id']}/image")

        listed = client.get(f"/api/v1/closets/{closet_id}/items", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        item_id = item.json()["id"]
        image = client.get(item.json()["image_url"], headers=headers)
        assert image.status_code == 200
        assert image.headers["content-type"] == "image/png"
        assert image.content == image_bytes((30, 80, 180))

        updated = client.patch(
            f"/api/v1/items/{item_id}",
            json={
                "style_tags": ["classic"],
                "season_tags": ["spring"],
                "materials": [{"name": "cotton", "source": "user_confirmed"}],
                "colors": [
                    {"display_hex": "#1E50B4", "color_name": "blue", "ratio": 1.0}
                ],
                "user_attributes": {"pattern": "solid", "fit": "regular"},
            },
            headers=headers,
        )
        assert updated.status_code == 200
        assert updated.json()["style_tags"] == ["classic"]
        assert updated.json()["materials"][0]["name"] == "cotton"
        assert updated.json()["colors"][0]["display_hex"] == "#1E50B4"

        same_category = client.post(
            f"/api/v1/closets/{closet_id}/items",
            data={"category": "top"},
            files={"image": ("sweater.png", image_bytes((200, 200, 200)), "image/png")},
            headers=headers,
        )
        assert same_category.status_code == 201

        different_category = client.post(
            f"/api/v1/closets/{closet_id}/items",
            data={"category": "bottom"},
            files={"image": ("pants.png", image_bytes((20, 20, 20)), "image/png")},
            headers=headers,
        )
        assert different_category.status_code == 201

        recommendations = client.get(
            f"/api/v1/items/{item_id}/recommendations", headers=headers
        )
        assert recommendations.status_code == 200
        assert [result["target_item_id"] for result in recommendations.json()] == [
            different_category.json()["id"]
        ]


def test_access_log_and_request_id(tmp_path, caplog) -> None:
    settings = make_test_settings(tmp_path)
    settings.run_database_migrations = False
    app = create_app(settings)
    with caplog.at_level(logging.INFO, logger="cloth_vision_api.access"):
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/health", headers={"X-Request-ID": "req_test_request"}
            )

    assert response.headers["X-Request-ID"] == "req_test_request"
    assert any(
        "GET /api/v1/health status=200" in record.message
        and "request_id=req_test_request" in record.message
        for record in caplog.records
    )


def test_rejects_invalid_image(tmp_path) -> None:
    app = create_app(make_test_settings(tmp_path))
    with TestClient(app) as client:
        headers = signup(client, "image@example.com")
        closet_id = client.post(
            "/api/v1/closets",
            json={"name": "main"},
            headers=headers,
        ).json()["id"]
        response = client.post(
            f"/api/v1/closets/{closet_id}/items",
            files={"image": ("bad.txt", b"not an image", "text/plain")},
            headers=headers,
        )
        assert response.status_code == 422
        assert response.json()["code"] == "InvalidImageError"


def test_login_and_rejects_missing_authentication(tmp_path) -> None:
    app = create_app(make_test_settings(tmp_path))
    with TestClient(app) as client:
        signup(client, "login@example.com")

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "demo-password"},
        )
        assert login.status_code == 200
        assert login.json()["token_type"] == "bearer"

        invalid = client.post(
            "/api/v1/auth/login",
            json={"email": "login@example.com", "password": "wrong-password"},
        )
        assert invalid.status_code == 401

        unauthenticated = client.get("/api/v1/closets")
        assert unauthenticated.status_code == 401
