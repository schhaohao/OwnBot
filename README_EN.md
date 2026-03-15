<div align="center">

# 🤖 OwnBot

**Agent Development for Beginners — Minimal Code, Zero Framework, Step-by-Step Tutorial. Build Your Own OpenClaw**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?style=flat-square&logo=python)](https://www.python.org/) [![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE) [![Code Style](https://img.shields.io/badge/Code%20Style-Black-black.svg?style=flat-square)](https://github.com/psf/black) [![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg?style=flat-square)](CONTRIBUTING.md)

**English** | [中文](./README.md)

</div>

---

## ✨ Introduction

> 🎓 **A Learning Project for Agent Beginners**

**OwnBot** is a **learning project** designed specifically for **students** and **Agent technology enthusiasts**. Our goals are:

- 📚 **Help understand Agent principles** - Implement Agent Loop + ReAct architecture from scratch, without relying on any Agent development frameworks
- 💡 **Minimal and clean code** - Every line is clearly commented and easy to understand
- 🎯 **Most accessible approach** - Show Agent workflows in the most intuitive way
- 🔧 **Fully functional system** - Not just concepts, but a truly working intelligent assistant

### 🌟 Why OwnBot?

There are many Agent frameworks available (like LangChain, LangGraph, AutoGPT, etc.), but they often:

- ❌ Over-encapsulated, making underlying principles hard to understand
- ❌ Complex codebase with steep learning curves
- ❌ Too many dependencies, difficult environment setup

**OwnBot takes a completely different approach**:

- ✅ **Pure Python native implementation** - No Agent framework dependencies
- ✅ **Clean and concise code** - Core logic only 500 lines
- ✅ **Built from scratch** - From message reception to LLM calls, every step is transparent
- ✅ **Learn by doing** - Understand how Agents work while reading the code

### 👥 Who Is It For?

| Audience                                   | Benefits                                                   |
| ------------------------------------------ | ---------------------------------------------------------- |
| 🎓**AI/CS Students**                 | Understand core Agent principles, complete course projects |
| 🔬**AI Enthusiasts**                 | Build a working Agent system from scratch                  |
| 👨‍🏫**Educators**                  | Use as a best practice case for Agent teaching             |
| 🚀**Entrepreneurs/Indie Developers** | Quickly prototype personal AI assistants                   |

### 🎯 Key Features

- **🚀 Multi-Platform Support** - Support both Telegram and WhatsApp simultaneously
- **🧠 Intelligent Architecture** - Based on ReAct (Reasoning + Acting) for complex task handling
- **🛠️ Tool System** - Built-in tools for file operations, shell commands, web requests, etc.
- **📦 Skill System** - Modular skill design for easy feature extension (e.g., weather queries)
- **💾 Memory Management** - Smart session management with memory consolidation
- **⚡ Async High Performance** - Built on Python asyncio for high concurrency
- **🔧 Easy to Extend** - Clear modular design for secondary development

---

## 🚧 Project Status

> 🟢 **Actively maintained** - Project is under active development

This project is currently in **Beta stage**. Core features are functional and we're continuously iterating and improving.

> ⚠️ **Note**: As a learning project, the code may contain bugs or imperfections. If you encounter issues during use, please feel free to report them via GitHub Issues. Your feedback is invaluable for improving the project!

We welcome all forms of feedback and suggestions!

### 📋 Development Roadmap

#### ✅ Implemented

- [X] Agent Loop + ReAct core architecture
- [X] Telegram channel support
- [X] WhatsApp channel support
- [X] Basic tool system (file, shell, network)
- [X] Skill system framework
- [X] Session, memory management

#### 🚧 In Progress

- [ ] 👤 **Human-in-the-Loop** - Require human confirmation for critical operations
- [ ] 🔌 **MCP Protocol Support** - Integrate Model Context Protocol
- [ ] More comprehensive documentation and tutorials
- [ ] More built-in skills (calendar, email, etc.)

#### 📅 Planned Features

| Feature                               | Description                                                | Priority  |
| ------------------------------------- | ---------------------------------------------------------- | --------- |
| 💾**Vector Database**           | Support RAG for Agents to read local documents             | 🔴 High   |
| 📱**More Platforms**            | Support for Discord, Slack, Feishu, etc.                   | 🔴 High   |
| 🧠**Multi-Agent Collaboration** | Support multiple Agents working together to complete tasks | 🟡 Medium |
| 🎨**Web Management Interface**  | Provide visual configuration and monitoring interface      | 🟡 Medium |
| 🔊**Voice Support**             | Voice input and voice response                             | 🟢 Low    |

---

## 📸 Project Showcase

<div align="center">

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Layer                                │
│    ┌──────────────┐    ┌──────────────┐                         │
│    │   Telegram   │    │   WhatsApp   │                         │
│    └──────┬───────┘    └──────┬───────┘                         │
└───────────┼───────────────────┼─────────────────────────────────┘
            │                   │
            ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Message Bus Layer                         │
│              ┌─────────────────────────┐                        │
│              │      MessageBus         │                        │
│              │   ┌───────────────┐     │                        │
│              │   │ Inbound Queue │     │                        │
│              │   │ Outbound Queue│     │                        │
│              │   └───────────────┘     │                        │
│              └─────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
            │                   │
            ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Agent Layer                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                      AgentLoop                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │   ReAct      │  │   Context    │  │   Session    │   │  │
│  │  │   Engine     │  │   Builder    │  │   Manager    │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
            │                   │
            ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Capability Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │    Tools     │  │   Skills     │  │    LLM       │          │
│  │ (File/Shell) │  │ (Weather/Ext)│  │  (DeepSeek)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

</div>

---

## 🚀 Quick Start

### Requirements

- Python 3.10+
- Node.js 18+ (for WhatsApp support)
- macOS / Linux / Windows

### Installation

#### 1. Clone the Project

```bash
git clone https://github.com/schhaohao/OwnBot.git
cd OwnBot
```

#### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or venv\Scripts\activate  # Windows

# Install Python dependencies
pip install -e .

# Install WhatsApp Bridge dependencies
cd whatsapp-bridge && npm install && cd ..
```

#### 3. Initialize Configuration

```bash
ownbot onboard
```

This creates a default config file at `~/.ownbot/config.json`

#### 4. Edit Configuration

```bash
# Edit config file
vim ~/.ownbot/config.json
```

**Minimum Configuration Example:**

```json
{
  "adminIds": ["your_telegram_user_id"],
  "telegram": {
    "enabled": true,
    "token": "YOUR_BOT_TOKEN",
    "allowFrom": ["*"]
  },
  "whatsapp": {
    "enabled": true,
    "allowFrom": ["*"]
  },
  "llm": {
    "apiBase": "https://api.openai.com/v1",
    "apiKey": "YOUR_API_KEY",
    "model": "gpt-4",
    "temperature": 0.7,
    "maxTokens": 4096
  }
}
```

#### 5. Login to WhatsApp (if needed)

```bash
ownbot channels login --channel whatsapp
```

Scan the QR code displayed in the terminal to complete login.

#### 6. Start the Service

```bash
ownbot gateway
```

---

## 📖 Usage Guide

### Basic Conversation

Simply send messages to the bot, and it will respond intelligently:

- **Simple Chat**: `Hello`, `Introduce yourself`
- **Weather Query**: `What's the weather like in Beijing today?`
- **File Operations**: `Create a todo.txt file for me`
- **Web Search**: `Search for the latest AI news`

### Tool Usage

The bot has multiple built-in tools that can be invoked through natural language:

| Tool            | Example                             | Description             |
| --------------- | ----------------------------------- | ----------------------- |
| `list_files`  | `List files in current directory` | List directory contents |
| `read_file`   | `Read README.md`                  | Read file content       |
| `write_file`  | `Create test.txt with hello`      | Create/write file       |
| `shell`       | `Execute ls -la`                  | Execute shell commands  |
| `web_request` | `Visit https://api.github.com`    | HTTP requests           |

### Skill System

Skills are predefined functional modules placed in the `ownbot/skills/` directory:

```
ownbot/skills/
├── weather/           # Weather query skill
│   ├── SKILL.md      # Skill definition
├── translate/        # Translate skill
|   ├── SKILL.md      # Skill definition
└── your_skill/       # Your custom skill
    └── SKILL.md
```

**SKILL.md Format:**

```markdown
---
name: weather
description: Query weather information
emoji: 🌤️
---

# Weather Skill

Detailed description of the skill...
```

---

## 🏗️ System Architecture

### Core Modules

| Module                | Responsibility       | Key Classes                                             |
| --------------------- | -------------------- | ------------------------------------------------------- |
| **Channels**    | Platform integration | `TelegramChannel`, `WhatsAppChannel`                |
| **Message Bus** | Message routing      | `MessageBus`, `InboundMessage`, `OutboundMessage` |
| **Agent**       | AI core              | `AgentLoop`, `ContextBuilder`, `SessionManager`   |
| **Tools**       | Tool execution       | `ToolRegistry`, `FileSystemTool`, `ShellTool`     |
| **Skills**      | Skill management     | `SkillLoader`, `Skill`                              |
| **LLM**         | Model integration    | `LiteLLMProvider`                                     |

### Message Processing Flow

```
1. Receive
   └─ User sends message → Channel receives

2. Enqueue
   └─ Message enters MessageBus inbound queue

3. Process
   └─ AgentLoop retrieves message
      ├─ SessionManager loads/creates session
      ├─ ContextBuilder builds context (with ReAct prompt)
      ├─ LLM call (ReAct loop)
      │   ├─ Thought: Analysis
      │   ├─ Action: Tool invocation
      │   ├─ Observation: Result observation
      │   └─ Final Answer: Generate response
      └─ Save session state

4. Dequeue
   └─ Response enters MessageBus outbound queue

5. Send
   └─ Channel sends to user
```

---

## ⚙️ Configuration Details

### Full Configuration Example

```json
{
  "adminIds": ["admin_telegram_user_id"],
  "telegram": {
    "enabled": true,
    "token": "YOUR_BOT_TOKEN",
    "allowFrom": ["*"],
    "proxy": null,
    "replyToMessage": false,
    "groupPolicy": "mention"
  },
  "whatsapp": {
    "enabled": true,
    "allowFrom": ["*"],
    "bridgeUrl": "ws://localhost:3001"
  },
  "llm": {
    "apiBase": "https://api.openai.com/v1",
    "apiKey": "YOUR_API_KEY",
    "model": "gpt-4",
    "temperature": 0.1,
    "maxTokens": 8192
  }
}
```

### Configuration Options

#### Telegram Configuration

| Option             | Type    | Default   | Description                                   |
| ------------------ | ------- | --------- | --------------------------------------------- |
| `adminIds`       | array   | []        | Admin user IDs with special permissions       |
| `enabled`        | boolean | false     | Enable/disable                                |
| `token`          | string  | ""        | Bot Token (from @BotFather)                   |
| `allowFrom`      | array   | []        | Allowed user IDs,`*` for all                |
| `proxy`          | string  | null      | Proxy address, e.g.,`http://127.0.0.1:7890` |
| `replyToMessage` | boolean | false     | Quote original message in reply               |
| `groupPolicy`    | string  | "mention" | Group policy:`mention` or `open`          |

#### WhatsApp Configuration

| Option        | Type    | Default               | Description                        |
| ------------- | ------- | --------------------- | ---------------------------------- |
| `enabled`   | boolean | false                 | Enable/disable                     |
| `allowFrom` | array   | []                    | Allowed phone numbers or group IDs |
| `bridgeUrl` | string  | "ws://localhost:3001" | Bridge service URL                 |

#### LLM Configuration

| Option          | Type   | Default                     | Description                 |
| --------------- | ------ | --------------------------- | --------------------------- |
| `apiBase`     | string | "https://api.openai.com/v1" | API base URL                |
| `apiKey`      | string | ""                          | API key                     |
| `model`       | string | "gpt-4"                     | Model name                  |
| `temperature` | float  | 0.1                         | Temperature parameter (0-2) |
| `maxTokens`   | int    | 8192                        | Maximum token count         |

---

## 🛠️ Development Guide

### Project Structure

```
ownbot/
├── __init__.py
├── __main__.py           # Entry point
├── agent/                # AI core
│   ├── __init__.py
│   ├── context.py        # Context building
│   ├── loop.py          # Agent Loop + ReAct main loop
│   └── session.py       # Session management
├── bus/                  # Message bus
│   ├── __init__.py
│   ├── events.py        # Message events
│   └── queue.py         # Message queue
├── channels/             # Platform channels
│   ├── __init__.py
│   ├── base.py          # Base channel class
│   ├── telegram.py      # Telegram implementation
│   ├── whatsapp.py      # WhatsApp implementation
│   └── manager.py       # Channel manager
├── cli/                  # CLI
│   └── commands.py
├── config/               # Configuration
│   ├── __init__.py
│   └── schema.py
├── skills/               # Skill system
│   ├── loader.py
│   ├── models.py
│   └── weather/         # Example skill
├── tools/                # Tool system
│   ├── registry.py
│   └── tools.py
└── utils/                # Utilities
    └── logger.py
```

### Adding Custom Tools

```python
# ownbot/tools/tools.py

async def my_custom_tool(param1: str, param2: int = 10) -> str:
    """
    My custom tool
  
    Args:
        param1: First parameter
        param2: Second parameter, default 10
  
    Returns:
        Processing result
    """
    # Implementation logic
    return f"Result: {param1}, {param2}"

# Register tool
from ownbot.tools.registry import register_tool
register_tool("my_tool", my_custom_tool)
```

### Adding Custom Skills

1. Create skill directory: `ownbot/skills/my_skill/`
2. Create `SKILL.md`:

```markdown
---
name: my_skill
description: My custom skill
emoji: 🚀
---

# My Skill

Detailed description here...
```

#### Example: Creating a "Translate" Skill

**Step 1: Create skill directory**

```bash
mkdir -p ownbot/skills/translate
```

**Step 2: Create SKILL.md file**

Create file `ownbot/skills/translate/SKILL.md`:

```markdown
---
name: translate
description: Translate text (supports multiple languages)
homepage: https://translate.google.com
metadata:
  ownbot:
    emoji: "🌐"
    requires:
      bins: ["curl"]
---

# Translate Skill

Use Google Translate for text translation, supporting multiple languages.

## Usage

Translate English to Chinese:
```bash
curl -s "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh&q=hello"
、、、

## 参数说明

- `sl`: 源语言代码 (source language)
  - `en`: 英语
  - `zh`: 中文
  - `ja`: 日语
  - `ko`: 韩语
  - `fr`: 法语
  - `de`: 德语
  - 更多语言代码参考 ISO 639-1 标准
- `tl`: 目标语言代码 (target language)
- `q`: 要翻译的文本（需要 URL 编码）
```

##### Examples

Users can say:

- "Translate hello to Chinese"
- "Translate 'Good morning' to Japanese"
- "How to say this in English: 你好世界"

```

**Step 3: Restart service**

```bash
# Stop current service (Ctrl+C)
# Restart
ownbot gateway
```

After starting, check logs to confirm skill is loaded:

```
INFO  Loaded skill: weather 🌤️
INFO  Loaded skill: translate 🌐
```

Now you can say to the bot:

- "Translate 'Hello World' to Chinese"
- "Translate '早上好' to English"

---

## 📜 License

This project is open-sourced under the [MIT](LICENSE) license.

---

## 🙏 Acknowledgments

Thanks to the following open-source projects:

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot framework
- [@whiskeysockets/baileys](https://github.com/WhiskeySockets/Baileys) - WhatsApp Web API
- [Rich](https://github.com/Textualize/rich) - Terminal beautification

---

## 📮 Contact Me

- 💬 **Issues**: [GitHub Issues](https://github.com/yourusername/ownbot/issues)
- 📧 **Email**: sunchenhao518@163.com
- 📱 **Xiaohongshu (小红书)**: [@真想不到](https://xhslink.com/m/WTYcSpJfdQ) (ID: schhaohao518)

<div align="center">

### Follow me on rednote

<img src="docs/images/xiaohongshu-qr.jpg" width="200" alt="Xiaohongshu QR Code">

**Scan to follow!**

</div>

---

<div align="center">

**⭐ If this project helps you, please give me a Star!**

**🚀 Let's build a more powerful AI assistant together!**

</div>
