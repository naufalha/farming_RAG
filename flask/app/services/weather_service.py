# app/services/weather_service.py
# --- Versi yang Dioptimalkan untuk Penjadwal dan Vector DB ---

import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
import locale
from datetime import datetime
import pytz

# --- Konfigurasi ---
LATITUDE = -7.6364
LONGITUDE = 110.7820
TIMEZONE = "Asia/Jakarta"

# Setup klien Open-Meteo
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

def get_daily_forecast_as_text() -> str | None:
    """
    Mengambil data cuaca harian dan mengembalikannya sebagai satu kalimat
    lengkap yang siap disimpan ke Vector DB.
    """
    print("WEATHER_SERVICE: Menjalankan pengambilan prakiraan cuaca harian...")
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "daily": ["temperature_2m_max", "temperature_2m_min", "uv_index_max", "precipitation_sum"],
        "timezone": TIMEZONE,
        "forecast_days": 1
    }
    try:
        response = openmeteo.weather_api(url, params=params)[0]
        daily = response.Daily()

        # Atur locale untuk nama hari/bulan dalam Bahasa Indonesia
        try:
            locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')
        except locale.Error:
            print("Peringatan: locale 'id_ID.UTF-8' tidak ditemukan. Menggunakan format default.")

        # Ambil dan format data
        date = pd.to_datetime(daily.Time(), unit="s", utc=True).date()
        date_str = date.strftime("%A, %d %B %Y")
        temp_max = daily.Variables(0).ValuesAsNumpy()[0]
        temp_min = daily.Variables(1).ValuesAsNumpy()[0]
        uv_index = daily.Variables(2).ValuesAsNumpy()[0]
        precipitation = daily.Variables(3).ValuesAsNumpy()[0]

        # Buat kalimat ringkasan yang kaya konteks
        summary = (
            f"Prakiraan cuaca untuk {date_str}: Suhu diperkirakan berkisar antara {temp_min:.1f}°C hingga {temp_max:.1f}°C. "
            f"Total curah hujan sekitar {precipitation:.1f} mm. Indeks UV maksimal hari ini adalah {uv_index:.1f}, yang termasuk kategori tinggi."
        )
        print(f"WEATHER_SERVICE: Prakiraan cuaca dibuat -> {summary}")
        return summary

    except Exception as e:
        print(f"WEATHER_SERVICE: Gagal mengambil data cuaca harian: {e}")
        return None
