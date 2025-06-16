# app/services/rag_service.py (Hybrid: SQL Agent + Vector Store RAG)
# --- Menggabungkan kekuatan SQL dan Pencarian Semantik ---

import os
from . import sql_database_service, vector_store_service
from langchain_deepseek import ChatDeepSeek
from langchain_community.agent_toolkits import create_sql_agent
from langchain_community.utilities import SQLDatabase
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import PromptTemplate
from datetime import datetime

# --- Inisialisasi Komponen ---
llm = ChatDeepSeek(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_API_BASE"),
    temperature=0.2 # Dibuat lebih faktual
)
db_uri = f"sqlite:///{sql_database_service.DB_PATH}"
db = SQLDatabase.from_uri(db_uri)

# --- State Management untuk Memori ---
conversation_memory_store = {}

def get_or_create_memory(chat_id: str):
    """Membuat atau mengambil memori percakapan untuk pengguna tertentu."""
    if chat_id not in conversation_memory_store:
        conversation_memory_store[chat_id] = ConversationBufferMemory(memory_key="history", input_key="input")
    return conversation_memory_store[chat_id]

# --- Alat: SQL Agent untuk Mengambil Data Terstruktur ---
def get_sql_context(question: str) -> str:
    """Menggunakan SQL Agent untuk membuat kueri dan mengambil data dari database SQL."""
    print(f"SQL_TOOL: Menerima pertanyaan untuk diubah ke SQL -> '{question}'")
    agent_executor = create_sql_agent(
        llm=llm,
        db=db,
        agent_type="openai-tools",
        verbose=False # Set True untuk melihat "pikiran" agent
    )
    try:
        result = agent_executor.invoke({"input": question})
        return result.get("output", "Tidak ada data yang ditemukan di database.")
    except Exception as e:
        print(f"SQL_TOOL: Gagal menjalankan SQL Agent: {e}")
        return "Gagal mengambil data dari database sensor."

# --- Template Prompt Utama (Hybrid) ---
hybrid_template = """
Anda adalah Mubarok, asisten pertanian virtual yang ahli. Tugas Anda adalah mensintesis semua informasi yang tersedia untuk memberikan jawaban yang akurat dan mudah dimengerti.

Aturan Anda:
1. JANGAN PERNAH ulangi perkenalan. Langsung jawab pertanyaan pengguna.
2. Gunakan Riwayat Percakapan untuk memahami konteks.
3. Prioritaskan data dari 'Konteks Database (SQL)' untuk menjawab pertanyaan spesifik (misal: "berapa nilai terakhir?").
4. Gunakan 'Konteks Ringkasan/Dokumen' untuk menjawab pertanyaan tentang tren, rata-rata, atau pengetahuan umum.

Riwayat Percakapan:
{history}

Konteks Database (SQL - Realtime):
{sql_context}

Konteks Ringkasan/Dokumen (Vector DB):
{vector_context}

Pertanyaan Pengguna: {input}

Jawaban Akhir Anda (sintesis dari semua konteks):
"""
hybrid_prompt_template = PromptTemplate(
    input_variables=["history", "sql_context", "vector_context", "input"],
    template=hybrid_template
)

def get_rag_response(question: str, db_collection, chat_id: str):
    """
    Menjawab pertanyaan pengguna menggunakan pendekatan RAG hibrida.
    """
    print(f"HYBRID_RAG: Menerima pertanyaan dari {chat_id} -> '{question}'")
    memory = get_or_create_memory(chat_id)

    # 1. Dapatkan konteks presisi dari Database SQL
    sql_context = get_sql_context(question)
    
    # 2. Dapatkan konteks ringkasan/pengetahuan dari Vector Store
    vector_context_list = vector_store_service.search_db(question, db_collection, n_results=3)
    vector_context = "\n".join(vector_context_list)

    # 3. Jalankan LLMChain utama dengan semua konteks
    conversation_chain = LLMChain(
        llm=llm,
        prompt=hybrid_prompt_template,
        memory=memory
    )

    answer = conversation_chain.predict(
        input=question,
        sql_context=sql_context,
        vector_context=vector_context or "Tidak ada pengetahuan tambahan dari dokumen atau ringkasan."
    )
    return answer

# --- Fungsi Tambahan (Dipertahankan) ---

def summarize_text(text_chunk: str) -> str:
    """Meringkas sebuah potongan teks menggunakan LLM."""
    print("LANGCHAIN_SUMMARIZER: Memulai proses peringkasan...")
    template = "Anda adalah asisten ahli ringkasan. Buat ringkasan singkat (2-3 kalimat) dari teks berikut dalam Bahasa Indonesia:\n\nTeks:\n{text}\n\nRingkasan Singkat:"
    prompt = PromptTemplate.from_template(template)
    summarizer_chain = LLMChain(llm=llm, prompt=prompt)
    summary = summarizer_chain.run(text=text_chunk)
    return summary

def get_latest_summary(db_collection):
    """Membuat ringkasan kondisi terkini dengan bertanya ke diri sendiri."""
    print("RAG_SUMMARY: Membuat ringkasan kondisi greenhouse terbaru...")
    summary_question = "Berikan saya ringkasan kondisi greenhouse terkini berdasarkan data pH, TDS, dan cuaca terakhir."
    
    dummy_chat_id = "summary_task"
    if dummy_chat_id in conversation_memory_store:
        del conversation_memory_store[dummy_chat_id]

    summary = get_rag_response(summary_question, db_collection, dummy_chat_id)
    return summary
