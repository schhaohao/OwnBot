const { default: makeWASocket, DisconnectReason, useMultiFileAuthState, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const qrcode = require('qrcode-terminal');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');
const pino = require('pino');

const PORT = process.env.PORT || 3001;
const AUTH_DIR = process.env.AUTH_DIR || './auth_info';
const PROXY_URL = process.env.PROXY_URL || null;  // e.g., http://127.0.0.1:7890

// Ensure auth directory exists
if (!fs.existsSync(AUTH_DIR)) {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
}

let sock = null;
let wss = null;
let clients = new Set();

// Create a simple logger
const logger = pino({ level: 'silent' });

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

    // Fetch latest version info
    const { version, isLatest } = await fetchLatestBaileysVersion();
    console.log(`Using Baileys version: ${version}, isLatest: ${isLatest}`);

    // Configure socket options
    const socketConfig = {
        version,
        auth: state,
        printQRInTerminal: false,
        // Add browser info to make it look more like a real browser
        browser: ['Chrome (MacOS)', '', ''],
        // Sync full history on first connect
        syncFullHistory: false,
        // Logger
        logger: logger
    };

    // Add proxy if configured
    if (PROXY_URL) {
        console.log(`Using proxy: ${PROXY_URL}`);
        const { HttpsProxyAgent } = require('https-proxy-agent');
        socketConfig.agent = new HttpsProxyAgent(PROXY_URL);
    }

    sock = makeWASocket(socketConfig);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log('╔════════════════════════════════════════════════════════╗');
            console.log('║              SCAN QR CODE WITH WHATSAPP                ║');
            console.log('║  Open WhatsApp → Settings → Linked Devices → Link      ║');
            console.log('╚════════════════════════════════════════════════════════╝');
            qrcode.generate(qr, { small: true });

            // Notify all connected clients
            broadcast({ type: 'qr', message: 'Scan QR code to connect' });
        }

        if (connection === 'close') {
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

            console.log('Connection closed due to:', lastDisconnect?.error?.message || 'Unknown error');
            console.log('Status code:', statusCode);
            console.log('Reconnecting:', shouldReconnect);

            broadcast({
                type: 'status',
                status: 'disconnected',
                message: lastDisconnect?.error?.message || 'Connection closed',
                code: statusCode
            });

            if (shouldReconnect) {
                setTimeout(connectToWhatsApp, 5000);
            }
        } else if (connection === 'open') {
            console.log('╔════════════════════════════════════════════════════════╗');
            console.log('║     WhatsApp connection opened successfully!           ║');
            console.log('║     You can now receive and send messages              ║');
            console.log('╚════════════════════════════════════════════════════════╝');
            broadcast({ type: 'status', status: 'connected' });
        }
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('messages.upsert', async (m) => {
        const msg = m.messages[0];
        if (!msg.message || msg.key.fromMe) return;

        const sender = msg.key.remoteJid;
        const senderName = msg.pushName || 'Unknown';

        // Extract message content
        let content = '';
        let media = [];

        if (msg.message.conversation) {
            content = msg.message.conversation;
        } else if (msg.message.extendedTextMessage) {
            content = msg.message.extendedTextMessage.text;
        } else if (msg.message.imageMessage) {
            content = '[Image Message]';
            // Download image if needed
        } else if (msg.message.videoMessage) {
            content = '[Video Message]';
        } else if (msg.message.audioMessage) {
            content = '[Voice Message]';
        } else if (msg.message.documentMessage) {
            content = '[Document Message]';
        } else {
            content = '[Unknown Message Type]';
        }

        console.log(`📨 Message from ${senderName} (${sender}): ${content.substring(0, 100)}`);

        broadcast({
            type: 'message',
            sender: sender,
            pn: sender,
            content: content,
            id: msg.key.id,
            timestamp: msg.messageTimestamp,
            isGroup: sender.endsWith('@g.us'),
            senderName: senderName,
            media: media
        });
    });

    return sock;
}

function broadcast(data) {
    const message = JSON.stringify(data);
    clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            client.send(message);
        }
    });
}

async function startServer() {
    // Start WebSocket server
    wss = new WebSocket.Server({ port: PORT });

    console.log(`WhatsApp Bridge Server running on ws://localhost:${PORT}`);

    wss.on('connection', (ws) => {
        console.log('✅ New client connected');
        clients.add(ws);

        // Send current connection status
        ws.send(JSON.stringify({
            type: 'status',
            status: sock?.user ? 'connected' : 'disconnected'
        }));

        ws.on('message', async (data) => {
            try {
                const msg = JSON.parse(data);

                if (msg.type === 'send') {
                    const { to, text } = msg;

                    if (!sock) {
                        ws.send(JSON.stringify({
                            type: 'error',
                            error: 'WhatsApp not connected'
                        }));
                        return;
                    }

                    try {
                        await sock.sendMessage(to, { text: text });
                        console.log(`📤 Sent message to ${to}: ${text.substring(0, 50)}`);
                        ws.send(JSON.stringify({
                            type: 'sent',
                            to: to,
                            success: true
                        }));
                    } catch (error) {
                        console.error('❌ Error sending message:', error);
                        ws.send(JSON.stringify({
                            type: 'error',
                            error: error.message
                        }));
                    }
                } else if (msg.type === 'auth') {
                    // Handle auth token if needed
                    console.log('🔑 Auth token received');
                }
            } catch (error) {
                console.error('❌ Error handling message:', error);
                ws.send(JSON.stringify({
                    type: 'error',
                    error: 'Invalid message format'
                }));
            }
        });

        ws.on('close', () => {
            console.log('❌ Client disconnected');
            clients.delete(ws);
        });

        ws.on('error', (error) => {
            console.error('❌ WebSocket error:', error);
            clients.delete(ws);
        });
    });

    // Connect to WhatsApp
    await connectToWhatsApp();
}

// Handle graceful shutdown
process.on('SIGINT', () => {
    console.log('\n👋 Shutting down...');
    if (wss) {
        wss.close();
    }
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\n👋 Shutting down...');
    if (wss) {
        wss.close();
    }
    process.exit(0);
});

startServer().catch(console.error);
