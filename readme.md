# Dokumentasi Proyek: Mubarok Smart Farm Assistant

**Versi Dokumen:** 1.0
**Tanggal:** 20 Juni 2025

## 1. Pendahuluan

**Mubarok Smart Farm Assistant** adalah sebuah sistem cerdas berbasis IoT dan AI yang dirancang untuk memantau, menganalisis, dan memberikan rekomendasi untuk *greenhouse* hidroponik. Sistem ini mengintegrasikan sensor lingkungan, platform robotik untuk inspeksi visual, dan asisten AI yang bisa diajak berkomunikasi melalui WhatsApp untuk memberikan laporan serta menjawab pertanyaan secara interaktif.

### Teknologi Utama yang Digunakan

* **Backend:** Python dengan framework Flask.
* **AI & Machine Learning:** LangChain (SQL Agent & RAG), DeepSeek (LLM), Ultralytics (YOLOv8), Kindwise API (Diagnosis Penyakit).
* **Database:** SQLite (untuk data terstruktur) & ChromaDB (untuk data tidak terstruktur/vektor).
* **Perangkat Keras IoT:** ESP32 (Sensor Node), Raspberry Pi (IoT Broker/Robot Controller).
* **Komunikasi:** MQTT (untuk sensor), HTTP REST API.
* **Antarmuka Pengguna:** WhatsApp, dihubungkan melalui `whatsapp-web.js`.
* **Manajemen Proses:** PM2 (untuk menjalankan layanan Flask & Node.js secara persisten).

---

## 2. Arsitektur Sistem

Sistem ini dibangun dengan arsitektur hibrida yang memisahkan antara pengumpulan data, pemrosesan, dan interaksi pengguna.


+----------------+      (MQTT)      +---------------------+      (HTTP)      +------------------+
|   Perangkat    |<---------------->|   Server Flask      |<---------------->|   Jembatan WA    |
|   IoT (ESP32)  |                  | (Otak & Gudang Data)|                  | (Node.js/wwebjs) |
+----------------+                  +----------+----------+                  +--------+---------+
^                                       ^                                     ^
| (Kontrol)                             | (Analisis)                          | (Interaksi)
v                                       v                                     v
+----------------+                  +----------+----------+                  +--------+---------+
| Robot Platform |                  |  Database Hibrida   |                  |   Pengguna WA    |
| (Edge IoT)     |                  | (SQL + Vector)      |                  |                  |
+----------------+                  +---------------------+                  +------------------+


**Alur Kerja Umum:**
1.  **Pengumpulan Data:** ESP32 mengirim data sensor (pH, TDS, suhu) ke Broker MQTT.
2.  **Pencatatan Data:** Layanan MQTT di server Flask menerima data dan menyimpannya ke database SQLite.
3.  **Inspeksi Otomatis:** Setiap jam 9 pagi, layanan *scheduler* di Flask memerintahkan *robot platform* untuk mengambil gambar tanaman. Gambar dianalisis oleh YOLO & Kindwise, lalu hasilnya (kondisi, diagnosis, path gambar) disimpan ke database SQLite.
4.  **Interaksi Pengguna:** Pengguna mengirim pesan (teks/gambar/PDF) ke WhatsApp. Jembatan `wweb.js` meneruskannya ke API Flask.
5.  **Pemrosesan AI:** Layanan RAG di Flask menganalisis pertanyaan, memilih "alat" yang tepat (SQL Agent atau Vector DB), mengambil data, dan merumuskan jawaban dengan bantuan LLM DeepSeek.
6.  **Pemberian Respons:** Jawaban dikirim kembali ke pengguna melalui WhatsApp.

---

## 3. Struktur Proyek

Proyek ini terbagi menjadi dua folder utama: `flask/` untuk backend dan `mubarok-botjs/` untuk jembatan WhatsApp.

### `flask/`

.
├── app/
│   ├── api/
│   │   └── routes.py         # Definisi semua endpoint API
│   ├── services/
│   │   ├── sql_database_service.py   # Mengelola database SQL (log)
│   │   ├── vector_store_service.py   # Mengelola vector DB (pengetahuan)
│   │   ├── rag_service.py          # Otak utama AI Agent (Router)
│   │   ├── mqtt_service.py         # Menerima data sensor
│   │   ├── scheduler_service.py    # Menjalankan tugas otomatis
│   │   ├── inspection_service.py   # Mengorkestrasi inspeksi robot
│   │   ├── robot_service.py        # Berkomunikasi dengan robot
│   │   ├── yolo_service.py         # Analisis gambar dengan YOLO
│   │   ├── kindwise_service.py     # Diagnosis penyakit
│   │   ├── notification_service.py # Mengirim laporan ke WA
│   │   └── ...
│   ├── utils/
│   │   └── helpers.py          # Fungsi-fungsi bantuan
│   └── init.py           # Factory untuk aplikasi Flask
├── db/                         # Lokasi penyimpanan database
├── static/images/              # Lokasi penyimpanan gambar
├── uploads/pdfs/               # Lokasi penyimpanan PDF
├── .env                        # File konfigurasi & API Key
├── requirements.txt            # Daftar library Python
└── run.py                      # File untuk menjalankan server Flask


### `mubarok-botjs/`

.
├── .wwebjs_auth/   # Direktori penyimpanan sesi WhatsApp
├── node_modules/     # Library JavaScript
├── index.js          # Kode utama untuk jembatan WhatsApp
├── package.json      # Informasi proyek Node.js
└── ...


---

## 4. Konfigurasi & Setup

### Backend Flask

1.  **Buat Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
2.  **Install Dependensi:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Konfigurasi `.env`:**
    Buat file `.env` di dalam folder `flask/` dan isi dengan semua kunci API dan konfigurasi yang dibutuhkan (DeepSeek, MQTT, Kindwise, IP Robot, nomor WA, dll).

### Jembatan WhatsApp

1.  **Install Dependensi:**
    ```bash
    cd ../mubarok-botjs
    npm install
    ```
2.  **Login Pertama Kali:**
    Jalankan `node index.js` untuk pertama kali, lalu pindai QR code yang muncul di terminal menggunakan aplikasi WhatsApp Anda.

---

## 5. Cara Menjalankan

Untuk lingkungan produksi, kedua layanan (Flask dan Node.js) dijalankan dan diawasi oleh **PM2**.

1.  **Install PM2 (jika belum ada):**
    ```bash
    npm install pm2 -g
    ```
2.  **Jalankan Aplikasi Flask:**
    ```bash
    # Pastikan Anda di folder flask/ dan venv aktif
    pm2 start run.py --name "mubarok-flask" --interpreter venv/bin/python
    ```
3.  **Jalankan Jembatan WhatsApp:**
    ```bash
    # Pindah ke folder mubarok-botjs/
    pm2 start index.js --name "mubarok-bot"
    ```
4.  **Simpan Konfigurasi untuk Startup Otomatis:**
    ```bash
    pm2 save
    pm2 startup
    # Jalankan perintah yang diberikan oleh pm2 startup
    ```

### Perintah Berguna PM2

* **Melihat status semua layanan:** `pm2 list`
* **Melihat log real-time:** `pm2 logs <nama_layanan>` (cth: `pm2 logs mubarok-flask`)
* **Me-restart layanan:** `pm2 restart <nama_layanan>`
* **Menghentikan layanan:** `pm2 stop <nama_layanan>`

