// wawebjs/index.js
// --- Versi Final dengan Fitur Eksekusi Perintah Bash & Pengecekan Koneksi ---

const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const fs = require('fs');
const path = require('path');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const { exec } = require('child_process');
const express = require('express');
const bodyParser = require('body-parser');
const dns = require('dns');

// Muat .env dari direktori flask agar konfigurasi terpusat
require('dotenv').config({ path: path.resolve(__dirname, '../flask/.env') });

console.log('🚀 Inisialisasi Mubarok Assistant...');

// --- Konfigurasi ---
const TAGLINE_BASH = 'bash!';
const ADMIN_NUMBER = process.env.ADMIN_WHATSAPP_NUMBER; 

// --- PERBAIKAN: Fungsi untuk menunggu koneksi internet yang lebih tangguh ---
function waitForInternetConnection() {
    return new Promise((resolve) => {
        const checkConnection = () => {
            dns.lookup('google.com', (err) => {
                if (err && (err.code === "ENOTFOUND" || err.code === "EAI_AGAIN")) {
                    console.log('🌐 Menunggu koneksi internet... Mencoba lagi dalam 10 detik.');
                    setTimeout(checkConnection, 10000); // Coba lagi setelah 10 detik
                } else {
                    console.log('✅ Koneksi internet terdeteksi! Melanjutkan dalam 3 detik...');
                    setTimeout(() => resolve(), 3000); // Beri jeda 3 detik setelah koneksi terdeteksi
                }
            });
        };
        checkConnection();
    });
}

// --- Fungsi Utama Aplikasi ---
async function startApp() {
    const app = express();
    const port = 3000;
    app.use(bodyParser.json({ limit: '50mb' }));

    // --- PERBAIKAN: Menambahkan argumen puppeteer untuk stabilitas jaringan ---
    const client = new Client({
        authStrategy: new LocalAuth(),
        puppeteer: {
            headless: true,
            args: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process', // <- mungkin membantu di beberapa environment
                '--disable-gpu'
            ]
        }
    });

    console.log('[WA] Klien WhatsApp dikonfigurasi.');

    client.on('qr', qr => {
        console.log('📲 Pindai QR Code di bawah ini:');
        qrcode.generate(qr, { small: true });
    });

    client.on('ready', () => {
        console.log('✅ Mubarok Assistant siap menerima perintah!');
        if (!ADMIN_NUMBER) {
            console.warn('⚠️  PERINGATAN: Nomor Admin tidak diatur. Fitur bash tidak akan berfungsi.');
        } else {
            console.log(`🔒 Fitur Bash diaktifkan untuk nomor: ${ADMIN_NUMBER}`);
        }
    });
    
    client.on('authenticated', () => console.log('✅ Autentikasi berhasil!'));
    client.on('auth_failure', msg => console.error('❌ Autentikasi gagal:', msg));

    client.on('message', async (message) => {
        // ... (seluruh logika client.on('message', ...) dari versi sebelumnya tetap sama di sini)
        if (message.from === 'status@broadcast' || message.isStatus || message.fromMe) return;

        const userNumber = message.from.split('@')[0];
        const userMessage = message.body.trim();
        const chat = await message.getChat();

        if (userMessage.toLowerCase().startsWith(TAGLINE_BASH)) {
            if (userNumber !== ADMIN_NUMBER) {
                await message.reply('❌ Anda tidak memiliki izin untuk menjalankan perintah ini.');
                return;
            }
            const command = userMessage.substring(TAGLINE_BASH.length).trim();
            if (!command) {
                await message.reply('Silakan berikan perintah setelah "bash!".');
                return;
            }
            await message.reply(`⚙️ Menjalankan perintah:\n\`\`\`${command}\`\`\``);
            exec(command, (error, stdout, stderr) => {
                if (error) { message.reply(`❌ *Error:*\n\n${error.message}`); return; }
                if (stderr) { message.reply(`⚠️ *Stderr:*\n\n${stderr}`); return; }
                const output = stdout || "[Perintah berhasil tanpa output]";
                message.reply(`✅ *Hasil:*\n\n\`\`\`${output}\`\`\``);
            });
            return;
        }

        try {
            await chat.sendStateTyping();
            if (message.hasMedia) {
                const media = await message.downloadMedia();
                if (media && media.mimetype === 'application/pdf' && message.type === 'document') {
                    const res = await axios.post('http://localhost:5000/upload-pdf-wa', { pdf_data: media.data });
                    await message.reply(res.data.answer);
                } else if (media && message.type === 'image') {
                    const res = await axios.post('http://localhost:5000/analyze-image', { image_data: media.data, chat_id: message.from });
                    await message.reply(res.data.answer);
                }
            } else {
                const res = await axios.post('http://localhost:5000/ask', { question: userMessage, chat_id: message.from });
                const responseData = res.data;
                if (responseData.type === 'image' && responseData.imageData) {
                    const media = new MessageMedia('image/jpeg', responseData.imageData, 'response.jpg');
                    await client.sendMessage(message.from, media, { caption: responseData.caption });
                } else {
                    await message.reply(responseData.answer);
                }
            }
        } catch (err) {
            console.error(`[❌ ERROR] Gagal proses pesan dari ${userNumber}:`, err.message);
            await message.reply('⚠️ Maaf, sedang ada gangguan.');
        } finally {
            await chat.clearState();
        }
    });

    const notifFile = path.join(__dirname, 'notif.txt');
    setInterval(() => {
        if (fs.existsSync(notifFile)) {
            const content = fs.readFileSync(notifFile, 'utf-8').trim();
            const [to, text, imagePath] = content.split('|');
            if (!to || !text) { fs.unlinkSync(notifFile); return; }
            const chatId = `${to.replace('+', '')}@c.us`;
            const sendNotif = async () => {
                try {
                    if (imagePath && fs.existsSync(imagePath)) {
                        const media = MessageMedia.fromFilePath(imagePath);
                        await client.sendMessage(chatId, media, { caption: text });
                    } else {
                        await client.sendMessage(chatId, text);
                    }
                    fs.unlinkSync(notifFile);
                } catch (err) {
                    console.error('❌ Gagal kirim notifikasi dari file:', err.message);
                }
            };
            sendNotif();
        }
    }, 5000);

    await client.initialize();
    app.listen(port, () => console.log(`Layanan notifikasi berjalan di port ${port}`));
}

// --- Titik Masuk Utama Aplikasi ---
async function main() {
    await waitForInternetConnection();
    await startApp();
}

main();

