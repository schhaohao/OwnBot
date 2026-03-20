# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

#### MCP (Model Context Protocol) Support
- Full MCP integration with client manager and tool adapters
- Support for stdio, SSE, and HTTP transports
- Automatic tool discovery and registration from MCP servers
- MCP configuration in `mcp` section of config.json
- Compatible with official MCP servers (filesystem, sqlite, github, etc.)

#### Real-time Progress Notifications
- Agent Loop now sends progress updates during processing
- Shows thinking status, tool calls, and execution results
- Formatted MCP tool names (server:tool format)
- Step-by-step iteration tracking

#### Development Tools
- Comprehensive test suite with pytest
- Pre-commit hooks configuration (ruff, mypy, bandit)
- GitHub Actions CI/CD workflow
- Makefile for common development tasks
- Code coverage reporting (pytest-cov)
- Type checking with mypy

#### Code Quality
- Centralized constants module (`ownbot/constants.py`)
- Comprehensive exception hierarchy (`ownbot/exceptions.py`)
- Type aliases module (`ownbot/types.py`)
- Enhanced type annotations across all modules

#### Documentation
- Development guide (`docs/DEVELOPMENT.md`)
- This changelog
- Improved docstrings following Google style

#### Security
- Shell command validation and blacklisting
- Path traversal prevention in filesystem tools
- URL validation in web request tool

### Changed

#### Memory System Simplification
- **BREAKING**: Removed complex memory consolidation system
- Replaced with simple sliding window mechanism
- Removed `memory.py` module (210 lines)
- Memory now keeps only recent N messages (default: 50)
- `/new` command properly clears session history

#### Refactored Modules
- `ownbot/agent/tools/`: Extracted base class, improved error handling
- `ownbot/config/`: Cleaner separation of concerns, added MCP config
- `ownbot/bus/`: Enhanced message bus with better async support
- `ownbot/providers/`: Improved provider abstraction
- `ownbot/agent/loop.py`: Added progress callback mechanism

#### Code Style
- Migrated to Python 3.11+ type syntax (`X | None` instead of `Optional[X]`)
- Unified constant definitions
- Removed magic numbers and strings
- Improved naming consistency

### Removed

- **Memory Consolidation System**:
  - `ownbot/agent/memory.py` (MemoryConsolidator, MemoryStore, MemoryEntry)
  - LLM-based summary generation
  - MEMORY.md and HISTORY.md file generation
  - Token-based consolidation triggers
  - `AGENT_MEMORY_CONSOLIDATION_THRESHOLD` constant
  - `MEMORY_FILE_NAME` constant

- Duplicate module files at package root:
  - `ownbot/agent.py`
  - `ownbot/bus.py`
  - `ownbot/config.py`
  - `ownbot/llm.py`

### Fixed

- Exception handling now properly chains exceptions with `raise ... from e`
- Async task cleanup in agent loop
- Path resolution security in filesystem tools

## [0.0.1] - 2024-03-13

### Added

- Initial project structure
- ReAct (Reasoning + Acting) agent architecture
- Telegram channel support
- WhatsApp channel support (via Node.js bridge)
- Tool system (filesystem, shell, web)
- Skill system with YAML frontmatter
- Session management with JSONL storage
- Memory consolidation
- RAG-based skill retrieval with Milvus
- Configuration management with Pydantic
- Rich console logging

[Unreleased]: https://github.com/schhaohao/OwnBot/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/schhaohao/OwnBot/releases/tag/v0.0.1
