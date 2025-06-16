# app/services/pdf_service.py
# --- Layanan untuk Memproses dan Memvektorisasi PDF ---

import os
import base64
from . import vector_store_service
from . import rag_service

# Import komponen LangChain untuk memproses PDF
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

def save_b64_as_pdf(b64_string: str, file_path: str):
    """Menyimpan string base64 menjadi file PDF."""
    try:
        pdf_bytes = base64.b64decode(b64_string)
        with open(file_path, 'wb') as f:
            f.write(pdf_bytes)
        return True
    except Exception as e:
        print(f"PDF_SERVICE: Gagal menyimpan file PDF: {e}")
        return False

def process_and_summarize_pdf(file_path: str, db_collection):
    """
    Memuat PDF, memecahnya menjadi potongan teks (chunks), menyimpannya ke Vector DB,
    dan mengembalikan ringkasan dari potongan pertama.
    """
    print(f"PDF_SERVICE: Memproses file -> {file_path}")
    
    try:
        # 1. Muat dokumen PDF
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        # 2. Pecah dokumen menjadi potongan-potongan kecil
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        docs_split = text_splitter.split_documents(documents)
        
        # 3. Ambil hanya konten teks untuk disimpan ke ChromaDB
        doc_contents = [doc.page_content for doc in docs_split]
        
        # 4. Simpan potongan teks ke Vector DB
        print(f"PDF_SERVICE: Menambahkan {len(doc_contents)} potongan dokumen ke Vector DB...")
        # (Kita asumsikan vector_store_service bisa menangani list)
        for content in doc_contents:
            vector_store_service.add_text_to_db(content, db_collection)
        
        print("PDF_SERVICE: Penambahan dokumen selesai.")
        
        # 5. Buat ringkasan dari potongan pertama sebagai konfirmasi
        summary = rag_service.summarize_text(doc_contents[0])
        
        # Hapus file PDF sementara setelah diproses
        os.remove(file_path)
        
        return f"Terima kasih! Dokumen berhasil diproses. Berikut ringkasan singkatnya:\n\n---\n{summary}"

    except Exception as e:
        print(f"PDF_SERVICE: Error saat memproses PDF: {e}")
        return "Maaf, terjadi kesalahan saat saya mencoba membaca file PDF tersebut."

