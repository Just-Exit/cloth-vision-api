from __future__ import annotations

import logging
from io import BytesIO

from cloth_vision_core import AnalysisPipeline, PillowImageProcessor
from cloth_vision_core.providers import MockVisionProvider
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
        openai_api_key="",
        openweather_api_key="",
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
    app.state.closet_service.analyzer = AnalysisPipeline(
        PillowImageProcessor(), MockVisionProvider()
    )
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
        assert item.json()["color_name"] is None
        assert item.json()["image_url"].endswith(f"/items/{item.json()['id']}/image")
        assert item.json()["images"]["thumbnail_url"].endswith(
            f"/items/{item.json()['id']}/images/thumbnail"
        )

        listed = client.get(f"/api/v1/closets/{closet_id}/items", headers=headers)
        assert listed.status_code == 200
        assert len(listed.json()) == 1

        item_id = item.json()["id"]
        image = client.get(item.json()["image_url"], headers=headers)
        assert image.status_code == 200
        assert image.headers["content-type"] == "image/png"
        assert image.content == image_bytes((30, 80, 180))
        thumbnail = client.get(item.json()["images"]["thumbnail_url"], headers=headers)
        assert thumbnail.status_code == 200
        # Segmentation is disabled in this test, so derived image routes use the original.
        assert thumbnail.headers["content-type"] == "image/png"
        assert thumbnail.content == image.content

        updated = client.patch(
            f"/api/v1/items/{item_id}",
            json={
                "style_tags": ["classic"],
                "season_tags": ["spring"],
                "materials": [{"name": "cotton", "source": "user_confirmed"}],
                "colors": [{"display_hex": "#1E50B4", "color_name": "blue", "ratio": 1.0}],
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

        recommendations = client.get(f"/api/v1/items/{item_id}/recommendations", headers=headers)
        assert recommendations.status_code == 200
        assert [result["target_item_id"] for result in recommendations.json()] == [
            different_category.json()["id"]
        ]

        outfits = client.post(
            f"/api/v1/closets/{closet_id}/outfit-recommendations",
            json={"limit": 3},
            headers=headers,
        )
        assert outfits.status_code == 200
        assert len(outfits.json()["outfits"]) == 2
        assert outfits.json()["missing_categories"] == []
        assert all(
            {item["category"] for item in outfit["items"]} == {"top", "bottom"}
            for outfit in outfits.json()["outfits"]
        )
        assert all(
            item["thumbnail_url"].endswith("/images/thumbnail")
            for outfit in outfits.json()["outfits"]
            for item in outfit["items"]
        )
        assert all(outfit["reason"] for outfit in outfits.json()["outfits"])
        assert all(len(outfit["reason"]) <= 80 for outfit in outfits.json()["outfits"])
        outfit_image = client.get(outfits.json()["outfits"][0]["image_url"], headers=headers)
        assert outfit_image.status_code == 200
        assert outfit_image.headers["content-type"] == "image/webp"
        another_closet = client.post("/api/v1/closets", json={"name": "다른 옷장"}, headers=headers)
        wrong_closet_url = outfits.json()["outfits"][0]["image_url"].replace(
            closet_id, another_closet.json()["id"]
        )
        assert client.get(wrong_closet_url, headers=headers).status_code == 404
        assert (
            client.post(
                "/api/v1/outfit-recommendations",
                json={"closet_id": closet_id, "limit": 3},
                headers=headers,
            ).status_code
            == 404
        )

        analytics = client.get(
            f"/api/v1/closets/{closet_id}/analytics",
            headers=headers,
        )
        assert analytics.status_code == 200
        report = analytics.json()
        assert report["total_items"] == 3
        assert {entry["category"] for entry in report["category_distribution"]} == {
            "top",
            "bottom",
        }
        assert report["color_distribution"][0]["display_hex"] == "#1E50B4"
        assert all(
            entry["category"] not in {"top", "bottom"}
            for entry in report["essential_recommendations"]
        )
        assert "unworn_items" not in report
        assert "cost_per_wear" not in report

        dashboard = client.get(
            f"/api/v1/closets/{closet_id}/dashboard",
            headers=headers,
        )
        assert dashboard.status_code == 200
        home = dashboard.json()
        assert home["nickname"] == "tester"
        assert home["today_outfit"]["image_url"].endswith("/image")
        assert home["closet_summary"]["completeness_score"] == 40
        assert home["closet_summary"]["total_items"] == 3
        assert len(home["recent_items"]) == 3
        assert home["weather"] is None
        assert "monthly_wear_count" not in home


def test_access_log_and_request_id(tmp_path, caplog) -> None:
    settings = make_test_settings(tmp_path)
    settings.run_database_migrations = False
    app = create_app(settings)
    with caplog.at_level(logging.INFO, logger="cloth_vision_api.access"):
        with TestClient(app) as client:
            response = client.get("/api/v1/health", headers={"X-Request-ID": "req_test_request"})

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


def test_marks_item_failed_without_vision_provider(tmp_path) -> None:
    app = create_app(make_test_settings(tmp_path))
    with TestClient(app) as client:
        headers = signup(client, "no-provider@example.com")
        closet_id = client.post("/api/v1/closets", json={"name": "main"}, headers=headers).json()[
            "id"
        ]

        response = client.post(
            f"/api/v1/closets/{closet_id}/items",
            files={"image": ("shirt.png", image_bytes((30, 80, 180)), "image/png")},
            headers=headers,
        )

        assert response.status_code == 201
        assert response.json()["status"] == "failed"
        assert response.json()["color_hex"] is None
        assert response.json()["colors"] == []
        assert response.json()["user_attributes"] == {
            "analysis_warning": "vision_provider_unavailable"
        }


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
