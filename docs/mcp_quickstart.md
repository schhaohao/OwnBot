# MCP 集成快速开始指南

## 什么是 MCP？

MCP (Model Context Protocol) 是一个开放协议，允许 AI Agent 连接和使用外部工具。通过 MCP，OwnBot 可以：

- 访问文件系统
- 查询数据库
- 调用 GitHub API
- 使用任何支持 MCP 的工具

## 快速开始

### 1. 安装 MCP 依赖

```bash
cd /path/to/OwnBot
pip install "mcp>=1.12.0,<2.0.0"
```

或者重新安装整个项目：

```bash
pip install -e .
```

### 2. 配置文件

编辑 `~/.ownbot/config.json`，添加 MCP 配置：

```json
{
  "mcp": {
    "enabled": true,
    "servers": [
      {
        "name": "filesystem",
        "enabled": true,
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"],
        "env": {},
        "timeout": 30
      }
    ]
  }
}
```

### 3. 启动 OwnBot

```bash
ownbot gateway
```

启动时你会看到 MCP 初始化日志：

```
INFO - Initializing MCP connections...
INFO - Connected to MCP server: filesystem with 5 tools
INFO - MCP initialization complete. Registered 5 tools from 1 servers
```

### 4. 使用 MCP 工具

现在你可以像使用普通工具一样使用 MCP 工具。例如：

**用户：** "帮我读取 /path/to/allowed/dir/README.md 文件"

Agent 会自动调用 `mcp_filesystem_read_file` 工具来读取文件。

## 可用的 MCP 服务器

### 文件系统
```json
{
  "name": "filesystem",
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
}
```

### SQLite 数据库
```json
{
  "name": "sqlite",
  "transport": "stdio",
  "command": "uvx",
  "args": ["mcp-server-sqlite", "--db-path", "/path/to/database.db"]
}
```

### GitHub
```json
{
  "name": "github",
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-github"],
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "your_token_here"
  }
}
```

### PostgreSQL
```json
{
  "name": "postgres",
  "transport": "stdio",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"]
}
```

### Fetch (HTTP 请求)
```json
{
  "name": "fetch",
  "transport": "stdio",
  "command": "uvx",
  "args": ["mcp-server-fetch"]
}
```

## 配置说明

| 字段 | 说明 | 示例 |
|------|------|------|
| `name` | 服务器唯一标识 | `filesystem` |
| `enabled` | 是否启用 | `true` |
| `transport` | 传输方式: `stdio`, `sse`, `http` | `stdio` |
| `command` | stdio 的命令 | `npx`, `uvx`, `python` |
| `args` | 命令参数 | `["-y", "server-package"]` |
| `url` | sse/http 的 URL | `http://localhost:3000/sse` |
| `env` | 环境变量 | `{"API_KEY": "xxx"}` |
| `timeout` | 超时时间(秒) | `30` |

## 工具命名规则

MCP 工具在 OwnBot 中会被重命名为：`mcp_{server_name}_{tool_name}`

例如：
- 服务器 `filesystem` 的工具 `read_file` → `mcp_filesystem_read_file`
- 服务器 `github` 的工具 `list_issues` → `mcp_github_list_issues`

## 故障排除

### MCP 服务器启动失败

```
Failed to connect to 'filesystem': command not found
```

**解决：** 确保 `npx` 或 `uvx` 已安装：
```bash
npm install -g npx
# 或
pip install uv
```

### 工具调用超时

增加配置文件中的 `timeout` 值：
```json
{
  "timeout": 60
}
```

### 查看 MCP 日志

在日志中搜索 `MCP` 关键词：
```bash
tail -f ~/.ownbot/logs/ownbot.log | grep -i mcp
```

## 了解更多

- 详细开发文档：[mcp_integration.md](./mcp_integration.md)
- 配置示例：[mcp_config_example.json](./mcp_config_example.json)
- MCP 官方文档：https://modelcontextprotocol.io/
- MCP Python SDK：https://github.com/modelcontextprotocol/python-sdk
