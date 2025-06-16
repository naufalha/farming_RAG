# app/services/weather_service.py
# --- Layanan untuk Mengambil Data Prakiraan Cuaca dari Open-Meteo ---

import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry

# --- Konfigurasi ---
LATITUDE = -7.6364
LONGITUDE = 110.7820
TIMEZONE = "Asia/Jakarta"

# Setup klien Open-Meteo
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)


def _format_weather_summary(forecast_data: dict) -> str:
    """Fungsi helper untuk mengubah data cuaca menjadi kalimat ringkasan."""
    try:
        date_str = forecast_data['date'].strftime("%A, %d %B %Y")
        temp_max = forecast_data['temperature_2m_max']
        temp_min = forecast_data['temperature_2m_min']
        uv_index = forecast_data['uv_index_max']
        precipitation = forecast_data['precipitation_sum']

        summary = (
            f"Prakiraan cuaca untuk {date_str}: Suhu antara {temp_min:.1f}°C dan {temp_max:.1f}°C, "
            f"dengan curah hujan {precipitation:.1f} mm dan indeks UV maksimal {uv_index:.1f}."
        )
        return summary
    except (KeyError, AttributeError) as e:
        return f"Gagal memformat ringkasan cuaca: {e}"


def get_daily_forecast_as_dict() -> dict | None:
    """
    Mengambil data cuaca harian dan mengembalikannya sebagai dictionary
    yang siap disimpan ke database SQL.
    """
    print("WEATHER_SERVICE: Mengambil prakiraan cuaca harian...")
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "daily": ["temperature_2m_max", "temperature_2m_min", "uv_index_max", "precipitation_sum"],
        "timezone": TIMEZONE,
        "forecast_days": 1
    }
    try:
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]

        daily = response.Daily()

        # Mengonversi timestamp awal menjadi objek tanggal tunggal
        date = pd.to_datetime(daily.Time(), unit="s", utc=True).date()

        # Ambil nilai cuaca. Karena forecast_days=1, setiap array hanya punya satu elemen.
        temp_max = daily.Variables(0).ValuesAsNumpy()[0]
        temp_min = daily.Variables(1).ValuesAsNumpy()[0]
        uv_index = daily.Variables(2).ValuesAsNumpy()[0]
        precipitation_sum = daily.Variables(3).ValuesAsNumpy()[0]

        # Susun dictionary hasil akhir
        today_forecast = {
            "date": date,
            "temperature_2m_max": temp_max,
            "temperature_2m_min": temp_min,
            "uv_index_max": uv_index,
            "precipitation_sum": precipitation_sum,
        }
        
        # --- PERUBAHAN: Menampilkan ringkasan yang sudah dikonversi di log ---
        summary_text = _format_weather_summary(today_forecast)
        print(f"WEATHER_SERVICE: {summary_text}")
        
        return today_forecast

    except Exception as e:
        print(f"WEATHER_SERVICE: Gagal mengambil data cuaca harian: {e}")
        return None
