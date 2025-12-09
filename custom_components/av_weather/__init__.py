"""The Av Weather integration."""
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, SERVICE_UPDATE_WEATHER, FEED_METAR, FEED_TAF

_LOGGER = logging.getLogger(__name__)

# The platforms your integration will support
PLATFORMS = [Platform.SENSOR]

# Service schema
SERVICE_UPDATE_WEATHER_SCHEMA = vol.Schema({
    vol.Optional("icao_code"): cv.string,
    vol.Optional("feed_type"): vol.In([FEED_METAR, FEED_TAF]),
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Av Weather from a config entry."""
    _LOGGER.info("Setting up Av Weather for ICAO codes: %s", entry.data.get("icao_codes"))

    # Store the entry in hass.data for the platforms to access
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = entry.data

    # Forward the setup to the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    async def async_handle_update_weather(call: ServiceCall) -> None:
        """Handle the update_weather service call."""
        icao_code = call.data.get("icao_code")
        feed_type = call.data.get("feed_type")
        
        if "entities" not in hass.data[DOMAIN]:
            _LOGGER.warning("No weather entities found")
            return
        
        entities_to_update = []
        
        # If icao_code is specified, update only that station
        if icao_code:
            icao_code = icao_code.upper()
            if icao_code in hass.data[DOMAIN]["entities"]:
                entities_to_update.extend(hass.data[DOMAIN]["entities"][icao_code])
            else:
                _LOGGER.warning("No entities found for ICAO code: %s", icao_code)
                return
        else:
            # Update all entities
            for entity_list in hass.data[DOMAIN]["entities"].values():
                entities_to_update.extend(entity_list)
        
        # Update each entity
        for entity in entities_to_update:
            try:
                await entity.async_update_weather(feed_type)
            except Exception as e:
                _LOGGER.error("Error updating weather for %s: %s", entity._icao_code, e)
    
    # Register the service
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_WEATHER,
        async_handle_update_weather,
        schema=SERVICE_UPDATE_WEATHER_SCHEMA,
    )
    
    # Listen for config entry updates
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Av Weather for ICAO codes: %s", entry.data.get("icao_codes"))
    
    # Unload the platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Clean up hass.data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        # Clean up entity references
        if "entities" in hass.data[DOMAIN]:
            icao_codes = entry.data.get("icao_codes", "").split(",")
            for icao_code in icao_codes:
                icao_code = icao_code.strip().upper()
                if icao_code in hass.data[DOMAIN]["entities"]:
                    hass.data[DOMAIN]["entities"].pop(icao_code)
        
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
            # Unregister service if no more entries
            if hass.services.has_service(DOMAIN, SERVICE_UPDATE_WEATHER):
                hass.services.async_remove(DOMAIN, SERVICE_UPDATE_WEATHER)

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle an options flow update."""
    _LOGGER.info("Reloading Av Weather configuration")
    await hass.config_entries.async_reload(entry.entry_id)
