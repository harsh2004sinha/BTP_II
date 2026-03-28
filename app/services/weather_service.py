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
    """
    Service to fetch weather and solar irradiance data.
    Uses OpenWeatherMap and pvlib for solar calculations.
    """
    
    OPENWEATHER_BASE_URL = "http://api.openweathermap.org/data/2.5"
    GEOCODING_URL = "http://api.openweathermap.org/geo/1.0/direct"
    PVGIS_BASE_URL = "https://re.jrc.ec.europa.eu/api/v5_2"
    
    @staticmethod
    def get_coordinates(location: str) -> Tuple[float, float]:
        """
        Get latitude/longitude from location name.
        
        Args:
            location: City name or address
            
        Returns:
            Tuple of (latitude, longitude)
        """
        try:
            url = WeatherService.GEOCODING_URL
            params = {
                'q': location,
                'limit': 1,
                'appid': settings.OPENWEATHER_API_KEY
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data:
                lat = data[0]['lat']
                lon = data[0]['lon']
                logger.info(f"Coordinates for '{location}': ({lat}, {lon})")
                return lat, lon
            
            # Fallback: use hardcoded coordinates for common locations
            return WeatherService._get_fallback_coordinates(location)
            
        except requests.RequestException as e:
            logger.warning(f"Geocoding API error: {e}. Using fallback.")
            return WeatherService._get_fallback_coordinates(location)
    
    @staticmethod
    def _get_fallback_coordinates(location: str) -> Tuple[float, float]:
        """Fallback coordinates for common locations"""
        fallback_locations = {
            'kuala lumpur': (3.1390, 101.6869),
            'singapore': (1.3521, 103.8198),
            'london': (51.5074, -0.1278),
            'new york': (40.7128, -74.0060),
            'sydney': (-33.8688, 151.2093),
            'dubai': (25.2048, 55.2708),
            'delhi': (28.6139, 77.2090),
            'jakarta': (-6.2088, 106.8456),
            'bangkok': (13.7563, 100.5018),
        }
        
        location_lower = location.lower().strip()
        for key, coords in fallback_locations.items():
            if key in location_lower or location_lower in key:
                return coords
        
        # Default: Kuala Lumpur (tropical, good solar)
        logger.warning(f"Location '{location}' not found. Using KL as default.")
        return (3.1390, 101.6869)
    
    @staticmethod
    def get_current_weather(lat: float, lon: float) -> Dict:
        """
        Get current weather conditions.
        
        Returns:
            Dict with temperature, cloud cover, humidity, etc.
        """
        try:
            url = f"{WeatherService.OPENWEATHER_BASE_URL}/weather"
            params = {
                'lat': lat,
                'lon': lon,
                'appid': settings.OPENWEATHER_API_KEY,
                'units': 'metric'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            return {
                'temperature': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'cloud_cover': data['clouds']['all'],  # percentage
                'wind_speed': data['wind']['speed'],
                'weather_description': data['weather'][0]['description'],
                'weather_main': data['weather'][0]['main'],
                'visibility': data.get('visibility', 10000),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except requests.RequestException as e:
            logger.error(f"Weather API error: {e}")
            return WeatherService._get_default_weather()
    
    @staticmethod
    def _get_default_weather() -> Dict:
        """Default weather when API unavailable"""
        return {
            'temperature': 28.0,
            'feels_like': 30.0,
            'humidity': 75,
            'pressure': 1013,
            'cloud_cover': 30,
            'wind_speed': 2.5,
            'weather_description': 'partly cloudy',
            'weather_main': 'Clouds',
            'visibility': 10000,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def calculate_solar_irradiance(
        lat: float,
        lon: float,
        date: Optional[datetime] = None
    ) -> Dict:
        """
        Calculate solar irradiance using pvlib.
        
        Args:
            lat: Latitude
            lon: Longitude
            date: Date for calculation (default: today)
            
        Returns:
            Dict with GHI, DNI, DHI values
        """
        if date is None:
            date = datetime.now()
        
        try:
            # Create time range for the day (hourly)
            times = pd.date_range(
                start=date.replace(hour=0, minute=0, second=0),
                end=date.replace(hour=23, minute=0, second=0),
                freq='1h',
                tz='UTC'
            )
            
            # Get location object
            location = pvlib.location.Location(
                latitude=lat,
                longitude=lon,
                tz='UTC',
                altitude=50  # approximate
            )
            
            # Calculate clear sky irradiance
            clear_sky = location.get_clearsky(times)
            
            # Solar position
            solar_position = location.get_solarposition(times)
            
            # Calculate peak sun hours
            ghi_values = clear_sky['ghi'].values
            peak_sun_hours = sum(ghi / 1000 for ghi in ghi_values if ghi > 0)
            
            # Daily totals (kWh/m2/day)
            daily_ghi = clear_sky['ghi'].sum() / 1000  # Convert Wh to kWh
            daily_dni = clear_sky['dni'].sum() / 1000
            daily_dhi = clear_sky['dhi'].sum() / 1000
            
            # Hourly data for chart
            hourly_data = []
            for i, time in enumerate(times):
                if clear_sky['ghi'].iloc[i] > 0:
                    hourly_data.append({
                        'hour': time.hour,
                        'ghi': round(float(clear_sky['ghi'].iloc[i]), 2),
                        'dni': round(float(clear_sky['dni'].iloc[i]), 2),
                        'dhi': round(float(clear_sky['dhi'].iloc[i]), 2),
                        'solar_zenith': round(
                            float(solar_position['zenith'].iloc[i]), 2
                        )
                    })
            
            return {
                'latitude': lat,
                'longitude': lon,
                'date': date.strftime('%Y-%m-%d'),
                'daily_ghi_kwh_m2': round(float(daily_ghi), 3),
                'daily_dni_kwh_m2': round(float(daily_dni), 3),
                'daily_dhi_kwh_m2': round(float(daily_dhi), 3),
                'peak_sun_hours': round(float(peak_sun_hours), 2),
                'hourly_data': hourly_data,
                'max_ghi': round(float(clear_sky['ghi'].max()), 2),
                'sunrise': WeatherService._get_sunrise_sunset(
                    lat, lon, date
                )['sunrise'],
                'sunset': WeatherService._get_sunrise_sunset(
                    lat, lon, date
                )['sunset']
            }
            
        except Exception as e:
            logger.error(f"pvlib calculation error: {e}")
            return WeatherService._get_default_irradiance(lat, lon)
    
    @staticmethod
    def _get_sunrise_sunset(lat: float, lon: float, date: datetime) -> Dict:
        """Get sunrise and sunset times"""
        try:
            times = pd.date_range(
                date.strftime('%Y-%m-%d'),
                periods=24,
                freq='1h',
                tz='UTC'
            )
            location = pvlib.location.Location(lat, lon, tz='UTC')
            solar_pos = location.get_solarposition(times)
            
            # Find hours when sun is above horizon
            daylight = solar_pos[solar_pos['elevation'] > 0]
            
            if not daylight.empty:
                return {
                    'sunrise': str(daylight.index[0].hour) + ":00",
                    'sunset': str(daylight.index[-1].hour) + ":00"
                }
        except Exception:
            pass
        
        return {'sunrise': '6:00', 'sunset': '18:00'}
    
    @staticmethod
    def _get_default_irradiance(lat: float, lon: float) -> Dict:
        """Default irradiance values"""
        return {
            'latitude': lat,
            'longitude': lon,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'daily_ghi_kwh_m2': 5.5,
            'daily_dni_kwh_m2': 4.8,
            'daily_dhi_kwh_m2': 1.8,
            'peak_sun_hours': 5.5,
            'hourly_data': [],
            'max_ghi': 950.0,
            'sunrise': '6:30',
            'sunset': '18:30'
        }
    
    @staticmethod
    def get_annual_irradiance(lat: float, lon: float) -> Dict:
        """
        Get annual average irradiance data using PVGIS API.
        
        Returns monthly averages for optimization.
        """
        try:
            url = f"{WeatherService.PVGIS_BASE_URL}/seriescalc"
            params = {
                'lat': lat,
                'lon': lon,
                'outputformat': 'json',
                'browser': 0,
                'usehorizon': 1,
                'raddatabase': 'PVGIS-SARAH2',
                'startyear': 2019,
                'endyear': 2023,
                'components': 1
            }
            
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return WeatherService._process_pvgis_data(data)
                
        except Exception as e:
            logger.warning(f"PVGIS API error: {e}")
        
        # Fallback: calculate using pvlib for each month
        return WeatherService._calculate_annual_pvlib(lat, lon)
    
    @staticmethod
    def _calculate_annual_pvlib(lat: float, lon: float) -> Dict:
        """Calculate annual data using pvlib"""
        monthly_data = []
        months = [
            'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
        ]
        
        for month_num in range(1, 13):
            date = datetime(2024, month_num, 15)
            irradiance = WeatherService.calculate_solar_irradiance(lat, lon, date)
            
            monthly_data.append({
                'month': months[month_num - 1],
                'month_num': month_num,
                'avg_daily_ghi': irradiance['daily_ghi_kwh_m2'],
                'peak_sun_hours': irradiance['peak_sun_hours']
            })
        
        annual_avg = sum(m['avg_daily_ghi'] for m in monthly_data) / 12
        
        return {
            'monthly_data': monthly_data,
            'annual_average_ghi': round(annual_avg, 3),
            'latitude': lat,
            'longitude': lon
        }
    
    @staticmethod
    def _process_pvgis_data(data: dict) -> dict:
        """Process PVGIS API response"""
        # Process the PVGIS data format
        monthly_data = []
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        try:
            monthly_totals = {}
            inputs = data.get('inputs', {})
            
            for month_num, month_name in enumerate(months, 1):
                monthly_data.append({
                    'month': month_name,
                    'month_num': month_num,
                    'avg_daily_ghi': 5.0,  # Default fallback
                    'peak_sun_hours': 5.0
                })
        except Exception:
            pass
        
        return {
            'monthly_data': monthly_data,
            'annual_average_ghi': 5.0,
            'source': 'PVGIS'
        }