import asyncio
from datetime import UTC, datetime

from cloth_vision_api.adapters.outbound.database import (
    SqlAlchemyWeatherCache,
    create_session_factory,
    upgrade_database,
)
from cloth_vision_api.adapters.outbound.weather import (
    CachedWeatherService,
    OpenWeatherMapProvider,
    WeatherSnapshot,
)


class FakeResponse:
    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict:
        return {
            "weather": [{"main": "Clouds", "description": "흐림"}],
            "main": {"temp": 18.2, "feels_like": 17.4, "humidity": 64},
            "wind": {"speed": 2.1},
            "rain": {"1h": 0.4},
            "dt": 1787529600,
        }


class FakeClient:
    def __init__(self) -> None:
        self.params = None

    async def get(self, url: str, *, params: dict) -> FakeResponse:
        self.params = params
        assert "appid" in params
        return FakeResponse()


class FakeCache:
    def __init__(self) -> None:
        self.snapshot = None

    def get(self):
        return self.snapshot

    def save(self, snapshot) -> None:
        self.snapshot = snapshot


def test_refreshes_and_caches_seoul_weather() -> None:
    client = FakeClient()
    provider = OpenWeatherMapProvider(
        api_key="secret", latitude=37.5665, longitude=126.9780, client=client
    )
    cache = FakeCache()
    service = CachedWeatherService(provider, cache)

    asyncio.run(service.refresh())

    weather = service.get()
    assert weather is not None
    assert weather.location == "서울"
    assert weather.temperature == 18.2
    assert weather.condition == "clouds"
    assert weather.precipitation == 0.4
    assert client.params["units"] == "metric"
    assert client.params["lang"] == "kr"
    assert cache.snapshot == weather


def test_database_cache_survives_repository_instances(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'weather.db'}"
    upgrade_database(database_url)
    session_factory = create_session_factory(database_url)
    snapshot = WeatherSnapshot(
        location="서울",
        temperature=24.0,
        feels_like=24.5,
        condition="clear",
        description="맑음",
        precipitation=0.0,
        humidity=45,
        wind_speed=1.2,
        observed_at=datetime.now(UTC),
        fetched_at=datetime.now(UTC),
    )

    SqlAlchemyWeatherCache(session_factory).save(snapshot)
    restored = SqlAlchemyWeatherCache(session_factory).get()

    assert restored is not None
    assert restored.location == "서울"
    assert restored.temperature == 24.0
