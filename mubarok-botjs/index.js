// wawebjs/index.js
// --- Versi Final dengan Fitur Logging Percakapan untuk Benchmark ---

const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const fs = require('fs');
const path = require('path');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

console.log('🚀 Inisialisasi Mubarok Assistant...');

// --- FUNGSI BARU: Untuk Logging ke CSV ---
const logFile = path.join(__dirname, 'conversation_log.csv');

function logConversation(userNumber, userMessage, botResponse, duration) {
    try {
        const timestamp = new Date().toISOString();
        // Membersihkan teks agar aman untuk format CSV (menghapus newline dan meng-escape tanda kutip)
        const cleanUserMessage = `"${userMessage.replace(/"/g, '""').replace(/\r?\n/g, ' ')}"`;
        const cleanBotResponse = `"${botResponse.replace(/"/g, '""').replace(/\r?\n/g, ' ')}"`;
        
        const csvRow = `${timestamp},${userNumber},${duration},${cleanUserMessage},${cleanBotResponse}\n`;

        // Buat header jika file belum ada
        if (!fs.existsSync(logFile)) {
            const header = "timestamp,user_number,processing_time_ms,user_message,bot_response\n";
            fs.writeFileSync(logFile, header);
        }

        // Tambahkan baris baru ke file
        fs.appendFileSync(logFile, csvRow);
        console.log(`[📊 LOG] Percakapan disimpan ke ${logFile}`);

    } catch (err) {
        console.error('❌ Gagal menulis ke file log CSV:', err.message);
    }
}


// --- Inisialisasi WA Client ---
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

client.on('qr', qr => { /* ... */ });
client.on('authenticated', () => { /* ... */ });
client.on('ready', () => console.log('✅ Mubarok Assistant siap menerima perintah!'));
client.on('auth_failure', msg => console.error('❌ Autentikasi gagal:', msg));


// --- Logika Utama: Penerima Pesan WA dari User ---
client.on('message', async (message) => {
    if (message.from === 'status@broadcast' || message.isStatus || message.fromMe) return;

    // --- PERUBAHAN: Mulai timer dan siapkan variabel untuk logging ---
    const startTime = Date.now();
    let botReplyText = '';

    const userNumber = message.from;
    const chat = await message.getChat();

    try {
        await chat.sendStateTyping();

        if (message.hasMedia) {
            const media = await message.downloadMedia();
            if (media && media.mimetype === 'application/pdf' && message.type === 'document') {
                await message.reply('📄 Menerima dokumen, sedang diproses...');
                const res = await axios.post('http://localhost:5000/upload-pdf-wa', { pdf_data: media.data });
                botReplyText = res.data.answer; // Simpan balasan untuk log
                await message.reply(botReplyText);
            } else if (media && message.type === 'image') {
                await message.reply('🧠 Sedang menganalisis gambar...');
                const res = await axios.post('http://localhost:5000/analyze-image', { image_data: media.data, chat_id: userNumber });
                botReplyText = res.data.answer; // Simpan balasan untuk log
                await message.reply(botReplyText);
            }
        } else {
            const userQuestion = message.body;
            const res = await axios.post('http://localhost:5000/ask', { question: userQuestion, chat_id: userNumber });
            const responseData = res.data;

            if (responseData.type === 'image' && responseData.imageData) {
                const media = new MessageMedia('image/jpeg', responseData.imageData, 'response.jpg');
                botReplyText = responseData.caption; // Simpan caption untuk log
                await client.sendMessage(message.from, media, { caption: botReplyText });
            } else {
                botReplyText = responseData.answer; // Simpan balasan untuk log
                await message.reply(botReplyText);
            }
        }
    } catch (err) {
        console.error(`[❌ ERROR] Gagal proses pesan dari ${userNumber}:`, err.message);
        botReplyText = '⚠️ Maaf, sedang ada gangguan. Coba sebentar lagi ya.'; // Catat pesan error
        await message.reply(botReplyText);
    } finally {
        await chat.clearState();
        // --- PERUBAHAN: Hitung durasi dan panggil fungsi log ---
        const duration = Date.now() - startTime;
        logConversation(userNumber, message.body, botReplyText, duration);
    }
});


// --- Logika Notifikasi Otomatis via File notif.txt (Proaktif) ---
const notifFile = path.join(__dirname, 'notif.txt');

setInterval(() => {
    if (fs.existsSync(notifFile)) {
        // ... (Logika notifikasi tidak berubah)
    }
}, 5000);

// --- Jalankan WA Client ---
client.initialize();
