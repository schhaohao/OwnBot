# OwnBot - AI Agent Development Guide

This document provides essential information for AI coding agents working on the OwnBot project.

## Project Overview

OwnBot is a **learning-oriented AI Agent framework** designed for students and AI enthusiasts. It implements the ReAct (Reasoning + Acting) architecture with minimal dependencies, aiming to teach Agent principles through clean, well-documented code.

### Key Characteristics

- **Pure Python Implementation**: No heavy Agent frameworks (no LangChain, LangGraph, AutoGPT)
- **Zero Framework Dependencies**: Built from scratch to demonstrate core concepts
- **Multi-Platform Support**: Telegram and WhatsApp channels
- **Modular Skill System**: RAG-based skill retrieval with progressive disclosure
- **Async Architecture**: High-performance asyncio-based design

## Technology Stack

### Core Technologies

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | >= 3.11 |
| CLI Framework | Typer | >= 0.12.3 |
| Data Validation | Pydantic | >= 2.7.0 |
| Logging | Loguru | >= 0.7.2 |
| Terminal UI | Rich | >= 13.0.0 |
| Telegram Bot | python-telegram-bot | >= 22.6 |
| Vector DB | Milvus Lite/Server | >= 2.6.0 |
| Embeddings | sentence-transformers | >= 3.0.0 |
| LLM Access | LiteLLM | Via provider |

### WhatsApp Bridge (Node.js)

- **Library**: @whiskeysockets/baileys ^6.7.16
- **WebSocket**: ws ^8.18.0
- **QR Display**: qrcode-terminal ^0.12.0

## Project Structure

```
ownbot/
├── __init__.py           # Package version
├── __main__.py           # Entry point with logging setup
├── agent/                # Core Agent implementation
│   ├── loop.py          # AgentLoop - ReAct main loop
│   ├── context.py       # ContextBuilder - prompt building
│   ├── memory.py        # (removed) - now using simple sliding window
│   └── tools/           # Tool implementations
│       ├── base.py      # Tool abstract base class
│       ├── filesystem.py # File operations
│       ├── shell.py     # Shell command execution
│       ├── web.py       # HTTP requests
│       └── registry.py  # Tool registry
├── bus/                  # Message bus system
│   ├── events.py        # InboundMessage, OutboundMessage
│   └── queue.py         # MessageBus async queues
├── channels/             # Platform integrations
│   ├── base.py          # BaseChannel ABC
│   ├── telegram.py      # Telegram channel implementation
│   ├── whatsapp.py      # WhatsApp channel (WebSocket bridge)
│   └── manager.py       # Channel lifecycle management
├── cli/                  # Command-line interface
│   └── commands.py      # Typer commands (onboard, gateway, channels, index-skills)
├── config/               # Configuration management
│   ├── schema.py        # Pydantic config models
│   ├── loader.py        # Config load/save utilities
│   └── paths.py         # Path utilities
├── llm.py               # LLM-related utilities
├── providers/            # LLM provider implementations
│   ├── base.py          # LLMProvider ABC, LLMResponse
│   ├── litellm_provider.py  # LiteLLM integration
│   └── registry.py      # Provider registry
├── retrieval/            # RAG skill retrieval
│   └── retriever.py     # SkillRetriever with Milvus
├── session/              # Conversation session management
│   ├── base.py          # Session dataclass
│   └── manager.py       # SessionManager (JSONL storage)
├── skills/               # Built-in skills
│   ├── loader.py        # SkillLoader for SKILL.md files
│   ├── models.py        # Skill, SkillSummary, SkillMetadata
│   ├── clawhub/         # ClawHub skill registry client
│   └── github/          # GitHub CLI integration skill
└── utils/                # Utilities
    └── logger.py        # Loguru configuration, Rich console

whatsapp-bridge/          # Node.js WhatsApp Web bridge
├── package.json
└── server.js            # WebSocket server using Baileys

templates/                # System prompt templates
├── AGENTS.md            # Agent identity template
├── HEARTBEAT.md         # Status reporting template
├── SOUL.md              # Personality definition
├── TOOLS.md             # Tool instructions template
└── USER.md              # User context template
```

## Build and Installation

### Development Setup

```bash
# Clone and setup
pip install -e .

# Install WhatsApp bridge dependencies
cd whatsapp-bridge && npm install && cd ..

# Initialize configuration
ownbot onboard  # Creates ~/.ownbot/config.json
```

### Running the Bot

```bash
# Start the gateway (Telegram + WhatsApp + Agent)
ownbot gateway

# With custom config
ownbot gateway --config /path/to/config.json

# Login to WhatsApp
ownbot channels login --channel whatsapp

# Build skill vector index
ownbot index-skills --force
```

## Configuration

Configuration is stored in `~/.ownbot/config.json`:

```json
{
  "adminIds": ["telegram_user_id"],
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
    "model": "gpt-4.1-mini",
    "temperature": 0.1,
    "maxTokens": 8192,
    "reasoningEffort": null
  },
  "retrieval": {
    "enabled": true,
    "useMilvusLite": true,
    "milvusHost": "localhost",
    "milvusPort": 19530,
    "milvusDbPath": "./milvus_data/ownbot.db",
    "topK": 50,
    "collectionName": "ownbot_skills",
    "embeddingModel": "BAAI/bge-m3"
  }
}
```

Environment variables are supported with `OWNBOT_` prefix and `__` delimiter:
```bash
export OWNBOT_TELEGRAM__TOKEN="your_token"
export OWNBOT_LLM__API_KEY="your_key"
```

## Code Style Guidelines

### Python Standards

- **Type Hints**: Use full type annotations (Python 3.11+ syntax)
- **Async/Await**: All I/O operations must be async
- **Imports**: Use `from __future__ import annotations` for forward references
- **String Formatting**: Use f-strings; use Loguru's `{}` formatting for logging

### Naming Conventions

- **Classes**: PascalCase (e.g., `AgentLoop`, `ContextBuilder`)
- **Functions/Methods**: snake_case (e.g., `build_messages`, `get_or_create`)
- **Constants**: UPPER_SNAKE_CASE for module-level constants
- **Private**: Prefix with underscore for internal use

### Documentation

- Docstrings use Google style:
```python
def execute(self, arguments: dict[str, Any]) -> str:
    """
    Execute the tool with given arguments.

    Args:
        arguments: Tool arguments

    Returns:
        Tool execution result as string
    """
```

### Logging

- Use `loguru.logger` throughout
- Use structured logging: `logger.info("Message: {}", value)`
- Use appropriate levels: debug for verbose, info for normal, warning/error for issues

## Architecture Patterns

### Message Flow

```
User Message → Channel → MessageBus.inbound → AgentLoop → MessageBus.outbound → Channel → User
```

### Agent Loop (ReAct)

1. Receive message from bus
2. Build context (system prompt + history + current message)
3. Call LLM with tool definitions
4. If tool calls: execute tools, add results, loop back to step 3
5. If final answer: return response
6. Save session (user input + final response only)

### Skill System (Progressive Disclosure)

1. **Load**: All skill metadata loaded at startup
2. **Expose**: Only metadata (name, description, path) in system prompt
3. **Retrieve**: Agent decides which skill is relevant
4. **Read**: Agent uses `read_file` tool to load full SKILL.md on demand

### Session Management

- Sessions stored as JSONL files in `~/.ownbot/sessions/{session_key}/session.jsonl`
- Each line is a JSON object (metadata or message)
- Simple sliding window: keeps only recent N messages (default: 50)

## Testing

### Manual Testing

```bash
# Test Milvus connection and skill retrieval
python test_retrieval.py

# Test Milvus standalone setup
python test_milvus.py
```

### No Automated Test Suite

The project currently relies on manual testing. When adding features:
1. Test with both Telegram and WhatsApp channels
2. Verify skill loading and retrieval
3. Check session persistence
4. Test tool execution (file, shell, web)

## Security Considerations

### File System Access

- Tools operate within workspace directory (`~/.ownbot/workspace/`)
- Shell tool is available - be cautious with user input
- Admin check required for `/restart` command

### Configuration Security

- API keys stored in config file - ensure proper file permissions
- WhatsApp auth stored in `~/.ownbot/workspace/whatsapp-auth/`
- No secrets should be committed to git

### Input Validation

- All user input goes through the LLM - expect unexpected inputs
- Tool arguments are validated by Pydantic schemas
- File paths are checked to prevent directory traversal

## Common Development Tasks

### Adding a New Tool

1. Create class in `ownbot/agent/tools/` inheriting from `Tool`
2. Implement `execute()` method
3. Register in `AgentLoop._create_tool_registry()`

### Adding a New Skill

1. Create directory: `ownbot/skills/{skill_name}/`
2. Create `SKILL.md` with YAML frontmatter:
```yaml
---
name: skill_name
description: What this skill does
metadata:
  ownbot:
    emoji: "🚀"
---
```
3. Skill auto-loads on restart

### Adding a New Channel

1. Create class in `ownbot/channels/` inheriting from `BaseChannel`
2. Implement `start()`, `stop()`, `send()` methods
3. Register in `ChannelManager`

## Debugging Tips

### Enable Verbose Logging

Logs are written to `~/.ownbot/logs/ownbot.log` and console.

### Inspect Message Flow

The AgentLoop logs all LLM requests and responses at INFO level.

### Check Session Files

Session data is human-readable JSONL in `~/.ownbot/sessions/`.

### Test RAG Retrieval

```python
from ownbot.retrieval import SkillRetriever

retriever = SkillRetriever(skills_dir=...)
results = retriever.search("your query", top_k=5)
for r in results:
    print(f"{r.name}: {r.score}")
```

## Known Limitations

1. **No Human-in-the-Loop**: Sensitive operations execute without confirmation
2. **Limited Testing**: No automated test suite
3. **Single LLM Provider**: Currently only LiteLLM is implemented
4. **No MCP Support**: Model Context Protocol not yet integrated
5. **WhatsApp Media**: Voice message transcription not fully supported via bridge

## Development Roadmap

See README.md for full roadmap. Key upcoming features:
- Human-in-the-Loop for sensitive operations
- MCP (Model Context Protocol) support
- Vector database RAG for document processing
- Multi-Agent collaboration

## License

MIT License - See LICENSE file
