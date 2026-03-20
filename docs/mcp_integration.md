# MCP (Model Context Protocol) 集成开发文档

## 目录

1. [什么是 MCP？](#什么是-mcp)
2. [架构设计](#架构设计)
3. [代码详解](#代码详解)
4. [配置方法](#配置方法)
5. [使用示例](#使用示例)
6. [扩展开发](#扩展开发)

---

## 什么是 MCP？

MCP（Model Context Protocol，模型上下文协议）是 Anthropic 推出的**开放标准协议**，用于标准化 AI 模型与外部系统（工具、数据源、服务）的交互方式。

### MCP 的核心概念

```
┌─────────────────────────────────────────────────────────────┐
│                        MCP 架构                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────────┐         Protocol          ┌──────────┐  │
│   │   AI Agent   │  ◄──────────────────────► │  Server  │  │
│   │   (Client)   │    Resources/Tools/       │ (MCP     │  │
│   │              │    Prompts                │  Server) │  │
│   └──────────────┘                           └──────────┘  │
│                                                             │
│   传输层：stdio / SSE / HTTP                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**MCP 提供三种核心能力：**

1. **Resources（资源）** - 类似 GET 请求，提供只读数据
2. **Tools（工具）** - 类似 POST 请求，执行操作并有副作用
3. **Prompts（提示）** - 可复用的交互模板

**为什么使用 MCP？**

- **标准化**：统一的工具调用接口，不用为每个工具写适配器
- **生态丰富**：社区有大量现成的 MCP 服务器（文件系统、数据库、GitHub 等）
- **即插即用**：AI Agent 可以动态发现和调用 MCP 工具

---

## 架构设计

### OwnBot MCP 集成架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         OwnBot Agent                                 │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                       AgentLoop                               │  │
│  │                                                              │  │
│  │   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │  │
│  │   │   Built-in   │    │ MCP Registry │    │   Future     │  │  │
│  │   │    Tools     │    │   (Dynamic)  │    │   Tools      │  │  │
│  │   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │  │
│  │          │                   │                   │          │  │
│  │          └───────────────────┼───────────────────┘          │  │
│  │                              │                              │  │
│  │                   ┌──────────┴──────────┐                   │  │
│  │                   │    ToolRegistry     │                   │  │
│  │                   │   (Unified View)    │                   │  │
│  │                   └──────────┬──────────┘                   │  │
│  │                              │                              │  │
│  └──────────────────────────────┼──────────────────────────────┘  │
│                                 │                                   │
│                    ┌────────────┴────────────┐                     │
│                    ▼                         ▼                     │
│           ┌─────────────────┐    ┌─────────────────────┐           │
│           │ MCPClientManager │    │   LLM Provider      │           │
│           │   (Connections)  │    │   (LiteLLM)         │           │
│           └────────┬─────────┘    └─────────────────────┘           │
│                    │                                                │
│     ┌──────────────┼──────────────┐                                 │
│     ▼              ▼              ▼                                 │
│  ┌──────┐    ┌────────┐    ┌──────────┐                            │
│  │stdio │    │  SSE   │    │   HTTP   │   ← Transport Layer         │
│  └──┬───┘    └───┬────┘    └────┬─────┘                            │
│     │            │              │                                   │
│     └────────────┴──────────────┘                                   │
│                    │                                                │
│          ┌─────────┴─────────┐                                     │
│          ▼                   ▼                                     │
│    ┌──────────┐       ┌──────────┐                                │
│    │ MCP Svr 1│       │ MCP Svr 2│   ← External MCP Servers        │
│    └──────────┘       └──────────┘                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 核心组件说明

| 组件 | 职责 | 对应文件 |
|------|------|----------|
| `MCPClientManager` | 管理 MCP 服务器连接、工具调用 | `mcp/client.py` |
| `MCPRegistry` | 管理工具适配器，加载/注册 MCP 工具 | `mcp/tools.py` |
| `MCPToolAdapter` | 将 MCP 工具适配为 OwnBot Tool | `mcp/tools.py` |
| `AgentLoop` | 集成 MCP 初始化到主循环 | `agent/loop.py` |

---

## 代码详解

### 1. 配置层 (config/schema.py)

```python
class MCPServerConfig(BaseConfigModel):
    """单个 MCP 服务器的配置"""

    name: str           # 服务器唯一标识
    enabled: bool       # 是否启用
    transport: str      # 传输方式: stdio/sse/http
    command: str | None # stdio 的命令（如 python, node）
    args: list[str]     # stdio 的命令参数
    url: str | None     # sse/http 的 URL
    env: dict[str, str] # 环境变量
    timeout: float      # 超时时间
```

**设计思考：**
- 支持多种传输方式，stdio 适合本地进程，SSE/HTTP 适合远程服务
- 环境变量支持让 MCP 服务器可以访问密钥等敏感信息
- 每个服务器独立配置，可以单独启用/禁用

### 2. MCP 客户端管理器 (mcp/client.py)

```python
class MCPClientManager:
    """
    核心职责：
    1. 维护与多个 MCP 服务器的连接
    2. 管理连接生命周期（连接、断开、重连）
    3. 转发工具调用请求到正确的服务器
    """
```

**连接流程：**

```python
async def connect_server(self, config: MCPServerConfig) -> MCPConnection:
    # 1. 根据传输方式选择连接方法
    if config.transport == "stdio":
        session = await self._connect_stdio(config)
    elif config.transport == "sse":
        session = await self._connect_sse(config)

    # 2. 获取服务器提供的工具列表
    tools_result = await session.list_tools()

    # 3. 保存连接信息
    conn = MCPConnection(
        server_name=config.name,
        session=session,
        tools=tools_result.tools,
        exit_stack=self._exit_stack,
    )
    self._connections[config.name] = conn
```

**stdio 连接示例：**

```python
async def _connect_stdio(self, config: MCPServerConfig) -> ClientSession:
    # 准备参数
    server_params = StdioServerParameters(
        command=config.command,      # 如 "python"
        args=config.args,            # 如 ["server.py"]
        env={**os.environ, **config.env},  # 合并环境变量
    )

    # 建立连接（使用上下文管理器确保资源释放）
    stdio_transport = await self._exit_stack.enter_async_context(
        stdio_client(server_params)
    )
    read_stream, write_stream = stdio_transport

    # 创建会话
    session = await self._exit_stack.enter_async_context(
        ClientSession(read_stream, write_stream)
    )

    # 初始化协议握手
    await session.initialize()
    return session
```

**为什么使用 `AsyncExitStack`？**

```python
# 问题：多个上下文管理器嵌套会很难看
async with a():
    async with b():
        async with c():
            pass

# 解决方案：AsyncExitStack 统一管理
self._exit_stack = AsyncExitStack()
await self._exit_stack.enter_async_context(a())
await self._exit_stack.enter_async_context(b())
await self._exit_stack.enter_async_context(c())

# 一键清理
await self._exit_stack.aclose()
```

### 3. 工具适配器 (mcp/tools.py)

```python
class MCPToolAdapter(Tool):
    """
    适配器模式的关键：将 MCP Tool 包装成 OwnBot Tool

    为什么需要适配器？
    - MCP Tool 有自己的定义格式（mcp.types.Tool）
    - OwnBot 使用自己的 Tool 基类
    - 适配器让两者可以无缝协作
    """
```

**命名空间处理：**

```python
def __init__(self, server_name: str, mcp_tool: MCPTool, ...):
    # 添加前缀避免命名冲突
    # 例如："filesystem" 服务器的 "read_file" 工具
    # 在 OwnBot 中注册为 "mcp_filesystem_read_file"
    self.name = f"mcp_{server_name}_{mcp_tool.name}"
```

**参数转换：**

```python
def _get_parameters_schema(self) -> dict[str, Any]:
    """
    MCP 工具的参数是 JSON Schema 格式
    直接透传给 OpenAI function calling
    """
    if self._mcp_tool.inputSchema:
        schema = self._mcp_tool.inputSchema
        if schema.get("type") == "object" and "properties" in schema:
            return schema["properties"]
    return {}
```

**工具执行：**

```python
async def execute(self, arguments: ToolParameters) -> ToolResult:
    # 1. 通过 client_manager 调用远程工具
    result = await self.client_manager.call_tool(
        server_name=self.server_name,
        tool_name=self.mcp_tool_name,
        arguments=arguments,
    )

    # 2. 格式化结果
    return self.client_manager.format_tool_result(result)
```

### 4. AgentLoop 集成 (agent/loop.py)

```python
class AgentLoop:
    def __init__(self, cfg: AppConfig, bus: MessageBus):
        # ... 其他初始化 ...

        # MCP 初始化
        self.mcp_manager: MCPClientManager | None = None
        self.mcp_registry: MCPRegistry | None = None
        if self.cfg.mcp.enabled:
            self.mcp_manager = MCPClientManager()
```

**初始化流程：**

```python
async def initialize_mcp(self) -> None:
    """
    在 Agent 启动时初始化 MCP 连接
    """
    # 1. 连接到所有配置的服务器
    await self.mcp_manager.connect_all(self.cfg.mcp.servers)

    # 2. 创建工具注册表
    self.mcp_registry = MCPRegistry(self.mcp_manager)
    await self.mcp_registry.load_tools()

    # 3. 注册到主工具注册表
    for tool in self.mcp_registry.get_tools():
        self.tools.register(tool)
```

**主循环集成：**

```python
async def run(self) -> None:
    self._running = True

    # 初始化 MCP
    await self.initialize_mcp()

    # 进入主循环
    while self._running:
        # ... 处理消息 ...
        pass
```

---

## 配置方法

### 配置文件示例

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
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/myuser/workspace"],
        "env": {},
        "timeout": 30
      },
      {
        "name": "sqlite",
        "enabled": true,
        "transport": "stdio",
        "command": "uvx",
        "args": ["mcp-server-sqlite", "--db-path", "/Users/myuser/data.db"],
        "env": {},
        "timeout": 60
      },
      {
        "name": "github",
        "enabled": true,
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {
          "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxxxxx"
        },
        "timeout": 30
      }
    ]
  }
}
```

### 环境变量配置

```bash
# 使用环境变量配置 MCP
export OWNBOT_MCP__ENABLED=true
export OWNBOT_MCP__SERVERS='[{"name": "filesystem", "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem"]}]'
```

---

## 使用示例

### 示例 1：文件系统操作

假设已配置 filesystem MCP 服务器：

**用户：** "帮我读取项目根目录下的 README.md 文件"

**Agent 思考过程：**

```
1. Agent 收到消息，发现需要使用文件系统工具
2. 在可用工具中发现 mcp_filesystem_read_file
3. 调用工具：
   {
     "name": "mcp_filesystem_read_file",
     "arguments": {
       "path": "/Users/myuser/workspace/README.md"
     }
   }
4. MCP 客户端转发到 filesystem 服务器
5. 服务器读取文件并返回内容
6. Agent 收到内容后回复用户
```

### 示例 2：数据库查询

假设已配置 sqlite MCP 服务器：

**用户：** "查询数据库中有多少用户"

**Agent 思考过程：**

```
1. Agent 分析需要使用数据库工具
2. 发现 mcp_sqlite_query 工具
3. 调用工具：
   {
     "name": "mcp_sqlite_query",
     "arguments": {
       "sql": "SELECT COUNT(*) as count FROM users"
     }
   }
4. 返回查询结果
```

### 示例 3：GitHub 集成

假设已配置 github MCP 服务器：

**用户：** "帮我查看 OpenAI 的 gpt-4 仓库最近的提交"

**Agent 思考过程：**

```
1. Agent 识别到需要 GitHub 操作
2. 发现 mcp_github_list_commits 工具
3. 调用工具：
   {
     "name": "mcp_github_list_commits",
     "arguments": {
       "owner": "openai",
       "repo": "gpt-4",
       "limit": 5
     }
   }
4. 获取提交历史并展示给用户
```

---

## 扩展开发

### 添加新的传输方式

在 `mcp/client.py` 中添加：

```python
async def _connect_websocket(self, config: MCPServerConfig) -> ClientSession:
    """WebSocket 传输示例"""
    import websockets

    ws = await websockets.connect(config.url)
    # 包装为 MCP 流
    read_stream = WebSocketReadStream(ws)
    write_stream = WebSocketWriteStream(ws)

    session = await self._exit_stack.enter_async_context(
        ClientSession(read_stream, write_stream)
    )
    await session.initialize()
    return session
```

### 添加工具调用中间件

```python
class MCPClientManager:
    async def call_tool(self, server_name: str, tool_name: str, arguments: dict):
        # 前置处理：记录调用
        logger.info("Calling MCP tool: {}.{}", server_name, tool_name)

        # 执行调用
        result = await self._do_call(server_name, tool_name, arguments)

        # 后置处理：缓存结果、更新统计等
        await self._post_process(result)

        return result
```

### 添加健康检查

```python
async def health_check(self, server_name: str) -> bool:
    """检查 MCP 服务器是否健康"""
    conn = self._connections.get(server_name)
    if not conn:
        return False

    try:
        # 尝试列出工具来验证连接
        await asyncio.wait_for(
            conn.session.list_tools(),
            timeout=5.0
        )
        return True
    except Exception:
        return False
```

---

## 故障排除

### 常见问题

**1. MCP 服务器启动失败**

```
错误：Failed to connect to 'filesystem': File not found

解决：
- 检查 command 和 args 是否正确
- 确保 npx/uvx 等工具已安装
- 检查文件路径是否正确
```

**2. 工具调用超时**

```
错误：Tool execution timed out

解决：
- 增加配置中的 timeout 值
- 检查 MCP 服务器是否卡住
- 查看服务器日志
```

**3. 工具名称冲突**

```
警告：Failed to register MCP tool xxx: Tool 'xxx' is already registered

解决：
- MCP 工具会自动添加前缀，检查是否有重复的服务器名
- 确保内置工具和 MCP 工具没有重名
```

### 调试技巧

```python
# 启用详细日志
import logging
logging.getLogger("ownbot.mcp").setLevel(logging.DEBUG)

# 手动测试 MCP 连接
async def test_mcp():
    from ownbot.mcp import MCPClientManager
    from ownbot.config.schema import MCPServerConfig

    manager = MCPClientManager()
    config = MCPServerConfig(
        name="test",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "."]
    )

    await manager.connect_server(config)
    tools = manager.get_all_tools()
    print(f"Available tools: {[t[1].name for t in tools]}")

    await manager.disconnect_all()
```

---

## 总结

通过 MCP 集成，OwnBot 获得了以下能力：

1. **动态工具发现** - 自动发现和注册 MCP 服务器的工具
2. **标准化接口** - 使用统一的方式调用任何 MCP 工具
3. **生态兼容** - 可以直接使用社区数千个 MCP 服务器
4. **灵活配置** - 支持多种传输方式和配置选项

这个实现展示了如何：
- 使用适配器模式集成外部协议
- 使用 AsyncExitStack 管理异步资源
- 在不破坏现有架构的情况下扩展功能
