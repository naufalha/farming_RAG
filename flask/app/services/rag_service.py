# app/services/rag_service.py
# --- Versi 4: Menggunakan Agent yang bisa memilih antara InfluxDB dan Vector DB ---

import os
from . import influxdb_service, vector_store_service
from datetime import datetime

# Import komponen yang dibutuhkan untuk Agent
from langchain_openai import ChatOpenAI
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

# Alat 1: InfluxDB Query Tool
def query_influxdb(question: str) -> str:
    """
    Menggunakan LLM untuk menerjemahkan pertanyaan bahasa alami menjadi kueri Flux,
    menjalankannya di InfluxDB, dan mengembalikan hasilnya sebagai teks.
    """
    print(f"INFLUX_TOOL: Menerjemahkan pertanyaan ke kueri Flux -> '{question}'")
    
    flux_prompt_template = """
    Anda adalah seorang ahli bahasa kueri Flux untuk InfluxDB.
    Berdasarkan pertanyaan pengguna dan skema database, buatlah satu kueri Flux yang paling sesuai.
    Hanya kembalikan kueri Flux saja, tanpa penjelasan tambahan.

    Skema Database:
    - Measurement `ph_logs`: fields(value, temperature), tags(location)
    - Measurement `tds_logs`: fields(value, temperature), tags(location)
    - Measurement `dht_logs`: fields(air_temperature, air_humidity), tags(location)
    - Measurement `plant_conditions`: fields(diagnosis, image_url), tags(plant_id, condition)
    
    Contoh:
    Pertanyaan: Berapa nilai pH terakhir?
    Kueri Flux: from(bucket: "smart_farm_data") |> range(start: -1d) |> filter(fn: (r) => r._measurement == "ph_logs") |> last() |> keep(columns: ["_value"])

    Pertanyaan: {question}
    Kueri Flux:
    """
    prompt = PromptTemplate.from_template(flux_prompt_template)
    flux_chain = LLMChain(llm=llm, prompt=prompt)
    
    # PERBAIKAN: Menggunakan .invoke() dan mengambil hasil 'text'
    flux_query_result = flux_chain.invoke({"question": question})
    flux_query = flux_query_result.get('text', '').strip()
    
    print(f"INFLUX_TOOL: Kueri Flux yang dibuat ->\n{flux_query}")

    try:
        # --- PERBAIKAN UTAMA: Membuat query_api dari klien yang sudah ada ---
        if not influxdb_service.client:
            return "Koneksi ke database InfluxDB belum siap."

        query_api = influxdb_service.client.query_api()
        tables = query_api.query(flux_query, org=influxdb_service.INFLUX_ORG)
        
        results = []
        for table in tables:
            for record in table.records:
                time_str = record.get_time().strftime('%Y-%m-%d %H:%M:%S')
                field = record.get_field()
                value = record.get_value()
                results.append(f"Pada {time_str}, tercatat {field} = {value}")
        
        return "\n".join(results) if results else "Tidak ada data yang ditemukan untuk pertanyaan tersebut."
    except Exception as e:
        print(f"INFLUX_TOOL: Gagal menjalankan kueri Flux: {e}")
        return "Gagal mengambil data dari database sensor."

influxdb_tool = Tool(
    name="database_sensor_influxdb",
    func=query_influxdb,
    description="Gunakan alat ini untuk menjawab pertanyaan tentang data sensor spesifik (pH, TDS, suhu, kelembapan) dan kondisi tanaman dari database InfluxDB. Sangat baik untuk data terbaru, rata-rata, min/max."
)

# Alat 2: Vector Store Retriever
def vector_search(query: str, db_collection):
    print(f"VECTOR_TOOL: Mencari pengetahuan untuk -> '{query}'")
    return "\n".join(vector_store_service.search_db(query, db_collection, n_results=3))

def create_vector_tool(db_collection):
    return Tool(
        name="database_pengetahuan_pdf",
        func=lambda query: vector_search(query, db_collection),
        description="Gunakan alat ini untuk menjawab pertanyaan umum, teoritis, atau berdasarkan dokumen pengetahuan (PDF) dan ringkasan data yang telah di-upload."
    )

# --- Prompt Utama untuk Router Agent ---
MAIN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", f"""
    Anda adalah Rifai, asisten AI spesialis hidroponik Pakcoy. Pilih alat yang paling tepat untuk menjawab pertanyaan. Waktu saat ini: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.
    - Untuk pertanyaan tentang data sensor real-time (pH, TDS, suhu), kondisi tanaman, atau agregasi data (rata-rata, min, max), gunakan `database_sensor_influxdb`.
    - Untuk pertanyaan tentang pengetahuan umum, panduan dari dokumen, atau ringkasan cuaca, gunakan `database_pengetahuan_pdf`.
    - Jika pengguna meminta foto, gunakan `database_sensor_influxdb` untuk mencari path gambar di measurement `plant_conditions`. Jawaban akhir Anda HARUS HANYA path file tersebut saja.
    """),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# --- Fungsi Utama ---
def get_rag_response(question: str, db_collection, chat_id: str):
    memory = get_or_create_memory(chat_id)
    tools = [influxdb_tool, create_vector_tool(db_collection)]
    
    agent = create_openai_tools_agent(llm, tools, MAIN_PROMPT)
    agent_executor = AgentExecutor(
        agent=agent, tools=tools, verbose=True, memory=memory, handle_parsing_errors=True
    )
    try:
        result = agent_executor.invoke({"input": question})
        return result.get("output", "Maaf, saya tidak dapat menemukan jawaban.")
    except Exception as e:
        print(f"ROUTER_AGENT: Gagal menjalankan agent: {e}")
        return "Maaf, terjadi kesalahan saat saya memproses permintaan Anda."

# --- Fungsi Tambahan (Dipertahankan) ---
def summarize_text(text_chunk: str) -> str:
    print("LANGCHAIN_SUMMARIZER: Memulai proses peringkasan...")
    template = "Anda adalah asisten ahli ringkasan. Buat ringkasan singkat (2-3 kalimat) dari teks berikut dalam Bahasa Indonesia:\n\nTeks:\n{text}\n\nRingkasan Singkat:"
    prompt = PromptTemplate.from_template(template)
    summarizer_chain = LLMChain(llm=llm, prompt=prompt)
    try:
        # PERBAIKAN: Menggunakan .invoke()
        summary_result = summarizer_chain.invoke({"text": text_chunk})
        return summary_result.get('text', 'Gagal membuat ringkasan.')
    except Exception as e:
        print(f"LANGCHAIN_SUMMARIZER: Gagal membuat ringkasan: {e}")
        return "Gagal membuat ringkasan dokumen."

def get_greenhouse_summary_for_report(app_context):
    print("RAG_SUMMARY: Membuat ringkasan kondisi greenhouse terbaru...")
    summary_question = "Berikan saya ringkasan kondisi greenhouse terkini berdasarkan data pH, TDS, dan cuaca terakhir."
    
    with app_context.app_context():
        db_collection = vector_store_service.setup_vector_store()
        dummy_chat_id = "summary_task"
        if dummy_chat_id in conversation_memory_store:
            del conversation_memory_store[dummy_chat_id]
        
        summary = get_rag_response(summary_question, db_collection, dummy_chat_id)
        return summary
