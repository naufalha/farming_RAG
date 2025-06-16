# app/services/rag_service.py
# --- Versi 3: Menggunakan Agent yang bisa memilih alat (SQL atau Vector DB) ---

import os
from . import sql_database_service, vector_store_service
from datetime import datetime

# Import komponen yang dibutuhkan untuk Agent
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain.agents import Tool, create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory

# --- Inisialisasi Komponen ---

# 1. Inisialisasi LLM menggunakan ChatOpenAI wrapper (sesuai eksperimen Anda)
llm = ChatOpenAI(
    model="deepseek-chat",
    openai_api_key=os.getenv("DEEPSEEK_API_KEY"),
    openai_api_base=os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/v1"),
    temperature=0
)

# 2. Inisialisasi koneksi database untuk LangChain
db_uri = f"sqlite:///{sql_database_service.DB_PATH}"
db = SQLDatabase.from_uri(db_uri)

# 3. Manajemen Memori Percakapan
conversation_memory_store = {}

def get_or_create_memory(chat_id: str):
    """Membuat atau mengambil memori percakapan untuk pengguna tertentu."""
    if chat_id not in conversation_memory_store:
        # Menggunakan Window Memory untuk efisiensi, hanya mengingat 5 interaksi terakhir
        conversation_memory_store[chat_id] = ConversationBufferWindowMemory(
            k=5, memory_key="chat_history", return_messages=True
        )
    return conversation_memory_store[chat_id]


# --- Definisikan "Alat" yang Bisa Digunakan Agent ---

# Alat 1: SQL Agent untuk data terstruktur (sensor, cuaca, kondisi tanaman)
sql_agent_executor = create_sql_agent(
    llm=llm,
    db=db,
    agent_type="openai-tools",
    verbose=True,
    prefix="""Anda adalah ahli kueri SQLite. Mengingat pertanyaan pengguna, buatlah kueri SQLite yang benar, jalankan, dan kembalikan hasilnya. Anda harus membatasi jumlah baris yang diambil jika tidak diminta secara spesifik."""
)
sql_tool = Tool(
    name="database_pertanian",
    func=sql_agent_executor.invoke,
    description="Gunakan alat ini untuk menjawab pertanyaan tentang data sensor spesifik (pH, TDS, suhu, kelembapan), prakiraan cuaca, dan kondisi tanaman. Alat ini bisa melakukan agregasi seperti rata-rata, nilai minimum, dan maksimum."
)

# Alat 2: Vector Store Retriever untuk pengetahuan umum/PDF
def vector_search(query: str, db_collection):
    """Fungsi pembungkus untuk pencarian di Vector DB."""
    print(f"VECTOR_TOOL: Mencari pengetahuan untuk -> '{query}'")
    return "\n".join(vector_store_service.search_db(query, db_collection, n_results=3))

def create_vector_tool(db_collection):
    """Membuat Tool untuk database vektor."""
    return Tool(
        name="database_pengetahuan_pdf",
        func=lambda query: vector_search(query, db_collection),
        description="Gunakan alat ini untuk menjawab pertanyaan umum, teoritis, atau berdasarkan dokumen pengetahuan yang telah di-upload, seperti 'bagaimana cara mengatasi jamur' atau 'apa saja gejala penyakit X'."
    )

# --- Prompt Utama untuk Router Agent ---
MAIN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""
    Anda adalah Mubarok, asisten pertanian AI yang sangat cerdas dan siap membantu. Waktu saat ini adalah {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.
    Tugas Anda adalah memilih alat yang paling tepat untuk menjawab pertanyaan pengguna.
    - Untuk pertanyaan tentang data sensor, cuaca, atau kondisi tanaman, gunakan `database_pertanian`.
    - Untuk pertanyaan tentang pengetahuan umum atau isi dokumen, gunakan `database_pengetahuan_pdf`.
    Setelah mendapatkan hasil dari alat, berikan jawaban akhir yang ramah dan jelas dalam Bahasa Indonesia.
    """),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])


# --- Fungsi Utama yang Dipanggil oleh API Route ---
def get_rag_response(question: str, db_collection, chat_id: str):
    """Menjawab pertanyaan pengguna dengan memilih alat yang paling sesuai."""
    print(f"ROUTER_AGENT: Menerima pertanyaan dari {chat_id} -> '{question}'")
    
    memory = get_or_create_memory(chat_id)
    tools = [sql_tool, create_vector_tool(db_collection)]
    
    # Membuat agent utama yang berfungsi sebagai router
    agent = create_openai_tools_agent(llm, tools, MAIN_PROMPT)
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True, 
        memory=memory,
        handle_parsing_errors=True # Penting untuk stabilitas
    )

    try:
        # Menjalankan agent dengan input dari pengguna
        result = agent_executor.invoke({"input": question})
        return result.get("output", "Maaf, saya tidak dapat menemukan jawaban.")
    except Exception as e:
        print(f"ROUTER_AGENT: Gagal menjalankan agent: {e}")
        return "Maaf, terjadi kesalahan saat saya memproses permintaan Anda."
