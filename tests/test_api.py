#!/usr/bin/env python3
"""Test script to verify API field mappings."""
import asyncio
import json
import aiohttp

METAR_API_URL = "https://aviationweather.gov/api/data/metar"
TAF_API_URL = "https://aviationweather.gov/api/data/taf"

async def test_metar():
    """Test METAR API response."""
    print("Testing METAR for NZAA...")
    async with aiohttp.ClientSession() as session:
        params = {"ids": "NZAA", "format": "json"}
        async with session.get(METAR_API_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data:
                    print("✓ METAR data received")
                    print(f"  Station: {data[0].get('icaoId')}")
                    print(f"  Raw: {data[0].get('rawOb')}")
                    print(f"  Flight Category: {data[0].get('fltCat')}")
                    print(f"  Temperature: {data[0].get('temp')}°C")
                    print(f"  Wind: {data[0].get('wdir')}° at {data[0].get('wspd')} kts")
                    return True
                else:
                    print("✗ No METAR data returned")
                    return False
            else:
                print(f"✗ METAR API error: {response.status}")
                return False

async def test_taf():
    """Test TAF API response."""
    print("\nTesting TAF for NZAA...")
    async with aiohttp.ClientSession() as session:
        params = {"ids": "NZAA", "format": "json"}
        async with session.get(TAF_API_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if data:
                    print("✓ TAF data received")
                    print(f"  Station: {data[0].get('icaoId')}")
                    print(f"  Raw: {data[0].get('rawTAF')}")
                    print(f"  Issue Time: {data[0].get('issueTime')}")
                    print(f"  Valid From: {data[0].get('validTimeFrom')}")
                    print(f"  Valid To: {data[0].get('validTimeTo')}")
                    print(f"  Forecast periods: {len(data[0].get('fcsts', []))}")
                    return True
                else:
                    print("✗ No TAF data returned")
                    return False
            else:
                print(f"✗ TAF API error: {response.status}")
                return False

async def main():
    """Run tests."""
    metar_ok = await test_metar()
    taf_ok = await test_taf()
    
    print("\n" + "="*50)
    if metar_ok and taf_ok:
        print("✓ All tests passed!")
        print("\nThe integration should now work correctly.")
        print("In Home Assistant, reload the integration or restart HA.")
    else:
        print("✗ Some tests failed")

if __name__ == "__main__":
    asyncio.run(main())
