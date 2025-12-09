"""Sensor platform for Av Weather."""
import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_ICAO_CODES,
    CONF_FEEDS,
    FEED_METAR,
    FEED_TAF,
    METAR_SENSOR_NAME,
    TAF_SENSOR_NAME,
)
from .api import AviationWeatherApi
from .airports import get_airport_by_icao

_LOGGER = logging.getLogger(__name__)


def _format_airport_name_sync(icao: str) -> str:
    """Format airport name synchronously for device_info (uses cache)."""
    from .airports import _AIRPORTS_CACHE
    
    if _AIRPORTS_CACHE and icao.upper() in _AIRPORTS_CACHE:
        data = _AIRPORTS_CACHE[icao.upper()]
        name = data.get("name", "Unknown")
        city = data.get("city", "")
        country = data.get("country", "")
        iata = data.get("iata", "")
        
        label_parts = [icao]
        if iata:
            label_parts[0] = f"{icao} ({iata})"
        
        location_parts = []
        if city:
            location_parts.append(city)
        if country:
            location_parts.append(country)
        
        if location_parts:
            label_parts.append(" - ".join(location_parts))
        
        return " - ".join(label_parts)
    
    return icao


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Av Weather sensors from a config entry."""
    icao_codes: str = entry.data[CONF_ICAO_CODES]
    feeds: list = entry.data[CONF_FEEDS]
    
    session = async_get_clientsession(hass)
    api = AviationWeatherApi(session)
    
    # Store API instance and entities in hass.data for service calls
    if "apis" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["apis"] = {}
    if "entities" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["entities"] = {}
    
    hass.data[DOMAIN]["apis"][entry.entry_id] = api
    
    # Fetch initial data
    initial_metar_data = []
    initial_taf_data = []
    
    if FEED_METAR in feeds:
        _LOGGER.info("Fetching initial METAR data for %s", icao_codes)
        initial_metar_data = await api.async_get_metar_data(icao_codes)
    
    if FEED_TAF in feeds:
        _LOGGER.info("Fetching initial TAF data for %s", icao_codes)
        initial_taf_data = await api.async_get_taf_data(icao_codes)
    
    # Create entities
    entities = []
    for icao_code in icao_codes.split(","):
        icao_code = icao_code.strip()
        if FEED_METAR in feeds:
            entity = MetarSensor(hass, entry, api, icao_code, initial_metar_data)
            entities.append(entity)
            # Store entity reference for service calls
            if icao_code not in hass.data[DOMAIN]["entities"]:
                hass.data[DOMAIN]["entities"][icao_code] = []
            hass.data[DOMAIN]["entities"][icao_code].append(entity)
            
        if FEED_TAF in feeds:
            entity = TafSensor(hass, entry, api, icao_code, initial_taf_data)
            entities.append(entity)
            # Store entity reference for service calls
            if icao_code not in hass.data[DOMAIN]["entities"]:
                hass.data[DOMAIN]["entities"][icao_code] = []
            hass.data[DOMAIN]["entities"][icao_code].append(entity)
    
    async_add_entities(entities, False)


class AvWeatherSensor(SensorEntity):
    """Base class for Av Weather sensors."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: AviationWeatherApi,
        icao_code: str,
        initial_data: list[dict[str, Any]]
    ):
        """Initialize the sensor."""
        self.hass = hass
        self._entry = entry
        self._api = api
        self._icao_code = icao_code.upper()
        self._attr_attribution = "Data provided by AviationWeather.gov"
        self._data: dict[str, Any] | None = None
        
        # Set initial data
        self._update_from_data_list(initial_data)

    def _update_from_data_list(self, data_list: list[dict[str, Any]]) -> None:
        """Update sensor from a list of station data."""
        if data_list:
            for station_data in data_list:
                if station_data.get("icaoId") == self._icao_code:
                    self._data = station_data
                    self._update_state()
                    return
        # No data found for this station
        self._data = None
        self._update_state()

    async def async_update_weather(self, feed_type: str | None = None) -> None:
        """Update weather data via service call."""
        raise NotImplementedError

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._data is not None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        airport_name = _format_airport_name_sync(self._icao_code)
        return DeviceInfo(
            identifiers={(DOMAIN, self._icao_code)},
            name=airport_name,
            manufacturer="AviationWeather.gov",
            model="Weather Station",
            configuration_url="https://aviationweather.gov/",
        )

    def _update_state(self) -> None:
        """Update the state and attributes of the sensor."""
        raise NotImplementedError


class MetarSensor(AvWeatherSensor):
    """Representation of a METAR sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: AviationWeatherApi,
        icao_code: str,
        initial_data: list[dict[str, Any]]
    ):
        """Initialize the METAR sensor."""
        super().__init__(hass, entry, api, icao_code, initial_data)
        self._attr_name = f"{icao_code} {METAR_SENSOR_NAME}"
        self._attr_unique_id = f"{self._icao_code}_{METAR_SENSOR_NAME}"
        self._attr_icon = "mdi:weather-partly-cloudy"

    async def async_update_weather(self, feed_type: str | None = None) -> None:
        """Update METAR data via service call."""
        if feed_type and feed_type != FEED_METAR:
            return
        
        _LOGGER.info("Updating METAR data for %s", self._icao_code)
        data_list = await self._api.async_get_metar_data(self._icao_code)
        self._update_from_data_list(data_list)
        self.async_write_ha_state()

    def _update_state(self) -> None:
        """Update the state and attributes of the sensor."""
        if not self._data:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            self._attr_icon = "mdi:weather-partly-cloudy"
            return

        self._attr_native_value = self._data.get("rawOb")
        
        # Update icon based on flight category
        flight_category = self._data.get("fltCat")
        if flight_category == "VFR":
            self._attr_icon = "mdi:weather-sunny"
        elif flight_category == "MVFR":
            self._attr_icon = "mdi:weather-partly-cloudy"
        elif flight_category == "IFR":
            self._attr_icon = "mdi:weather-cloudy"
        elif flight_category == "LIFR":
            self._attr_icon = "mdi:weather-fog"
        else:
            self._attr_icon = "mdi:weather-partly-cloudy"
        
        # Parse observation time
        obs_time_str = self._data.get("reportTime")
        if obs_time_str:
            try:
                obs_time = dt_util.parse_datetime(obs_time_str)
                if obs_time:
                    self._attr_extra_state_attributes = {"observation_time": obs_time.isoformat()}
                else:
                    self._attr_extra_state_attributes = {"observation_time": obs_time_str}
            except (ValueError, TypeError):
                self._attr_extra_state_attributes = {"observation_time": obs_time_str}
        else:
            self._attr_extra_state_attributes = {}

        # Basic attributes
        self._attr_extra_state_attributes["raw_report"] = self._data.get("rawOb")
        self._attr_extra_state_attributes["station_id"] = self._data.get("icaoId")
        self._attr_extra_state_attributes["temperature_c"] = self._data.get("temp")
        self._attr_extra_state_attributes["dewpoint_c"] = self._data.get("dewp")
        self._attr_extra_state_attributes["wind_speed_kts"] = self._data.get("wspd")
        self._attr_extra_state_attributes["wind_gust_kts"] = self._data.get("wgst")
        self._attr_extra_state_attributes["wind_direction_deg"] = self._data.get("wdir")
        self._attr_extra_state_attributes["visibility_mi"] = self._data.get("visib")
        self._attr_extra_state_attributes["altimeter_in_hg"] = self._data.get("altim")
        self._attr_extra_state_attributes["sea_level_pressure_mb"] = None  # Not in new API
        self._attr_extra_state_attributes["flight_category"] = flight_category
        
        # Cloud coverage
        clouds = self._data.get("clouds", [])
        if clouds:
            self._attr_extra_state_attributes["cloud_coverage"] = [
                f'{c.get("cover", "Unknown")} at {c.get("base", "N/A")} ft AGL' for c in clouds
            ]
        
        # Weather phenomena
        wx_string = self._data.get("wxString")
        if wx_string:
            self._attr_extra_state_attributes["weather"] = wx_string
        
        # Latitude/Longitude
        if self._data.get("lat") is not None and self._data.get("lon") is not None:
            self._attr_extra_state_attributes["latitude"] = self._data.get("lat")
            self._attr_extra_state_attributes["longitude"] = self._data.get("lon")
        
        # Elevation
        if self._data.get("elev") is not None:
            self._attr_extra_state_attributes["elevation_m"] = self._data.get("elev")


class TafSensor(AvWeatherSensor):
    """Representation of a TAF sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: AviationWeatherApi,
        icao_code: str,
        initial_data: list[dict[str, Any]]
    ):
        """Initialize the TAF sensor."""
        super().__init__(hass, entry, api, icao_code, initial_data)
        self._attr_name = f"{icao_code} {TAF_SENSOR_NAME}"
        self._attr_unique_id = f"{self._icao_code}_{TAF_SENSOR_NAME}"
        self._attr_icon = "mdi:weather-cloudy-clock"

    async def async_update_weather(self, feed_type: str | None = None) -> None:
        """Update TAF data via service call."""
        if feed_type and feed_type != FEED_TAF:
            return
        
        _LOGGER.info("Updating TAF data for %s", self._icao_code)
        data_list = await self._api.async_get_taf_data(self._icao_code)
        self._update_from_data_list(data_list)
        self.async_write_ha_state()

    def _update_state(self) -> None:
        """Update the state and attributes of the sensor."""
        if not self._data:
            self._attr_native_value = None
            self._attr_extra_state_attributes = {}
            return

        self._attr_native_value = self._data.get("rawTAF")
        self._attr_extra_state_attributes = {
            "raw_forecast": self._data.get("rawTAF"),
            "station_id": self._data.get("icaoId"),
        }

        # Parse issue and valid times
        issue_time = self._data.get("issueTime")
        if issue_time:
            self._attr_extra_state_attributes["issue_time"] = issue_time
            
        valid_from = self._data.get("validTimeFrom")
        if valid_from:
            # Convert Unix timestamp to ISO format
            try:
                from datetime import datetime
                valid_from_dt = datetime.fromtimestamp(valid_from, tz=dt_util.UTC)
                self._attr_extra_state_attributes["valid_time_from"] = valid_from_dt.isoformat()
            except (ValueError, TypeError):
                self._attr_extra_state_attributes["valid_time_from"] = valid_from
            
        valid_to = self._data.get("validTimeTo")
        if valid_to:
            # Convert Unix timestamp to ISO format
            try:
                from datetime import datetime
                valid_to_dt = datetime.fromtimestamp(valid_to, tz=dt_util.UTC)
                self._attr_extra_state_attributes["valid_time_to"] = valid_to_dt.isoformat()
            except (ValueError, TypeError):
                self._attr_extra_state_attributes["valid_time_to"] = valid_to
        
        # Add latitude/longitude if available
        if self._data.get("lat") is not None and self._data.get("lon") is not None:
            self._attr_extra_state_attributes["latitude"] = self._data.get("lat")
            self._attr_extra_state_attributes["longitude"] = self._data.get("lon")
        
        # Add elevation
        if self._data.get("elev") is not None:
            self._attr_extra_state_attributes["elevation_m"] = self._data.get("elev")
