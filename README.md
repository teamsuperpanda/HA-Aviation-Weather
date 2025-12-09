# Aviation Weather for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)  
[![Hassfest](https://github.com/teamsuperpanda/HA-Aviation-Weather/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/teamsuperpanda/HA-Aviation-Weather/actions/workflows/hassfest.yaml)

A custom Home Assistant integration that retrieves METAR and TAF data directly from the official AviationWeather.gov API.

## Overview

This integration provides aviation weather information for any ICAO airport worldwide. It validates airport codes, fetches both METAR and TAF reports, and exposes detailed weather attributes as Home Assistant sensors. Weather updates are controlled entirely through service calls, which helps avoid excessive API requests.

## Features

**Airport Validation**  
ICAO codes are checked against a complete global airport database.

**METAR and TAF Support**  
Fetch current aviation observations and forecasts.

**Service Based Updates**  
Weather is refreshed only when you call the update service.

**Comprehensive Sensor Data**  
Includes flight category, visibility, wind, cloud layers, altimeter, weather phenomena, and more.

## Data Source

This integration is not affiliated with NOAA or AviationWeather.gov.

Weather data is obtained from the public JSON API provided by AviationWeather.gov, which is operated by the United States National Oceanic and Atmospheric Administration.

### Rate Limits

The API includes rate limiting to prevent abuse. Since the exact limits are not published, it is recommended that you:

- Avoid polling more than once per minute per airport  
- Use the update service to request data only when needed  
- Stagger updates if you track several airports

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant.  
2. Select Integrations and search for Av Weather.  
3. Download the integration.  
4. Restart Home Assistant.

### Manual Installation

1. Copy the `custom_components/av_weather` folder into your Home Assistant `config/custom_components` directory.  
2. Restart Home Assistant.

## Configuration

1. Go to **Settings > Devices and Services**.  
2. Select **Add Integration** and search for **Aviation Weather**.  
3. Enter the ICAO airport codes you want to monitor, for example `KJFK, EGLL`.  
4. Choose whether to fetch METAR, TAF, or both.

Weather is retrieved a single time during setup. After this you must use the service `av_weather.update_weather` to refresh the data.

## Services

### av_weather.update_weather

Fetches the latest weather information.

**Parameters**

- `icao_code` optional. Update a single airport. Omit this to update all airports.  
- `feed_type` optional. Use `METAR` or `TAF`. Omit this to update all feeds.

**Examples**

```yaml
action: av_weather.update_weather
```

```yaml
action: av_weather.update_weather
data:
  feed_type: METAR
```

```yaml
action: av_weather.update_weather
data:
  icao_code: NZAA
```

## Example Automations

### Update METARs every 30 minutes

```yaml
automation:
  - alias: "Update METAR every 30 min"
    trigger:
      - platform: time_pattern
        minutes: "/30"
    action:
      - action: av_weather.update_weather
        data:
          feed_type: METAR
```

### Alert on VFR conditions

```yaml
automation:
  - alias: "VFR weather alert"
    trigger:
      - platform: state
        entity_id: sensor.yssy_metar
        attribute: flight_category
        to: "VFR"
    action:
      - action: notify.mobile_app
        data:
          message: "Sydney is VFR!"
```

## Sensor Attributes

### METAR Sensors
- `flight_category`
- `temperature_c`, `dewpoint_c`
- `wind_speed_kts`, `wind_direction_deg`
- `visibility_mi`
- `altimeter_in_hg`
- `cloud_coverage`
- `weather`
- `latitude`, `longitude`, `elevation`

### TAF Sensors
- Issue and valid times
- Coordinates and elevation

## Credits

- Airport data from [mwgg/Airports](https://github.com/mwgg/Airports)
- Weather data from [AviationWeather.gov](https://aviationweather.gov/) (NOAA)

## Issues

Issues and feature requests are welcome! Please report them on the [GitHub Issues](https://github.com/teamsuperpanda/HA-Aviation-Weather/issues) page.

## License

MIT License
