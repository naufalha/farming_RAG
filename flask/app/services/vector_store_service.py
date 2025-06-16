# app/services/vector_store_service.py
# --- Versi Upgrade dengan Model Embedding yang Lebih Canggih ---

import chromadb
import os
from chromadb.config import Settings
# --- PERUBAHAN KUNCI 1: Import embedding functions dari ChromaDB ---
from chromadb.utils import embedding_functions

# --- Konfigurasi ChromaDB ---
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'db'))
client = chromadb.Client(
    Settings(
        persist_directory=DB_PATH,
        is_persistent=True,
    )
)

# --- PERUBAHAN KUNCI 2: Tentukan model embedding yang lebih kuat ---
# Model 'all-mpnet-base-v2' jauh lebih baik dalam memahami konteks semantik
# dibandingkan model default yang lebih ringan.
embedding_model = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-mpnet-base-v2"
)

# Nama koleksi
COLLECTION_NAME = "smart_farm_logs_v2" # Nama baru untuk menghindari konflik dengan data lama

def setup_vector_store():
    """Menginisialisasi koneksi ke ChromaDB dan membuat atau memuat koleksi."""
    try:
        # --- PERUBAHAN KUNCI 3: Terapkan embedding model saat membuat koleksi ---
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_model
        )
        print(f"ChromaDB: Berhasil terhubung ke koleksi '{COLLECTION_NAME}' dengan model embedding kustom.")
        return collection
    except Exception as e:
        print(f"Error saat menginisialisasi ChromaDB: {e}")
        raise e

def add_text_to_db(text: str, collection):
    """Menambahkan satu entri teks ke dalam koleksi."""
    if not text or not collection:
        return
    doc_id = str(hash(text))
    collection.add(
        documents=[text],
        ids=[doc_id]
    )

def search_db(query: str, collection, n_results: int = 5):
    """Mencari dokumen yang paling relevan dengan query di dalam koleksi."""
    if not query or not collection:
        return []
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    return results['documents'][0] if results.get('documents') else []

def get_all_data(collection):
    """Mengambil semua dokumen yang tersimpan dalam sebuah koleksi."""
    if not collection:
        return {"error": "Koleksi tidak valid atau belum diinisialisasi"}
    results = collection.get(include=["documents"])
    return results
