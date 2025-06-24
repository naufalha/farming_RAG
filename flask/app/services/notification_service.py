# app/services/notification_service.py
# --- Versi Diperbarui: Menggunakan file notif.txt untuk mengirim notifikasi ---

import os
import time

# --- Konfigurasi ---
# Mendefinisikan path absolut ke file notif.txt di direktori mubarok-botjs
# ../../.. -> dari /app/services/ ke /farming_RAG/
NOTIF_FILE_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'mubarok-botjs', 'notif.txt'
))

# Ambil daftar penerima dari environment
RECIPIENT_NUMBERS_STR = os.getenv("NOTIFICATION_RECIPIENTS", "")
RECIPIENTS = [num.strip() for num in RECIPIENT_NUMBERS_STR.split(',') if num.strip()]

def _write_and_wait(recipient, message, image_path=None):
    """
    Menulis satu notifikasi ke file dan menunggu beberapa saat agar
    bisa diproses oleh layanan wawebjs sebelum melanjutkan.
    """
    try:
        # Hapus file lama jika ada untuk memastikan tidak ada antrean ganda
        if os.path.exists(NOTIF_FILE_PATH):
            print(f"NOTIFICATION_SERVICE: Peringatan - file notif.txt masih ada. Menunggu...")
            time.sleep(5) 
            if os.path.exists(NOTIF_FILE_PATH):
                 os.remove(NOTIF_FILE_PATH)

        # Buat konten baris baru: nomor|pesan|path_gambar
        content = f"{recipient}|{message}"
        if image_path and os.path.exists(image_path):
            content += f"|{image_path}"
        
        # Tulis ke file
        with open(NOTIF_FILE_PATH, "w") as f:
            f.write(content)
        
        print(f"NOTIFICATION_SERVICE: Perintah notifikasi untuk {recipient} telah ditulis.")
        
        # Beri waktu 6 detik bagi wawebjs (yang mengecek setiap 5 detik) untuk
        # membaca dan menghapus file sebelum loop berikutnya menimpanya.
        time.sleep(6)

    except Exception as e:
        print(f"NOTIFICATION_SERVICE: Gagal menulis file notifikasi: {e}")

def send_report(message: str, image_path: str = None):
    """
    Mengirimkan laporan (teks dengan atau tanpa gambar) ke semua penerima
    yang terdaftar, satu per satu.
    """
    if not RECIPIENTS:
        print("NOTIFICATION_SERVICE: Tidak ada nomor penerima notifikasi yang diatur di .env.")
        return
    
    print(f"NOTIFICATION_SERVICE: Memulai pengiriman laporan ke {len(RECIPIENTS)} penerima...")
    for recipient in RECIPIENTS:
        _write_and_wait(recipient, message, image_path)
    
    print("NOTIFICATION_SERVICE: Semua laporan telah dijadwalkan untuk dikirim.")

