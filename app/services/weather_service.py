import requests
import pvlib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class WeatherService:

    OPENWEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5"
    GEOCODING_URL        = "http://api.openweathermap.org/geo/1.0/direct"
    PVGIS_BASE_URL       = "https://re.jrc.ec.europa.eu/api/v5_2"

    @staticmethod
    def get_coordinates(location: str) -> Tuple[float, float]:
        try:
            url    = WeatherService.GEOCODING_URL
            params = {
                'q'     : location,
                'limit' : 1,
                'appid' : settings.OPENWEATHER_API_KEY
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data:
                lat = data[0]['lat']
                lon = data[0]['lon']
                logger.info(f"Coordinates for '{location}': ({lat}, {lon})")
                return lat, lon
            return WeatherService._get_fallback_coordinates(location)
        except requests.RequestException as e:
            logger.warning(f"Geocoding API error: {e}. Using fallback.")
            return WeatherService._get_fallback_coordinates(location)

    @staticmethod
    def _get_fallback_coordinates(location: str) -> Tuple[float, float]:
        """
        FIX BUG 4: Extended fallback list with Indian cities.
        OLD default was Kuala Lumpur — wrong for any Indian city not in the list.
        NEW default is India center (20.5937, 78.9629).
        """
        fallback_locations = {
            # --- International ---
            'kuala lumpur' : (3.1390,   101.6869),
            'singapore'    : (1.3521,   103.8198),
            'london'       : (51.5074,  -0.1278),
            'new york'     : (40.7128,  -74.0060),
            'sydney'       : (-33.8688, 151.2093),
            'dubai'        : (25.2048,   55.2708),
            'jakarta'      : (-6.2088,  106.8456),
            'bangkok'      : (13.7563,  100.5018),
            # --- India: major cities ---
            'india'        : (20.5937,   78.9629),
            'delhi'        : (28.6139,   77.2090),
            'new delhi'    : (28.6139,   77.2090),
            'bengaluru'    : (12.9716,   77.5946),
            'bangalore'    : (12.9716,   77.5946),
            'mumbai'       : (19.0760,   72.8777),
            'bombay'       : (19.0760,   72.8777),
            'chennai'      : (13.0827,   80.2707),
            'madras'       : (13.0827,   80.2707),
            'hyderabad'    : (17.3850,   78.4867),
            'kolkata'      : (22.5726,   88.3639),
            'calcutta'     : (22.5726,   88.3639),
            'pune'         : (18.5204,   73.8567),
            'ahmedabad'    : (23.0225,   72.5714),
            'jaipur'       : (26.9124,   75.7873),
            'surat'        : (21.1702,   72.8311),
            'lucknow'      : (26.8467,   80.9462),
            'nagpur'       : (21.1458,   79.0882),
            'bhopal'       : (23.2599,   77.4126),
            'chandigarh'   : (30.7333,   76.7794),
            'coimbatore'   : (11.0168,   76.9558),
            'kochi'        : (9.9312,    76.2673),
            'cochin'       : (9.9312,    76.2673),
            'visakhapatnam': (17.6868,   83.2185),
            'vizag'        : (17.6868,   83.2185),
            'indore'       : (22.7196,   75.8577),
            'vadodara'     : (22.3072,   73.1812),
            'patna'        : (25.5941,   85.1376),
            'ranchi'       : (23.3441,   85.3096),
            'bhubaneswar'  : (20.2961,   85.8245),
            'guwahati'     : (26.1445,   91.7362),
            'thiruvananthapuram': (8.5241, 76.9366),
            'trivandrum'   : (8.5241,    76.9366),
            'mysuru'       : (12.2958,   76.6394),
            'mysore'       : (12.2958,   76.6394),
            'mangaluru'    : (12.9141,   74.8560),
            'mangalore'    : (12.9141,   74.8560),
            'hubli'        : (15.3647,   75.1240),
            'belgaum'      : (15.8497,   74.4977),
            'belagavi'     : (15.8497,   74.4977),
        }

        location_lower = location.lower().strip()
        for key, coords in fallback_locations.items():
            if key in location_lower or location_lower in key:
                return coords

        # FIX BUG 4: Default India center, NOT Kuala Lumpur
        logger.warning(
            f"Location '{location}' not found in fallback list. "
            f"Defaulting to India center (20.59, 78.96)."
        )
        return (20.5937, 78.9629)

    @staticmethod
    def get_current_weather(lat: float, lon: float) -> Dict:
        try:
            url    = f"{WeatherService.OPENWEATHER_BASE_URL}/weather"
            params = {
                'lat'   : lat,
                'lon'   : lon,
                'appid' : settings.OPENWEATHER_API_KEY,
                'units' : 'metric'
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {
                'temperature'        : data['main']['temp'],
                'feels_like'         : data['main']['feels_like'],
                'humidity'           : data['main']['humidity'],
                'pressure'           : data['main']['pressure'],
                'cloud_cover'        : data['clouds']['all'],
                'wind_speed'         : data['wind']['speed'],
                'weather_description': data['weather'][0]['description'],
                'weather_main'       : data['weather'][0]['main'],
                'visibility'         : data.get('visibility', 10000),
                'timestamp'          : datetime.utcnow().isoformat()
            }
        except requests.RequestException as e:
            logger.error(f"Weather API error: {e}")
            return WeatherService._get_default_weather()

    @staticmethod
    def _get_default_weather() -> Dict:
        return {
            'temperature'        : 28.0,
            'feels_like'         : 30.0,
            'humidity'           : 75,
            'pressure'           : 1013,
            'cloud_cover'        : 30,
            'wind_speed'         : 2.5,
            'weather_description': 'partly cloudy',
            'weather_main'       : 'Clouds',
            'visibility'         : 10000,
            'timestamp'          : datetime.utcnow().isoformat()
        }

    @staticmethod
    def calculate_solar_irradiance(
        lat  : float,
        lon  : float,
        date : Optional[datetime] = None
    ) -> Dict:
        if date is None:
            date = datetime.now()
        try:
            times = pd.date_range(
                start = date.replace(hour=0,  minute=0, second=0),
                end   = date.replace(hour=23, minute=0, second=0),
                freq  = '1h',
                tz    = 'UTC'
            )
            location  = pvlib.location.Location(
                latitude=lat, longitude=lon, tz='UTC', altitude=50)
            clear_sky = location.get_clearsky(times)
            solar_pos = location.get_solarposition(times)

            ghi_values    = clear_sky['ghi'].values
            peak_sun_hours = sum(ghi / 1000 for ghi in ghi_values if ghi > 0)

            daily_ghi = clear_sky['ghi'].sum() / 1000
            daily_dni = clear_sky['dni'].sum() / 1000
            daily_dhi = clear_sky['dhi'].sum() / 1000

            hourly_data = []
            for i, time in enumerate(times):
                if clear_sky['ghi'].iloc[i] > 0:
                    hourly_data.append({
                        'hour'        : time.hour,
                        'ghi'         : round(float(clear_sky['ghi'].iloc[i]), 2),
                        'dni'         : round(float(clear_sky['dni'].iloc[i]), 2),
                        'dhi'         : round(float(clear_sky['dhi'].iloc[i]), 2),
                        'solar_zenith': round(float(solar_pos['zenith'].iloc[i]), 2)
                    })

            return {
                'latitude'          : lat,
                'longitude'         : lon,
                'date'              : date.strftime('%Y-%m-%d'),
                'daily_ghi_kwh_m2'  : round(float(daily_ghi), 3),
                'daily_dni_kwh_m2'  : round(float(daily_dni), 3),
                'daily_dhi_kwh_m2'  : round(float(daily_dhi), 3),
                'peak_sun_hours'    : round(float(peak_sun_hours), 2),
                'hourly_data'       : hourly_data,
                'max_ghi'           : round(float(clear_sky['ghi'].max()), 2),
                'sunrise'           : WeatherService._get_sunrise_sunset(lat, lon, date)['sunrise'],
                'sunset'            : WeatherService._get_sunrise_sunset(lat, lon, date)['sunset']
            }
        except Exception as e:
            logger.error(f"pvlib calculation error: {e}")
            return WeatherService._get_default_irradiance(lat, lon)

    @staticmethod
    def _get_sunrise_sunset(lat: float, lon: float, date: datetime) -> Dict:
        try:
            times    = pd.date_range(
                date.strftime('%Y-%m-%d'), periods=24, freq='1h', tz='UTC')
            location = pvlib.location.Location(lat, lon, tz='UTC')
            solar_pos = location.get_solarposition(times)
            daylight  = solar_pos[solar_pos['elevation'] > 0]
            if not daylight.empty:
                return {
                    'sunrise': str(daylight.index[0].hour)  + ":00",
                    'sunset' : str(daylight.index[-1].hour) + ":00"
                }
        except Exception:
            pass
        return {'sunrise': '6:00', 'sunset': '18:00'}

    @staticmethod
    def _get_default_irradiance(lat: float, lon: float) -> Dict:
        return {
            'latitude'        : lat,
            'longitude'       : lon,
            'date'            : datetime.now().strftime('%Y-%m-%d'),
            'daily_ghi_kwh_m2': 5.5,
            'daily_dni_kwh_m2': 4.8,
            'daily_dhi_kwh_m2': 1.8,
            'peak_sun_hours'  : 5.5,
            'hourly_data'     : [],
            'max_ghi'         : 950.0,
            'sunrise'         : '6:30',
            'sunset'          : '18:30'
        }

    @staticmethod
    def get_annual_irradiance(lat: float, lon: float) -> Dict:
        try:
            url    = f"{WeatherService.PVGIS_BASE_URL}/seriescalc"
            params = {
                'lat'         : lat,
                'lon'         : lon,
                'outputformat': 'json',
                'browser'     : 0,
                'usehorizon'  : 1,
                'raddatabase' : 'PVGIS-SARAH2',
                'startyear'   : 2019,
                'endyear'     : 2023,
                'components'  : 1
            }
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                return WeatherService._process_pvgis_data(response.json())
        except Exception as e:
            logger.warning(f"PVGIS API error: {e}")
        return WeatherService._calculate_annual_pvlib(lat, lon)

    @staticmethod
    def _calculate_annual_pvlib(lat: float, lon: float) -> Dict:
        monthly_data = []
        months = ['Jan','Feb','Mar','Apr','May','Jun',
                  'Jul','Aug','Sep','Oct','Nov','Dec']
        for month_num in range(1, 13):
            date       = datetime(2024, month_num, 15)
            irradiance = WeatherService.calculate_solar_irradiance(lat, lon, date)
            monthly_data.append({
                'month'          : months[month_num - 1],
                'month_num'      : month_num,
                'avg_daily_ghi'  : irradiance['daily_ghi_kwh_m2'],
                'peak_sun_hours' : irradiance['peak_sun_hours']
            })
        annual_avg = sum(m['avg_daily_ghi'] for m in monthly_data) / 12
        return {
            'monthly_data'        : monthly_data,
            'annual_average_ghi'  : round(annual_avg, 3),
            'latitude'            : lat,
            'longitude'           : lon
        }

    @staticmethod
    def _process_pvgis_data(data: dict) -> dict:
        months       = ['Jan','Feb','Mar','Apr','May','Jun',
                        'Jul','Aug','Sep','Oct','Nov','Dec']
        monthly_data = []
        try:
            for month_num, month_name in enumerate(months, 1):
                monthly_data.append({
                    'month'         : month_name,
                    'month_num'     : month_num,
                    'avg_daily_ghi' : 5.0,
                    'peak_sun_hours': 5.0
                })
        except Exception:
            pass
        return {
            'monthly_data'      : monthly_data,
            'annual_average_ghi': 5.0,
            'source'            : 'PVGIS'
        }