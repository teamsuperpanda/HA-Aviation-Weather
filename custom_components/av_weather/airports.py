"""Airport data management for Av Weather integration."""
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

_AIRPORTS_CACHE: dict[str, dict[str, Any]] | None = None


def _load_airports_sync() -> dict[str, dict[str, Any]]:
    """Load airport data from airports.json file (synchronous)."""
    try:
        airports_file = Path(__file__).parent / "airports.json"
        with open(airports_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            _LOGGER.debug("Loaded %d airports from airports.json", len(data))
            return data
    except FileNotFoundError:
        _LOGGER.error("airports.json file not found")
        return {}
    except json.JSONDecodeError as err:
        _LOGGER.error("Failed to parse airports.json: %s", err)
        return {}
    except Exception as err:
        _LOGGER.exception("Unexpected error loading airports.json: %s", err)
        return {}


async def load_airports() -> dict[str, dict[str, Any]]:
    """Load airport data from airports.json file."""
    global _AIRPORTS_CACHE
    
    if _AIRPORTS_CACHE is not None:
        return _AIRPORTS_CACHE
    
    # Run blocking I/O in executor to avoid blocking event loop
    _AIRPORTS_CACHE = await asyncio.to_thread(_load_airports_sync)
    return _AIRPORTS_CACHE


async def get_airport_by_icao(icao: str) -> dict[str, Any] | None:
    """Get airport data by ICAO code."""
    airports = await load_airports()
    return airports.get(icao.upper())


async def validate_icao_code(icao: str) -> bool:
    """Validate that an ICAO code exists in the airport database."""
    return await get_airport_by_icao(icao) is not None





async def format_airport_label(icao: str, airport_data: dict[str, Any] | None = None) -> str:
    """Format an airport for display in the UI."""
    if airport_data is None:
        airport_data = await get_airport_by_icao(icao)
    
    if not airport_data:
        return icao
    
    name = airport_data.get("name", "Unknown")
    city = airport_data.get("city", "")
    country = airport_data.get("country", "")
    iata = airport_data.get("iata", "")
    
    # Format: "ICAO (IATA) - Name, City, Country"
    label_parts = [icao]
    
    if iata:
        label_parts[0] = f"{icao} ({iata})"
    
    location_parts = []
    if name:
        location_parts.append(name)
    if city:
        location_parts.append(city)
    if country:
        location_parts.append(country)
    
    if location_parts:
        label_parts.append(" - ".join(location_parts))
    
    return " - ".join(label_parts)



