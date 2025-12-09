"""Constants for the Av Weather integration."""

DOMAIN = "av_weather"

# API Endpoints
METAR_API_URL = "https://aviationweather.gov/api/data/metar"
TAF_API_URL = "https://aviationweather.gov/api/data/taf"

# Configuration keys
CONF_ICAO_CODES = "icao_codes"
CONF_FEEDS = "feeds"

# Feed types
FEED_METAR = "METAR"
FEED_TAF = "TAF"

# User-Agent for requests
CUSTOM_USER_AGENT = "HomeAssistant-AviationWeather/1.0.0"

# Sensor names
METAR_SENSOR_NAME = "METAR"
TAF_SENSOR_NAME = "TAF"

# Service names
SERVICE_UPDATE_WEATHER = "update_weather"
