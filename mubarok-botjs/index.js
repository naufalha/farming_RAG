// wawebjs/index.js
// --- Versi Final dengan Notifikasi File & Pengiriman Gambar Interaktif ---

const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const fs = require('fs');
const path = require('path');
const qrcode = require('qrcode-terminal');
const axios = require('axios');

console.log('🚀 Inisialisasi Mubarok Assistant...');

// --- Inisialisasi WA Client ---
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

client.on('qr', qr => {
    console.log('� Pindai QR Code di bawah ini:');
    qrcode.generate(qr, { small: true });
});

client.on('authenticated', () => {
    console.log('✅ Autentikasi berhasil!');
});

client.on('ready', () => {
    console.log('✅ Mubarok Assistant siap menerima perintah!');
});

client.on('auth_failure', msg => {
    console.error('❌ Autentikasi gagal:', msg);
});

// --- Logika Utama: Penerima Pesan WA dari User (Interaktif) ---
client.on('message', async (message) => {
    if (message.from === 'status@broadcast' || message.isStatus || message.fromMe) return;

    const userNumber = message.from;
    const chat = await message.getChat();

    try {
        await chat.sendStateTyping();

        // 1. Jika pesan berisi media (gambar atau PDF)
        if (message.hasMedia) {
            const media = await message.downloadMedia();
            
            // a. Jika media adalah PDF, proses sebagai penambah pengetahuan
            if (media && media.mimetype === 'application/pdf' && message.type === 'document') {
                console.log(`[📄 PDF Diterima] dari ${userNumber}`);
                await message.reply('📄 Menerima dokumen, sedang diproses...');
                const res = await axios.post('http://localhost:5000/upload-pdf-wa', { pdf_data: media.data });
                await message.reply(res.data.answer);
            } 
            // b. Jika media adalah gambar, proses sebagai analisis tanaman
            else if (media && message.type === 'image') {
                console.log(`[🖼️ Gambar Diterima] dari ${userNumber}`);
                await message.reply('🧠 Sedang menganalisis gambar...');
                const res = await axios.post('http://localhost:5000/analyze-image', {
                    image_data: media.data,
                    chat_id: userNumber
                });
                await message.reply(res.data.answer);
            }
        } 
        // 2. Jika pesan adalah teks biasa, proses sebagai pertanyaan ke RAG
        else {
            const userQuestion = message.body;
            console.log(`[💬 Teks Diterima] dari ${userNumber}: "${userQuestion}"`);
            const res = await axios.post('http://localhost:5000/ask', {
                question: userQuestion,
                chat_id: userNumber
            });

            // --- Logika Pengiriman Gambar Interaktif ---
            const responseData = res.data;
            if (responseData.type === 'image' && responseData.imageData) {
                const media = new MessageMedia('image/jpeg', responseData.imageData, 'response.jpg');
                await client.sendMessage(message.from, media, { caption: responseData.caption });
                console.log(`[📤 Gambar Interaktif Dikirim] ke ${userNumber}`);
            } else {
                await message.reply(responseData.answer);
            }
        }

    } catch (err) {
        console.error(`[❌ ERROR] Gagal proses pesan dari ${userNumber}:`, err.message);
        await message.reply('⚠️ Maaf, sedang ada gangguan. Coba sebentar lagi ya.');
    } finally {
        await chat.clearState();
    }
});


// --- Logika Notifikasi Otomatis via File notif.txt (Proaktif) ---
const notifFile = path.join(__dirname, 'notif.txt');

setInterval(() => {
    if (fs.existsSync(notifFile)) {
        const content = fs.readFileSync(notifFile, 'utf-8').trim();
        const [to, text, imagePath] = content.split('|');

        if (!to || !text) {
            console.error('❌ Format notif.txt tidak valid. Menghapus file...');
            fs.unlinkSync(notifFile);
            return;
        }

        const chatId = `${to.replace('+', '')}@c.us`;

        const sendNotif = async () => {
            try {
                console.log(`NOTIFIKASI: Memproses perintah dari notif.txt untuk ${to}...`);
                if (imagePath && fs.existsSync(imagePath)) {
                    // Mengirim gambar dari path file lokal untuk laporan rutin
                    const media = MessageMedia.fromFilePath(imagePath);
                    await client.sendMessage(chatId, media, { caption: text });
                    console.log(`📤 Laporan bergambar berhasil dikirim ke ${to}`);
                } else {
                    await client.sendMessage(chatId, text);
                    console.log(`📤 Laporan teks berhasil dikirim ke ${to}`);
                }
                fs.unlinkSync(notifFile); // Hapus file setelah terkirim
            } catch (err) {
                console.error('❌ Gagal kirim notifikasi dari file:', err.message);
            }
        };

        sendNotif();
    }
}, 5000); // Mengecek setiap 5 detik

// --- Jalankan WA Client ---
client.initialize();
