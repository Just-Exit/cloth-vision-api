from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from cloth_vision_api.adapters.outbound.database.orm.base import Base


class WeatherCacheRow(Base):
    __tablename__ = "weather_cache"

    location_key: Mapped[str] = mapped_column(String(80), primary_key=True)
    location: Mapped[str] = mapped_column(String(80))
    provider: Mapped[str] = mapped_column(String(40))
    temperature: Mapped[float] = mapped_column(Float)
    feels_like: Mapped[float] = mapped_column(Float)
    condition: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(String(200))
    precipitation: Mapped[float] = mapped_column(Float)
    humidity: Mapped[int] = mapped_column(Integer)
    wind_speed: Mapped[float] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
