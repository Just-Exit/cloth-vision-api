from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from cloth_vision_api.ports.outbound.weather_cache import WeatherCache

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WeatherSnapshot:
    location: str
    temperature: float
    feels_like: float
    condition: str
    description: str
    precipitation: float
    humidity: int
    wind_speed: float
    observed_at: datetime
    fetched_at: datetime
    is_stale: bool = False


class OpenWeatherMapProvider:
    endpoint = "https://api.openweathermap.org/data/2.5/weather"

    def __init__(
        self,
        *,
        api_key: str,
        latitude: float,
        longitude: float,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.api_key = api_key
        self.latitude = latitude
        self.longitude = longitude
        self._client = client

    async def fetch(self) -> WeatherSnapshot:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=10)
        try:
            response = await client.get(
                self.endpoint,
                params={
                    "lat": self.latitude,
                    "lon": self.longitude,
                    "appid": self.api_key,
                    "units": "metric",
                    "lang": "kr",
                },
            )
            response.raise_for_status()
            return self._snapshot(response.json())
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def _snapshot(payload: dict[str, Any]) -> WeatherSnapshot:
        now = datetime.now(UTC)
        weather = payload.get("weather") or [{}]
        rain = payload.get("rain") or {}
        snow = payload.get("snow") or {}
        return WeatherSnapshot(
            location="서울",
            temperature=float(payload["main"]["temp"]),
            feels_like=float(payload["main"]["feels_like"]),
            condition=str(weather[0].get("main", "unknown")).lower(),
            description=str(weather[0].get("description", "")),
            precipitation=float(rain.get("1h", 0)) + float(snow.get("1h", 0)),
            humidity=int(payload["main"]["humidity"]),
            wind_speed=float((payload.get("wind") or {}).get("speed", 0)),
            observed_at=datetime.fromtimestamp(int(payload["dt"]), UTC),
            fetched_at=now,
        )


class CachedWeatherService:
    def __init__(
        self,
        provider: OpenWeatherMapProvider,
        cache: WeatherCache,
        *,
        refresh_minutes: int = 30,
        max_age_minutes: int = 90,
    ) -> None:
        self.provider = provider
        self.cache = cache
        self.refresh_seconds = max(refresh_minutes, 1) * 60
        self.max_age = timedelta(minutes=max(max_age_minutes, 1))

    async def refresh(self) -> None:
        try:
            cached = self.cache.get()
            if cached and datetime.now(UTC) - cached.fetched_at < timedelta(
                seconds=self.refresh_seconds
            ):
                return
            self.cache.save(await self.provider.fetch())
        except Exception:
            # Some HTTP errors include the request URL, which contains the API key.
            logger.warning("weather refresh failed; retaining cached snapshot")

    async def run(self) -> None:
        while True:
            await self.refresh()
            await asyncio.sleep(self.refresh_seconds)

    def get(self) -> WeatherSnapshot | None:
        snapshot = self.cache.get()
        if not snapshot:
            return None
        stale = datetime.now(UTC) - snapshot.fetched_at > self.max_age
        return replace(snapshot, is_stale=stale)
