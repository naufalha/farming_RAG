image_path = "/home/nopal/farming_RAG/flask/app/../static/images/inspeksi_tanaman_1_1750115167.jpg"
message = "🌱 Laporan inspeksi tanaman terbaru"
phone = "6281919865896"

with open("/home/nopal/farming_RAG/mubarok-botjs/notif.txt", "w") as f:
    f.write(f"{phone}|{message}|{image_path}")
