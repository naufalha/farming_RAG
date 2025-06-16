# app/utils/helpers.py

def allowed_file(filename, allowed_set):
    """Mengecek apakah ekstensi file ada dalam set yang diizinkan."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_set