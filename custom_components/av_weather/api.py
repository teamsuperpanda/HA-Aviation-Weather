"""API client for AviationWeather.gov."""
import asyncio
import logging
from typing import Any

import aiohttp
from aiohttp.client_exceptions import ClientConnectorError, ClientError

from .const import METAR_API_URL, TAF_API_URL, CUSTOM_USER_AGENT

_LOGGER = logging.getLogger(__name__)

class AviationWeatherApi:
    """API client for fetching METAR and TAF data."""

    def __init__(self, session: aiohttp.ClientSession):
        """Initialize the API client."""
        self._session = session

    async def _async_fetch_data(self, url: str, icao_codes: str) -> list[dict[str, Any]]:
        """Fetch data from the AviationWeather API."""
        headers = {"User-Agent": CUSTOM_USER_AGENT}
        params = {"ids": icao_codes, "format": "json"}
        
        try:
            async with self._session.get(url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    data = await response.json()
                    if not isinstance(data, list):
                        _LOGGER.error("API response is not a list: %s", data)
                        return []
                    
                    # Log which stations returned data
                    station_ids = [item.get("icaoId", "UNKNOWN") for item in data]
                    requested_stations = [code.strip() for code in icao_codes.split(",")]
                    missing_stations = set(requested_stations) - set(station_ids)
                    
                    if missing_stations:
                        _LOGGER.info(
                            "No data available for stations: %s (may not exist or no current reports)",
                            ", ".join(missing_stations)
                        )
                    
                    return data
                    
                if response.status == 204:
                    _LOGGER.info("No data available for ICAO codes: %s (HTTP 204)", icao_codes)
                    return []
                    
                if response.status == 400:
                    error_text = await response.text()
                    _LOGGER.error(
                        "Bad request to %s for %s. Check ICAO codes are valid. Response: %s",
                        url,
                        icao_codes,
                        error_text,
                    )
                    return []
                    
                if response.status == 429:
                    _LOGGER.warning("Rate limit exceeded. Please increase your update intervals.")
                    return []
                
                _LOGGER.error(
                    "Failed to fetch data from %s for %s. Status: %d, Response: %s",
                    url,
                    icao_codes,
                    response.status,
                    await response.text(),
                )
                return []
                
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout while fetching data for %s from %s", icao_codes, url)
            return []
        except ClientConnectorError as err:
            _LOGGER.error("Connection error while fetching data for %s: %s", icao_codes, err)
            return []
        except ClientError as err:
            _LOGGER.error("Client error while fetching data for %s: %s", icao_codes, err)
            return []
        except Exception as err:
            _LOGGER.exception("Unexpected error fetching data for %s from %s", icao_codes, url)
            return []

    async def async_get_metar_data(self, icao_codes: str) -> list[dict[str, Any]]:
        """Fetch METAR data for given ICAO codes."""
        _LOGGER.debug("Fetching METAR data for: %s", icao_codes)
        return await self._async_fetch_data(METAR_API_URL, icao_codes)

    async def async_get_taf_data(self, icao_codes: str) -> list[dict[str, Any]]:
        """Fetch TAF data for given ICAO codes."""
        _LOGGER.debug("Fetching TAF data for: %s", icao_codes)
        return await self._async_fetch_data(TAF_API_URL, icao_codes)
