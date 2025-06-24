import sqlite3

# Path ke database
db_path = "farm_data.db"

# Connect ke database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Hapus semua data dari tabel environment_logs
cursor.execute("DELETE FROM environment_logs")

# Commit perubahan dan tutup koneksi
conn.commit()
conn.close()

print("🔥 Semua data di tabel 'environment_logs' telah dihapus.")
