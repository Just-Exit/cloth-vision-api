from cloth_vision_api.adapters.outbound.database.orm import WeatherCacheRow
from cloth_vision_api.adapters.outbound.database.repositories.base import SqlAlchemyRepositoryBase
from cloth_vision_api.adapters.outbound.weather import WeatherSnapshot


class SqlAlchemyWeatherCache(SqlAlchemyRepositoryBase):
    location_key = "seoul"

    def get(self) -> WeatherSnapshot | None:
        with self._session() as session:
            row = session.get(WeatherCacheRow, self.location_key)
            if not row:
                return None
            return WeatherSnapshot(
                location=row.location,
                temperature=row.temperature,
                feels_like=row.feels_like,
                condition=row.condition,
                description=row.description,
                precipitation=row.precipitation,
                humidity=row.humidity,
                wind_speed=row.wind_speed,
                observed_at=row.observed_at,
                fetched_at=row.fetched_at,
            )

    def save(self, snapshot: WeatherSnapshot) -> None:
        with self._session() as session:
            session.merge(
                WeatherCacheRow(
                    location_key=self.location_key,
                    location=snapshot.location,
                    provider="openweathermap",
                    temperature=snapshot.temperature,
                    feels_like=snapshot.feels_like,
                    condition=snapshot.condition,
                    description=snapshot.description,
                    precipitation=snapshot.precipitation,
                    humidity=snapshot.humidity,
                    wind_speed=snapshot.wind_speed,
                    observed_at=snapshot.observed_at,
                    fetched_at=snapshot.fetched_at,
                )
            )
