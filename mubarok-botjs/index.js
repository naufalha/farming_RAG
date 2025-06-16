// wawebjs/index.js
// --- Versi Final dengan Deteksi Otomatis untuk Semua Pesan ---

const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');

console.log('Inisialisasi Mubarok Assistant...');

// --- Konfigurasi ---
const app = express();
const port = 3000;
// Payload gambar bisa besar, jadi kita naikkan limitnya
app.use(bodyParser.json({ limit: '50mb' }));

// --- Inisialisasi Klien WhatsApp ---
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: { 
        headless: true, // Jalankan tanpa antarmuka browser
        args: ['--no-sandbox', '--disable-setuid-sandbox'] 
    }
});

client.on('qr', qr => {
    console.log('--- Pindai QR Code di bawah ini dengan WhatsApp Anda ---');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('Mubarok Assistant siap menerima perintah!');
});

client.on('authenticated', () => {
    console.log('Autentikasi Berhasil!');
});

client.on('auth_failure', msg => {
    console.error('AUTENTIKASI GAGAL', msg);
});

// --- Logika Utama Penerima Pesan ---
client.on('message', async (message) => {
    // Abaikan pesan dari status, broadcast, atau dari bot itu sendiri
    if (message.from === 'status@broadcast' || message.isStatus || message.fromMe) {
        return;
    }

    const userNumber = message.from;
    const chat = await message.getChat();

    // --- LOGIKA UTAMA: Deteksi Tipe Pesan ---
    try {
        await chat.sendStateTyping();

        // 1. Jika pesan berisi media (gambar atau PDF)
        if (message.hasMedia) {
            const media = await message.downloadMedia();

            // a. Jika media adalah PDF
            if (media && media.mimetype === 'application/pdf' && message.type === 'document') {
                console.log(`[PDF Diterima] dari ${userNumber}`);
                await message.reply('Menerima dokumen, sedang memproses untuk menambah pengetahuan...');
                const response = await axios.post('http://localhost:5000/upload-pdf-wa', { pdf_data: media.data });
                await message.reply(response.data.answer);
            } 
            // b. Jika media adalah gambar
            else if (media && message.type === 'image') {
                console.log(`[Gambar Diterima] dari ${userNumber} untuk dianalisis.`);
                await message.reply('Menerima gambar, sedang menganalisis...');
                const response = await axios.post('http://localhost:5000/analyze-image', {
                    image_data: media.data,
                    chat_id: userNumber
                });
                await message.reply(response.data.answer);
            }
        } 
        // 2. Jika pesan adalah teks biasa
        else {
            const userQuestion = message.body;
            console.log(`[Pesan Teks Diterima] dari ${userNumber}: "${userQuestion}"`);
            const response = await axios.post('http://localhost:5000/ask', {
                question: userQuestion,
                chat_id: userNumber
            });
            await message.reply(response.data.answer);
        }

    } catch (error) {
        console.error(`[Error] Gagal memproses pesan dari ${userNumber}:`, error.message);
        await message.reply('Maaf, Mubarok sedang mengalami sedikit gangguan. Coba beberapa saat lagi ya.');
    } finally {
        // Hentikan status "sedang mengetik..."
        await chat.clearState();
    }
});

// Endpoint untuk menerima notifikasi proaktif dari Flask (jika diperlukan nanti)
app.post('/send-notification', async (req, res) => {
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

// Mulai inisialisasi klien WhatsApp dan server API
client.initialize();
app.listen(port, () => console.log(`Layanan notifikasi berjalan di port ${port}`));
