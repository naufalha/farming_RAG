// wawebjs/index.js
// --- WhatsApp Bridge Service dengan Logika yang Disempurnakan ---

const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const express = require('express');
const bodyParser = require('body-parser');
const axios = require('axios');

console.log('Inisialisasi WhatsApp Bridge...');

// --- Konfigurasi ---
const app = express();
const port = 3000;
const TAGLINE_START = '#rifai';
const TAGLINE_END = '#end';
const TAGLINE_PDF = '#pdf';
const IGNORE_WORDS = [
    'iya', 'siap', 'okey', 'oke', 'ok', '👍', '👍👍', '👍👍👍', 'halo',
    'terima kasih', 'makasih', 'terimakasih', 'mksh', 'sip', 'mantap', 'betul', 'nggih'
];
app.use(bodyParser.json({ limit: '50mb' })); // Naikkan limit untuk payload gambar

// --- Manajemen Sesi dan Timer ---
const activeConversations = new Set();
const conversationTimers = new Map();

function endConversation(userNumber) {
    if (activeConversations.has(userNumber)) {
        activeConversations.delete(userNumber);
        if (conversationTimers.has(userNumber)) {
            clearTimeout(conversationTimers.get(userNumber));
            conversationTimers.delete(userNumber);
        }
        console.log(`[Percakapan Diakhiri] dengan ${userNumber}`);
    }
}

function resetConversationTimeout(userNumber, client) {
    if (conversationTimers.has(userNumber)) {
        clearTimeout(conversationTimers.get(userNumber));
    }
    const timeoutId = setTimeout(async () => {
        try {
            const chat = await client.getChatById(userNumber);
            await chat.sendMessage('Sesi percakapan telah berakhir karena tidak ada aktivitas. Panggil "#rifai" lagi jika butuh bantuan. Terima kasih! 😊');
            endConversation(userNumber);
            console.log(`[Sesi Timeout] untuk ${userNumber}`);
        } catch (error) {
            console.error(`[Error] Gagal mengirim pesan timeout untuk ${userNumber}:`, error);
        }
    }, 600000); // 10 menit
    conversationTimers.set(userNumber, timeoutId);
    console.log(`[Timer Disetel] untuk ${userNumber} selama 10 menit.`);
}

// --- Inisialisasi WhatsApp Client ---
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: { args: ['--no-sandbox', '--disable-setuid-sandbox'] }
});

client.on('qr', qr => qrcode.generate(qr, { small: true }));
client.on('ready', () => console.log('WhatsApp Client Siap Menerima Perintah!'));

// --- Logika Utama Penerima Pesan ---
client.on('message', async (message) => {
    if (message.from === 'status@broadcast' || message.isStatus || message.fromMe) return;

    const userNumber = message.from;

    // --- LOGIKA PENANGANAN MEDIA (GAMBAR & PDF) ---
    if (message.hasMedia) {
        const caption = message.body ? message.body.trim().toLowerCase() : '';
        const chat = await message.getChat();

        // 1. Penanganan Dokumen PDF
        if (message.type === 'document' && caption === TAGLINE_PDF) {
            console.log(`[PDF Diterima] dari ${userNumber}`);
            try {
                await chat.sendStateTyping();
                await message.reply('Menerima dokumen, sedang memproses... Mohon tunggu sebentar.');
                const media = await message.downloadMedia();

                if (media.mimetype !== 'application/pdf') {
                    await message.reply('Maaf, saya hanya bisa memproses file dengan format PDF.');
                    return;
                }

                const response = await axios.post('http://localhost:5000/upload-pdf-wa', { pdf_data: media.data });
                await message.reply(response.data.answer);
            } catch (error) {
                console.error('[Error] Gagal memproses PDF:', error.message);
                await message.reply('Maaf, terjadi kesalahan saat memproses dokumen Anda.');
            } finally {
                await chat.clearState();
            }
            return; // Hentikan proses setelah menangani PDF
        }

        // 2. Penanganan Gambar selama sesi aktif
        if (message.type === 'image' && activeConversations.has(userNumber)) {
            console.log(`[Gambar Diterima] dari ${userNumber} untuk dianalisis.`);
            try {
                await chat.sendStateTyping();
                await message.reply('Menerima gambar, sedang menganalisis...');
                const media = await message.downloadMedia();
                
                const response = await axios.post('http://localhost:5000/analyze-image', {
                    image_data: media.data,
                    chat_id: userNumber
                });

                await message.reply(response.data.answer);
                resetConversationTimeout(userNumber, client);
            } catch (error) {
                console.error('[Error] Gagal menganalisis gambar:', error.message);
                await message.reply('Maaf, terjadi kesalahan saat menganalisis gambar Anda.');
            } finally {
                await chat.clearState();
            }
            return; // Hentikan proses setelah menangani gambar
        }
    }

    // --- LOGIKA PENANGANAN PESAN TEKS ---
    const userMessage = message.body.trim().toLowerCase();

    // Prioritas 1: Mengakhiri Percakapan
    if (userMessage === TAGLINE_END) {
        if (activeConversations.has(userNumber)) {
            await message.reply('Baik, percakapan diakhiri. Sampai jumpa lagi!');
            endConversation(userNumber);
        }
        return;
    }

    // Prioritas 2: Memulai Percakapan
    if (userMessage === TAGLINE_START) {
        activeConversations.add(userNumber);
        console.log(`[Percakapan Dimulai] dengan ${userNumber}`);
        const chat = await message.getChat();
        await chat.sendStateTyping();
        await message.reply('Halo, saya Rifai asisten pertanian virtual dari Mubarok Farm.kamu bisa upload gambar tanaman untuk saya analisis atau upload file pdf untuk pengetahuan baru saya dengan #pdf disertai file pdfnya, Saya sedang mengambil data terbaru, mohon tunggu...');

        try {
            const response = await axios.get('http://localhost:5000/summary');
            await chat.sendMessage(response.data.summary);
            await chat.sendMessage('Ada lagi yang bisa saya bantu?');
            resetConversationTimeout(userNumber, client);
        } catch (error) {
            console.error(`[Error] Gagal mendapatkan ringkasan: ${error.message}`);
            await message.reply('Maaf, ada kendala saat mengambil data ringkasan.');
        } finally {
            await chat.clearState();
        }
        return;
    }

    // Prioritas 3: Memproses Pesan dalam Sesi Aktif
    if (activeConversations.has(userNumber)) {
        if (IGNORE_WORDS.includes(userMessage)) {
            console.log(`[Pesan Diabaikan] dari ${userNumber}: "${userMessage}"`);
            return;
        }
        resetConversationTimeout(userNumber, client);
        try {
            const chat = await message.getChat();
            await chat.sendStateTyping();
            const response = await axios.post('http://localhost:5000/ask', {
                question: message.body,
                chat_id: userNumber
            });
            await message.reply(response.data.answer);
            await chat.clearState();
        } catch (e) {
            console.error(`[Error] Gagal memanggil /ask: ${e.message}`);
            await message.reply('Maaf, sistem sedang sibuk.');
        }
    }
});

client.initialize();
app.listen(port, () => console.log(`Layanan notifikasi berjalan di port ${port}`));
