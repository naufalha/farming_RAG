# app/services/rag_service.py
# --- Versi 3: Menggunakan Agent yang bisa memilih alat (SQL atau Vector DB) ---

import os
from . import sql_database_service, vector_store_service
from datetime import datetime

# Import komponen yang dibutuhkan untuk Agent dan fungsi lain
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain.agents import Tool, create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import LLMChain

# --- Inisialisasi Komponen ---
llm = ChatOpenAI(
    model="deepseek-chat",
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1"),
    temperature=0.1
)
db_uri = f"sqlite:///{sql_database_service.DB_PATH}"
db = SQLDatabase.from_uri(db_uri)

# --- Manajemen Memori Percakapan ---
conversation_memory_store = {}

def get_or_create_memory(chat_id: str):
    """Membuat atau mengambil memori percakapan untuk pengguna tertentu."""
    if chat_id not in conversation_memory_store:
        conversation_memory_store[chat_id] = ConversationBufferWindowMemory(
            k=5, memory_key="chat_history", return_messages=True
        )
    return conversation_memory_store[chat_id]


# --- Definisikan "Alat" yang Bisa Digunakan Agent ---

# Alat 1: SQL Agent
sql_agent_executor = create_sql_agent(llm=llm, db=db, agent_type="openai-tools", verbose=True)
sql_tool = Tool(
    name="database_pertanian_lokal",
    func=sql_agent_executor.invoke,
    description="Gunakan untuk menjawab pertanyaan tentang data sensor spesifik (pH, TDS, suhu, kelembapan), prakiraan cuaca, dan kondisi tanaman dari database internal."
)

# Alat 2: Vector Store Retriever
def vector_search(query: str, db_collection):
    print(f"VECTOR_TOOL: Mencari pengetahuan untuk -> '{query}'")
    return "\n".join(vector_store_service.search_db(query, db_collection, n_results=3))

def create_vector_tool(db_collection):
    """Membuat Tool untuk database vektor."""
    return Tool(
        name="database_pengetahuan_pdf",
        func=lambda query: vector_search(query, db_collection),
        description="Gunakan untuk menjawab pertanyaan umum, teoritis, atau mencari informasi **deskriptif** dari dokumen PDF dan **ringkasan data yang tersimpan, seperti ringkasan prakiraan cuaca harian**."
    )

# --- PERUBAHAN 1: Sapaan Perkenalan untuk Pengguna Baru ---
def get_new_user_greeting():
    """Mengembalikan teks perkenalan standar untuk pengguna baru."""
    return """Halo! Saya Rifai, asisten AI dari Mubarok Farm, siap membantu Anda mengelola greenhouse hidroponik Pakcoy.

Berikut beberapa hal utama yang bisa saya lakukan:
1.  **Analisis Kesehatan Tanaman**: Kirimkan foto tanaman Pakcoy, dan saya akan menganalisis kondisinya untuk Anda.
2.  **Tanya Jawab Data**: Tanyakan tentang data sensor terakhir, rata-rata pH, atau kondisi cuaca. Contoh: "Berapa TDS terakhir?"
3.  **Tambah Pengetahuan**: Kirimkan file PDF berisi panduan atau riset, dan saya akan mempelajarinya untuk menjawab pertanyaan Anda di masa depan.
4.  **Laporan Harian**: Secara otomatis, saya akan mengirimkan laporan inspeksi tanaman setiap pagi.

Ada yang bisa saya bantu sekarang?"""


# --- PERUBAHAN 2: Prompt Utama yang Dioptimalkan ---
MAIN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""
    Anda adalah **Rifai**, asisten AI yang merupakan seorang spesialis untuk **greenhouse hidroponik** yang fokus pada tanaman **Pakcoy**.
    Waktu saat ini adalah {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.

    Tugas utama Anda adalah menjawab pertanyaan pengguna dengan alur prioritas berikut:
    1.  **Gunakan Alat Internal Dahulu**: Selalu coba jawab pertanyaan dengan menggunakan alat yang tersedia (`database_pertanian_lokal` atau `database_pengetahuan_pdf`).
    2.  **Gunakan Pengetahuan Umum Jika Perlu**: Jika kedua alat di atas tidak memberikan hasil yang relevan, baru gunakan pengetahuan umum Anda untuk menjawab dan beritahu pengguna.

    Aturan Jawaban:
    - Selalu jawab dalam Bahasa Indonesia yang ramah dan profesional.
    - PENTING: Jika pengguna meminta foto dan Anda menemukan path file gambar, jawaban akhir Anda HARUS HANYA path file tersebut saja.
    """),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])


# --- PERUBAHAN 3: Logika Baru di Fungsi Utama ---
def get_rag_response(question: str, db_collection, chat_id: str):
    """Menjawab pertanyaan pengguna dengan logika baru untuk pengguna baru."""
    print(f"ROUTER_AGENT: Menerima pertanyaan dari {chat_id} -> '{question}'")
    
    # Cek apakah ini pengguna baru dan pertanyaannya umum
    is_new_user = chat_id not in conversation_memory_store
    help_keywords = ["apa saja", "bisa apa", "bantuan", "help", "fitur", "kamu siapa"]
    is_help_request = any(keyword in question.lower() for keyword in help_keywords)

    if is_new_user and is_help_request:
        print(f"ROUTER_AGENT: Menangani permintaan bantuan dari pengguna baru: {chat_id}")
        return get_new_user_greeting()

    # Jika bukan, lanjutkan dengan alur kerja Agent seperti biasa
    memory = get_or_create_memory(chat_id)
    tools = [sql_tool, create_vector_tool(db_collection)]
    
    agent = create_openai_tools_agent(llm, tools, MAIN_PROMPT)
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True, 
        memory=memory,
        handle_parsing_errors=True
    )

    try:
        result = agent_executor.invoke({"input": question})
        return result.get("output", "Maaf, saya tidak dapat menemukan jawaban.")
    except Exception as e:
        print(f"ROUTER_AGENT: Gagal menjalankan agent: {e}")
        return "Maaf, terjadi kesalahan saat saya memproses permintaan Anda."

# --- FUNGSI SUMMARIZE_TEXT (DITAMBAHKAN KEMBALI) ---
def summarize_text(text_chunk: str) -> str:
    """Meringkas sebuah potongan teks menggunakan LLM."""
    print("LANGCHAIN_SUMMARIZER: Memulai proses peringkasan...")
    template = """
    Anda adalah seorang asisten yang ahli membuat ringkasan.
    Berdasarkan teks berikut, buatlah satu ringkasan singkat (2-3 kalimat) yang menjelaskan isi utamanya dalam Bahasa Indonesia.

    Teks:
    {text}

    Ringkasan Singkat:
    """
    prompt = PromptTemplate.from_template(template)
    
    # Menggunakan LLMChain sederhana khusus untuk tugas ini
    summarizer_chain = LLMChain(llm=llm, prompt=prompt)
    
    try:
        summary = summarizer_chain.run(text=text_chunk)
        print(f"LANGCHAIN_SUMMARIZER: Ringkasan dibuat -> '{summary}'")
        return summary
    except Exception as e:
        print(f"LANGCHAIN_SUMMARIZER: Gagal membuat ringkasan: {e}")
        return "Gagal membuat ringkasan dokumen."
# app/services/rag_service.py
# ... (kode lain tetap sama) ...

def get_greenhouse_summary_for_report(app_context):
    """
    Membuat ringkasan kondisi greenhouse menggunakan konteks aplikasi yang diberikan.
    """
    print("RAG_SERVICE: Membuat ringkasan analitis kondisi greenhouse...")
    
    summary_question = """
    Berdasarkan data di tabel environment_logs dan weather_logs, berikan ringkasan data terbaru untuk parameter berikut: 
    pH, TDS, suhu air (water_temperature), suhu udara (air_temperature), kelembapan udara (air_humidity), dan prakiraan curah hujan (precipitation_sum).
    """
    
    try:
        # --- PERUBAHAN: Menjalankan agent di dalam konteks aplikasi ---
        with app_context.app_context():
            sql_agent_executor = create_sql_agent(
                llm=llm, db=db, agent_type="openai-tools", verbose=False
            )
            data_summary = sql_agent_executor.invoke({"input": summary_question}).get("output")
            
            analysis_prompt = f"""
            Anda adalah Mubarok, seorang ahli agronomi. Berdasarkan data berikut:
            ---
            {data_summary}
            ---
            Berikan kesimpulan singkat (2-3 kalimat) mengenai kondisi greenhouse saat ini dan dampaknya pada tanaman Pakcoy.
            """
            final_analysis = llm.invoke(analysis_prompt).content
            return final_analysis

    except Exception as e:
        print(f"RAG_SERVICE: Gagal membuat ringkasan greenhouse: {e}")
        return "Tidak dapat menganalisis kondisi greenhouse saat ini."

# (fungsi get_rag_response dan lainnya tidak perlu diubah)
# ...
