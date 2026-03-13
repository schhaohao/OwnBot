from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from loguru import logger

from ownbot.agent import AgentLoop
from ownbot.bus import MessageBus
from ownbot.channels import ChannelManager
from ownbot.config import AppConfig, get_config_path, load_config, save_config, set_config_path

app = typer.Typer(no_args_is_help=True)


@app.command()
def onboard() -> None:
    """初始化配置文件（~/.ownbot/config.json）。"""
    path = save_config(AppConfig())
    typer.echo(f"已生成配置：{path}")
    typer.echo('下一步：编辑 telegram.token / telegram.allowFrom / llm.apiKey 等字段，然后运行：ownbot gateway')


@app.command()
def gateway(
    config: str | None = typer.Option(None, "--config", "-c", help="配置文件路径（默认 ~/.ownbot/config.json）"),
) -> None:
    """启动 gateway（Telegram + AgentLoop）。"""
    if config:
        set_config_path(Path(config).expanduser().resolve())

    cfg = load_config()
    bus = MessageBus()
    agent = AgentLoop(cfg=cfg, bus=bus)
    channel_manager = ChannelManager(cfg, bus)
    channel_manager.setup_channels()

    async def _run() -> None:
        logger.info("Config: {}", get_config_path())
        await asyncio.gather(
            agent.run(),
            channel_manager.start_all(),
        )

    asyncio.run(_run())


@app.command()
def channels(
    action: str = typer.Argument(..., help="操作：login / status"),
    channel: str = typer.Option(None, "--channel", "-c", help="通道名称，如 whatsapp"),
    config: str | None = typer.Option(None, "--config", "-f", help="配置文件路径（默认 ~/.ownbot/config.json）"),
) -> None:
    """管理通道，如登录 WhatsApp。"""
    if config:
        set_config_path(Path(config).expanduser().resolve())

    cfg = load_config()
    bus = MessageBus()

    if action == "login":
        if channel == "whatsapp":
            typer.echo("正在启动 WhatsApp 登录...")
            
            # 检查并启动 bridge 服务器
            import subprocess
            import os
            import time
            
            bridge_dir = Path(__file__).parent.parent / "bridge"
            if not bridge_dir.exists():
                typer.echo("创建 bridge 服务器目录...")
                bridge_dir.mkdir(parents=True, exist_ok=True)
                
                # 创建 package.json
                package_json = bridge_dir / "package.json"
                package_json.write_text('''{
  "name": "ownbot-whatsapp-bridge",
  "version": "1.0.0",
  "description": "WhatsApp bridge server for OwnBot",
  "main": "server.js",
  "scripts": {
    "start": "node server.js"
  },
  "dependencies": {
    "@whiskeysockets/baileys": "^6.7.18",
    "ws": "^8.14.2",
    "qrcode-terminal": "^0.12.0"
  }
}''')
                
                # 创建 server.js
                server_js = bridge_dir / "server.js"
                server_js.write_text('''const { default: makeWASocket, useMultiFileAuthState, Browsers, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const http = require('http');
const WebSocket = require('ws');
const fs = require('fs');
const path = require('path');
const qrcode = require('qrcode-terminal');

// Create HTTP server
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('OwnBot WhatsApp Bridge Server');
});

// Create WebSocket server
const wss = new WebSocket.Server({ server });

wss.on('connection', async (ws) => {
  console.log('Client connected');

  // Load auth state
  const authDir = path.join(__dirname, 'auth');
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }

  const { state, saveCreds } = await useMultiFileAuthState(authDir);
  const { version } = await fetchLatestBaileysVersion();

  // Create WhatsApp socket
  const sock = makeWASocket({
    version,
    auth: state,
    browser: Browsers.macOS('Chrome')
  });

  // 统一事件处理
  setupSockEvents(sock, ws, saveCreds);

  // Handle messages from WS client
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      if (data.type === 'send') {
        sock.sendMessage(data.to, { text: data.text });
      } else if (data.type === 'auth') {
        console.log('Auth token received:', data.token);
      }
    } catch (error) {
      console.error('Error processing message:', error);
    }
  });

  ws.on('close', () => {
    console.log('Client disconnected');
    sock.close();
  });
});

server.listen(3001, () => {
  console.log('OwnBot WhatsApp Bridge Server running on port 3001');
  console.log('WebSocket URL: ws://localhost:3001');
});

// -------------------- 统一事件处理函数 --------------------
function setupSockEvents(sock, ws, saveCreds) {
  const authDir = path.join(__dirname, 'auth');

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log('=======================================');
      console.log('Scan this QR code with WhatsApp:');
      console.log('=======================================');
      qrcode.generate(qr, { small: false });
      console.log('=======================================');
      ws.send(JSON.stringify({ type: 'qr', qr }));
    }

    if (connection === 'close') {
      const shouldReconnect = lastDisconnect.error?.output?.statusCode !== 401;
      console.log('Connection closed', shouldReconnect ? 'reconnecting...' : 'not reconnecting');
      if (shouldReconnect) {
        setTimeout(async () => {
          const { state, saveCreds } = await useMultiFileAuthState(authDir);
          const newSock = makeWASocket({
            auth: state,
            browser: Browsers.macOS('Chrome')
          });
          setupSockEvents(newSock, ws, saveCreds);
        }, 5000);
      }
    } else if (connection === 'open') {
      console.log('Connected to WhatsApp');
      ws.send(JSON.stringify({ type: 'status', status: 'connected' }));
    }
  });

  sock.ev.on('messages.upsert', async ({ messages }) => {
    for (const msg of messages) {
      if (!msg.key.fromMe) {
        const content = msg.message.conversation ||
                        msg.message.extendedTextMessage?.text ||
                        '[Voice Message]';

        const media = [];
        if (msg.message.imageMessage) {
          try {
            const buffer = await sock.downloadMediaMessage(msg.message.imageMessage);
            const fileName = `image_${Date.now()}.jpg`;
            const mediaDir = path.join(__dirname, 'media');
            if (!fs.existsSync(mediaDir)) fs.mkdirSync(mediaDir, { recursive: true });
            const filePath = path.join(mediaDir, fileName);
            fs.writeFileSync(filePath, buffer);
            media.push(filePath);
          } catch (err) {
            console.error('Error downloading media:', err);
          }
        }

        ws.send(JSON.stringify({
          type: 'message',
          sender: msg.key.remoteJid,
          content: content,
          id: msg.key.id,
          timestamp: msg.messageTimestamp,
          isGroup: msg.key.remoteJid.endsWith('@g.us'),
          media
        }));
      }
    }
  });
}''')
            
            # 检查是否安装了 Node.js
            try:
                subprocess.run(['node', '--version'], check=True, capture_output=True)
                typer.echo("Node.js 已安装")
            except subprocess.CalledProcessError:
                typer.echo("错误：未安装 Node.js，请先安装 Node.js")
                return
            
            # 安装依赖
            typer.echo("安装 bridge 服务器依赖...")
            subprocess.run(['npm', 'install'], cwd=bridge_dir, capture_output=True)
            
            # 启动 bridge 服务器
            typer.echo("启动 bridge 服务器...")
            bridge_process = subprocess.Popen(['npm', 'start'], cwd=bridge_dir)
            
            # 等待服务器启动
            typer.echo("等待 bridge 服务器启动...")
            time.sleep(3)
            
            typer.echo("扫描桥接终端中的 QR 码以登录 WhatsApp")
            
            from ownbot.channels import WhatsAppChannel
            whatsapp_channel = WhatsAppChannel(cfg.whatsapp, bus)
            
            async def _login() -> None:
                try:
                    await whatsapp_channel.start()
                except asyncio.CancelledError:
                    pass
            
            try:
                asyncio.run(_login())
            except KeyboardInterrupt:
                typer.echo("登录已取消")
            finally:
                # 停止 bridge 服务器
                bridge_process.terminate()
                bridge_process.wait()
        else:
            typer.echo(f"不支持的通道：{channel}")
    elif action == "status":
        typer.echo("通道状态：")
        typer.echo(f"Telegram: {'启用' if cfg.telegram.enabled else '禁用'}")
        typer.echo(f"WhatsApp: {'启用' if cfg.whatsapp.enabled else '禁用'}")
    else:
        typer.echo(f"不支持的操作：{action}")


