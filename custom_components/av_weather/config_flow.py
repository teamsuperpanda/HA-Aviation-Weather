"""Config flow for Av Weather integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_ICAO_CODES,
    CONF_FEEDS,
    FEED_METAR,
    FEED_TAF,
)
from .airports import validate_icao_code, format_airport_label

_LOGGER = logging.getLogger(__name__)


async def validate_icao_codes(value: Any) -> str:
    """Validate ICAO codes (can be list from selector or comma-separated string)."""
    # Handle list from multi-select selector
    if isinstance(value, list):
        codes = [code.strip().upper() for code in value if code.strip()]
    # Handle comma-separated string (backward compatibility)
    elif isinstance(value, str):
        codes = [code.strip().upper() for code in value.split(",") if code.strip()]
    else:
        raise vol.Invalid("ICAO codes must be a list or string.")
    
    if not codes:
        raise vol.Invalid("At least one airport must be selected.")
    
    invalid_codes = []
    for code in codes:
        if len(code) != 4:
            invalid_codes.append(f"{code} (must be exactly 4 characters)")
        elif not code.isalpha():
            invalid_codes.append(f"{code} (must contain only letters)")
        elif not await validate_icao_code(code):
            invalid_codes.append(f"{code} (airport not found in database)")
    
    if invalid_codes:
        error_msg = "Invalid ICAO code(s): " + ", ".join(invalid_codes)
        raise vol.Invalid(error_msg)
            
    return ",".join(sorted(list(set(codes))))


class AvWeatherConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Av Weather."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate and process ICAO codes
                validated_icao_codes = await validate_icao_codes(user_input[CONF_ICAO_CODES])
                codes_list = validated_icao_codes.split(",")
                
                # Create a separate entry for each airport after the first one
                for icao_code in codes_list[1:]:  # Skip the first airport
                    # Check if this airport is already configured
                    for entry in self._async_current_entries():
                        if entry.data.get(CONF_ICAO_CODES) == icao_code:
                            _LOGGER.warning("Airport %s is already configured, skipping", icao_code)
                            continue
                    
                    # Create entry for this airport
                    title = await format_airport_label(icao_code)
                    self.hass.async_create_task(
                        self.hass.config_entries.flow.async_init(
                            DOMAIN,
                            context={"source": "import"},
                            data={
                                CONF_ICAO_CODES: icao_code,
                                CONF_FEEDS: user_input[CONF_FEEDS],
                            },
                        )
                    )
                
                # Create entry for the first airport and return
                # (the others will be created via the import flow)
                first_code = codes_list[0]
                title = await format_airport_label(first_code)
                return self.async_create_entry(
                    title=title,
                    data={
                        CONF_ICAO_CODES: first_code,
                        CONF_FEEDS: user_input[CONF_FEEDS],
                    }
                )
            except vol.Invalid as err:
                errors["base"] = str(err)
            except Exception as e:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "An unknown error occurred."


        # Schema for the user form
        data_schema = vol.Schema({
            vol.Required(CONF_ICAO_CODES): selector.TextSelector(
                selector.TextSelectorConfig(
                    multiline=False,
                )
            ),
            vol.Required(CONF_FEEDS, default=[FEED_METAR, FEED_TAF]): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=FEED_METAR, label="METAR (Current Conditions)"),
                        selector.SelectOptionDict(value=FEED_TAF, label="TAF (Forecast)"),
                    ],
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        })
        
        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema, 
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> config_entries.ConfigFlowResult:
        """Handle import of additional airports."""
        icao_code = import_data[CONF_ICAO_CODES]
        
        # Check if already configured
        await self.async_set_unique_id(icao_code)
        self._abort_if_unique_id_configured()
        
        title = await format_airport_label(icao_code)
        return self.async_create_entry(
            title=title,
            data=import_data,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle an options flow for Av Weather."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Update the config entry's data (not options)
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    CONF_ICAO_CODES: self.config_entry.data[CONF_ICAO_CODES],
                    CONF_FEEDS: user_input[CONF_FEEDS],
                },
            )
            return self.async_create_entry(title="", data={})

        options_schema = vol.Schema({
            vol.Required(CONF_FEEDS, default=self.config_entry.data.get(CONF_FEEDS, [FEED_METAR, FEED_TAF])): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=FEED_METAR, label="METAR (Current Conditions)"),
                        selector.SelectOptionDict(value=FEED_TAF, label="TAF (Forecast)"),
                    ],
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
        })

        return self.async_show_form(
            step_id="init", 
            data_schema=options_schema, 
            errors=errors,
        )
