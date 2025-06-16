// wawebjs/index.js
// --- WhatsApp Bridge Service dengan Mode Percakapan ---

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios'); // Library untuk mengirim request ke Flask

console.log('Inisialisasi WhatsApp Bridge...');

// --- Konfigurasi ---
const app = express();
const port = 3000;
const TAGLINE_START = 'mubarok'; // Kata kunci untuk memulai percakapan
const TAGLINE_END = 'end';       // Kata kunci untuk mengakhiri percakapan
app.use(bodyParser.json());

// --- State Management ---
// Menggunakan Set untuk menyimpan ID chat pengguna yang sedang dalam percakapan aktif
const activeConversations = new Set();

// --- Inisialisasi WhatsApp Client ---
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

client.on('qr', qr => {
    console.log('--- SCAN QR CODE DI BAWAH INI DENGAN WHATSAPP ANDA ---');
    qrcode.generate(qr, { small: true });
});

client.on('authenticated', () => {
    console.log('Autentikasi Berhasil!');
});

client.on('ready', () => {
    console.log('WhatsApp Client Siap Menerima Perintah!');
    console.log(`Layanan Notifikasi berjalan di http://localhost:${port}`);
});

// --- LOGIKA UTAMA: MENERIMA DAN MEMBALAS PESAN ---
client.on('message', async (message) => {
    if (message.from === 'status@broadcast' || message.isStatus || message.fromMe) {
        return;
    }

    const userMessage = message.body.trim().toLowerCase();
    const userNumber = message.from;

    // --- LOGIKA PERCAKAPAN BERANTAI ---

    // 1. Cek perintah untuk memulai percakapan
    if (userMessage === TAGLINE_START) {
        activeConversations.add(userNumber);
        await message.reply('Halo, saya Mubarok. Ada yang bisa saya bantu? Untuk mengakhiri percakapan, ketik "end".');
        console.log(`[Percakapan Dimulai] dengan ${userNumber}`);
        return;
    }

    // 2. Cek perintah untuk mengakhiri percakapan
    if (userMessage === TAGLINE_END) {
        if (activeConversations.has(userNumber)) {
            activeConversations.delete(userNumber);
            await message.reply('Baik, percakapan diakhiri. Panggil "mubarok" lagi jika Anda membutuhkan bantuan.');
            console.log(`[Percakapan Diakhiri] dengan ${userNumber}`);
        }
        return;
    }

    // 3. Jika pengguna sedang dalam percakapan aktif, proses pesannya
    if (activeConversations.has(userNumber)) {
        const userQuestion = message.body; // Ambil pesan asli
        console.log(`[Pesan Masuk] dari ${userNumber}: "${userQuestion}"`);

        try {
            const chat = await message.getChat();
            await chat.sendStateTyping();

            // Kirim pertanyaan ke API Flask
            const response = await axios.post('http://localhost:5000/ask', {
                question: userQuestion
            });

            const answer = response.data.answer;
            await message.reply(answer);
            await chat.clearState();
            console.log(`[Pesan Terkirim] Balasan dikirim ke ${userNumber}`);

        } catch (error) {
            console.error('[Error] Gagal memproses permintaan:', error.message);
            await message.reply('Maaf, Mubarok sedang mengalami sedikit gangguan. Coba beberapa saat lagi ya.');
        }
    }
    // Jika tidak ada kondisi di atas yang terpenuhi, bot akan mengabaikan pesan.
});
// ----------------------------------------------------


// Endpoint untuk notifikasi dari Flask tetap ada
app.post('/send-message', async (req, res) => {
    // (Kode ini tidak perlu diubah)
    const { to, message } = req.body;
    if (!to || !message) {
        return res.status(400).json({ status: 'error', message: 'Parameter "to" dan "message" diperlukan.' });
    }
    const chatId = `${to.replace('+', '')}@c.us`;
    try {
        await client.sendMessage(chatId, message);
        res.status(200).json({ status: 'success', message: 'Notifikasi berhasil dikirim.' });
    } catch (error) {
        res.status(500).json({ status: 'error', message: 'Gagal mengirim notifikasi.' });
    }
});

client.initialize();
app.listen(port);
