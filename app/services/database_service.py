from sqlalchemy.orm import Session

from app.models.location import Location
from app.models.weather_record import WeatherRecord


def get_or_create_location(
    db: Session,
    name: str,
    latitude: float,
    longitude: float,
) -> Location:
    location = (
        db.query(Location)
        .filter(
            Location.latitude == latitude,
            Location.longitude == longitude,
        )
        .first()
    )

    if location:
        return location

    location = Location(
        name=name,
        latitude=latitude,
        longitude=longitude,
    )

    db.add(location)
    db.commit()
    db.refresh(location)

    return location


def save_weather_record(
    db: Session,
    location: Location,
    temperature: float,
    feels_like: float,
    humidity: int,
    wind_speed: float,
    rain_probability: int,
    condition: str,
    is_day: int,
) -> WeatherRecord:
    record = WeatherRecord(
        location_id=location.id,
        temperature=temperature,
        feels_like=feels_like,
        humidity=humidity,
        wind_speed=wind_speed,
        rain_probability=rain_probability,
        condition=condition,
        is_day=is_day,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record