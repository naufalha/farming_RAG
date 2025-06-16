const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal'); // For displaying QR code in the terminal

console.log('Starting WhatsApp Web Client...');

// Initialize the client with LocalAuth
// LocalAuth saves session data to the disk, so you don't have to scan the QR code every time
const client = new Client({
    authStrategy: new LocalAuth({
        // Optional: specify a custom path for session files
        // dataPath: './.wwebjs_auth_session'
    }),
    puppeteer: {
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            // '--single-process' // Use this if you encounter issues on some systems
        ],
        // headless: false // Set to true for production, false for development (to see the browser)
    }
});

// Event: QR Code received
client.on('qr', (qr) => {
    console.log('QR RECEIVED');
    qrcode.generate(qr, { small: true }); // Display the QR code in the terminal
    console.log('Please scan the QR code with your WhatsApp app.');
});

// Event: Client is ready and connected
client.on('ready', () => {
    console.log('Client is ready! You are logged in.');
    console.log('------------------------------------');
    console.log('Waiting for 30 seconds before logging out...');

    // Set a timeout to log out after 30 seconds
    setTimeout(async () => {
        await logoutClient();
    }, 30000); // 30 seconds
});

// Event: Message received (example usage)
client.on('message', message => {
    if (message.body === '!ping') {
        message.reply('pong');
    }
});

// Event: Client disconnected
client.on('disconnected', (reason) => {
    console.log('Client was disconnected:', reason);
    console.log('Session files might have been removed.');
});

// Function to handle logout
async function logoutClient() {
    try {
        console.log('\nAttempting to log out...');
        await client.logout();
        console.log('Logged out successfully!');
        // After logout, the client instance is no longer usable.
        // You might want to exit the process or re-initialize the client if needed.
        process.exit(0); // Exit the process after successful logout
    } catch (error) {
        console.error('Error during logout:', error);
        console.error('If the session directory is locked (EPERM), you might need to delete it manually.');
        console.error('Default session directory: ./.wwebjs_auth');
        process.exit(1); // Exit with an error code
    }
}

// Initialize the client
client.initialize();
