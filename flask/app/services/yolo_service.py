# app/services/yolo_service.py
# --- Versi yang Disesuaikan untuk Model Deteksi Objek ---

import os
from ultralytics import YOLO
from collections import Counter

class YOLOService:
    """
    Kelas ini sekarang dirancang untuk menangani model deteksi objek (object detection).
    """
    def __init__(self, model_path):
        self.model = None
        self.model_path = model_path
        self._load_model()

    def _load_model(self):
        """Memuat model YOLO dari file .pt."""
        print(f"YOLO_SERVICE: Mencoba memuat model dari: {self.model_path}")
        if not os.path.exists(self.model_path):
            print(f"YOLO_SERVICE: ERROR - File model tidak ditemukan di {self.model_path}")
            return
        try:
            self.model = YOLO(self.model_path)
            print("YOLO_SERVICE: Model deteksi objek berhasil dimuat.")
        except Exception as e:
            print(f"YOLO_SERVICE: Gagal memuat model. Error: {e}")
            self.model = None
        
    def classify_image(self, image_path: str) -> str:
        """
        Melakukan deteksi pada gambar dan menentukan status keseluruhan.
        """
        if not self.model:
            return "error_model_tidak_dimuat"

        print(f"YOLO_SERVICE: Melakukan deteksi pada gambar: {image_path}...")
        
        try:
            # --- PERUBAHAN UTAMA: Memproses hasil deteksi ---
            results = self.model(image_path)
            
            detected_classes = []
            if results[0].boxes:
                # Ambil semua ID kelas yang terdeteksi
                class_indices = results[0].boxes.cls.tolist()
                # Ubah ID menjadi nama kelas
                detected_classes = [results[0].names[int(i)] for i in class_indices]

            if not detected_classes:
                return "tidak ada tanaman terdeteksi"

            # Hitung jumlah setiap kelas yang terdeteksi
            class_counts = Counter(detected_classes)
            print(f"YOLO_SERVICE: Objek terdeteksi -> {dict(class_counts)}")

            # Tentukan status akhir berdasarkan prioritas
            if class_counts['not healty'] > 0:
                return "tidak sehat"
            elif class_counts['healty'] > 0:
                return "sehat"
            elif class_counts['siap-panen'] > 0:
                return "siap panen"
            elif class_counts['belum-siap'] > 0:
                return "belum siap panen"
            else:
                return "tidak terklasifikasi"
            
        except Exception as e:
            print(f"YOLO_SERVICE: Terjadi error saat inferensi: {e}")
            return "error_saat_inferensi"

# --- Inisialisasi Layanan (tetap sama) ---
model_file_path = os.path.join(
    os.path.dirname(__file__), 
    'pakcoy_combined_v18', 
    'weights', 
    'best.pt'
)
yolo_classifier = YOLOService(model_path=model_file_path)

def classify_image(image_path: str) -> str:
    """Fungsi pembungkus untuk memanggil metode klasifikasi dari instance layanan."""
    return yolo_classifier.classify_image(image_path)
