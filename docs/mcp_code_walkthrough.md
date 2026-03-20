# MCP 集成代码详解 - 学习指南

## 项目概述

本次开发为 OwnBot 添加了 MCP (Model Context Protocol) 支持，使 AI Agent 可以无缝使用外部 MCP 服务器提供的工具。

## 文件结构

```
ownbot/
├── mcp/                        # MCP 集成模块 (新增)
│   ├── __init__.py            # 模块导出
│   ├── client.py              # MCP 客户端管理器
│   └── tools.py               # 工具适配器
├── config/
│   └── schema.py              # MCP 配置模型 (修改)
├── agent/
│   └── loop.py                # AgentLoop MCP 集成 (修改)
├── exceptions.py              # MCP 异常 (修改)
└── agent/tools/
    └── __init__.py            # 导出 MCP 工具 (修改)

docs/
├── mcp_integration.md         # 详细开发文档
├── mcp_quickstart.md          # 快速开始指南
├── mcp_config_example.json    # 配置示例
└── mcp_code_walkthrough.md    # 本文件

test_mcp_integration.py        # 集成测试
```

## 代码讲解

### 1. 配置模型 (config/schema.py)

**为什么需要配置模型？**

Pydantic 配置模型提供：
- 类型安全：在开发时就能发现配置错误
- 自动验证：确保必填字段存在、数值在合理范围
- JSON 序列化：方便保存/加载配置

```python
class MCPServerConfig(BaseConfigModel):
    """
    单个 MCP 服务器的配置

    设计决策：
    1. transport 支持多种方式：stdio(本地进程)、sse/http(远程服务)
    2. command/args 用于 stdio，url 用于 sse/http
    3. env 允许每个服务器有独立的环境变量
    """
    name: str           # 唯一标识，用于工具命名前缀
    enabled: bool       # 可以单独启用/禁用某个服务器
    transport: str      # stdio | sse | http
    command: str | None # 如 "npx", "python"
    args: list[str]     # 命令参数
    url: str | None     # 远程服务器 URL
    env: dict[str, str] # 环境变量（如 API 密钥）
    timeout: float      # 防止请求卡住
```

**配置继承关系：**

```
AppConfig (根配置)
├── TelegramConfig
├── WhatsAppConfig
├── LLMConfig
├── RetrievalConfig
└── MCPConfig (新增)
    └── list[MCPServerConfig]
```

### 2. 异常定义 (exceptions.py)

**异常层次设计：**

```
OwnBotError (基类)
└── MCPError (MCP 相关错误的基类)
    ├── MCPConnectionError    # 连接失败
    ├── MCPServerNotFoundError # 服务器不存在
    └── MCPToolError          # 工具调用失败
```

**为什么要自定义异常？**

```python
# 不使用自定义异常
try:
    result = await some_operation()
except Exception as e:
    # 不知道是什么错误，可能是网络、配置、服务器问题
    pass

# 使用自定义异常
try:
    result = await mcp_manager.call_tool(...)
except MCPConnectionError:
    # 明确知道是连接问题，可以提示用户检查服务器
    logger.error("无法连接到 MCP 服务器，请检查配置")
except MCPToolError:
    # 工具执行失败，可以提示用户检查参数
    logger.error("工具执行失败，请检查参数")
```

### 3. MCP 客户端管理器 (mcp/client.py)

这是 MCP 集成的核心，负责与 MCP 服务器通信。

#### 核心类：MCPClientManager

```python
class MCPClientManager:
    """
    职责：
    1. 建立和维护与多个 MCP 服务器的连接
    2. 转发工具调用请求到正确的服务器
    3. 管理连接生命周期（创建、重用、清理）
    """

    def __init__(self):
        self._connections: dict[str, MCPConnection] = {}
        self._exit_stack = AsyncExitStack()
```

#### 关键技术：AsyncExitStack

**问题：** 多个异步上下文管理器嵌套很难看

```python
# 糟糕的写法 - 深层嵌套
async with context1() as c1:
    async with context2() as c2:
        async with context3() as c3:
            # 实际代码
            pass
```

**解决方案：** AsyncExitStack

```python
# 优雅的写法
self._exit_stack = AsyncExitStack()
await self._exit_stack.enter_async_context(context1())
await self._exit_stack.enter_async_context(context2())
await self._exit_stack.enter_async_context(context3())

# 一键清理所有资源
await self._exit_stack.aclose()
```

#### 连接流程详解

```python
async def connect_server(self, config: MCPServerConfig) -> MCPConnection:
    # 1. 根据传输方式选择连接方法
    if config.transport == "stdio":
        session = await self._connect_stdio(config)
    elif config.transport == "sse":
        session = await self._connect_sse(config)

    # 2. 获取该服务器提供的所有工具
    tools_result = await session.list_tools()

    # 3. 保存连接信息供后续使用
    conn = MCPConnection(
        server_name=config.name,
        session=session,
        tools=tools_result.tools,
        ...
    )
    self._connections[config.name] = conn
```

#### stdio 传输详解

```python
async def _connect_stdio(self, config: MCPServerConfig) -> ClientSession:
    """
    stdio 传输通过启动子进程通信

    例如：npx -y @modelcontextprotocol/server-filesystem /path

    流程：
    1. 启动子进程
    2. 建立双向通信管道（stdin/stdout）
    3. 使用 MCP 协议进行握手
    """

    # 准备参数
    server_params = StdioServerParameters(
        command=config.command,      # "npx"
        args=config.args,            # ["-y", "server-package"]
        env={**os.environ, **config.env},  # 合并环境变量
    )

    # 启动子进程，建立通信
    stdio_transport = await self._exit_stack.enter_async_context(
        stdio_client(server_params)
    )
    read_stream, write_stream = stdio_transport

    # 创建 MCP 会话
    session = await self._exit_stack.enter_async_context(
        ClientSession(read_stream, write_stream)
    )

    # 协议握手
    await session.initialize()
    return session
```

### 4. 工具适配器 (mcp/tools.py)

**为什么需要适配器？**

```
┌──────────────┐         ┌──────────────┐
│   MCP Tool   │  ──X──► │  OwnBot Tool │  不兼容！
│  (mcp.types) │         │  (ownbot)    │
└──────────────┘         └──────────────┘
       │                        │
       │   ┌──────────────┐    │
       └──►│   Adapter    ├───►│
           │(MCPToolAdapter)│   │
           └──────────────┘    │
                    适配后兼容   │
```

#### MCPToolAdapter 详解

```python
class MCPToolAdapter(Tool):
    """
    适配器将 MCP 工具包装成 OwnBot Tool
    """

    def __init__(self, server_name, mcp_tool, client_manager):
        # 关键：命名空间隔离
        # 格式：mcp_{server_name}_{tool_name}
        # 例如：mcp_filesystem_read_file
        self.name = f"mcp_{server_name}_{mcp_tool.name}"

        # 保存原始信息
        self.server_name = server_name
        self.mcp_tool_name = mcp_tool.name
        self.client_manager = client_manager

        # 保存 MCP 工具定义（包含参数schema）
        self._mcp_tool = mcp_tool
```

#### 参数 Schema 转换

```python
def _get_parameters_schema(self) -> dict[str, Any]:
    """
    MCP 工具已经提供了 JSON Schema 格式的参数定义
    我们直接透传，不需要额外转换
    """
    if self._mcp_tool.inputSchema:
        schema = self._mcp_tool.inputSchema
        # MCP Schema 示例：
        # {
        #   "type": "object",
        #   "properties": {
        #     "path": {"type": "string", "description": "文件路径"}
        #   },
        #   "required": ["path"]
        # }
        if schema.get("type") == "object" and "properties" in schema:
            return schema["properties"]
    return {}
```

#### 工具执行流程

```python
async def execute(self, arguments: ToolParameters) -> ToolResult:
    """
    执行 MCP 工具的完整流程
    """
    # 1. 通过 client_manager 调用远程工具
    result = await self.client_manager.call_tool(
        server_name=self.server_name,
        tool_name=self.mcp_tool_name,
        arguments=arguments,
    )

    # 2. MCP 返回结构化结果，转换为字符串
    return self.client_manager.format_tool_result(result)

# format_tool_result 示例：
def format_tool_result(self, result: CallToolResult) -> str:
    parts = []
    for content in result.content:
        if isinstance(content, TextContent):
            parts.append(content.text)  # 提取文本
        else:
            parts.append(f"[{content.type} content]")  # 其他类型
    return "\n".join(parts)
```

#### MCPRegistry 详解

```python
class MCPRegistry:
    """
    管理所有 MCP 工具适配器

    职责：
    1. 为每个 MCP 工具创建适配器
    2. 提供工具查询接口
    """

    async def load_tools(self) -> list[MCPToolAdapter]:
        # 从 client_manager 获取所有工具
        all_tools = self.client_manager.get_all_tools()
        # all_tools = [("server1", tool1), ("server2", tool2), ...]

        # 为每个工具创建适配器
        for server_name, mcp_tool in all_tools:
            adapter = MCPToolAdapter(
                server_name=server_name,
                mcp_tool=mcp_tool,
                client_manager=self.client_manager,
            )
            self._adapters.append(adapter)
```

### 5. AgentLoop 集成 (agent/loop.py)

**延迟导入解决循环依赖：**

```python
# 问题：直接导入会导致循环导入
from ownbot.mcp.tools import MCPRegistry  # ❌

# 解决：在方法内部导入
async def initialize_mcp(self):
    from ownbot.mcp.tools import MCPRegistry  # ✅
```

**初始化流程：**

```python
class AgentLoop:
    def __init__(self, cfg: AppConfig, bus: MessageBus):
        # ... 其他初始化 ...

        # MCP 初始化（仅当启用时）
        self.mcp_manager: Any | None = None
        self.mcp_registry: Any | None = None
        if self.cfg.mcp.enabled:
            from ownbot.mcp import MCPClientManager
            self.mcp_manager = MCPClientManager()

    async def run(self) -> None:
        """主循环"""
        self._running = True

        # 启动时初始化 MCP
        await self.initialize_mcp()

        # 进入消息处理循环
        while self._running:
            # ...

    async def initialize_mcp(self) -> None:
        """连接 MCP 服务器并注册工具"""
        if not self.cfg.mcp.enabled:
            return

        # 1. 连接所有配置的服务器
        await self.mcp_manager.connect_all(self.cfg.mcp.servers)

        # 2. 加载工具
        self.mcp_registry = MCPRegistry(self.mcp_manager)
        await self.mcp_registry.load_tools()

        # 3. 注册到主工具注册表
        for tool in self.mcp_registry.get_tools():
            self.tools.register(tool)  # 现在 Agent 可以使用这些工具了
```

### 6. 工具注册流程

**完整的数据流：**

```
1. 用户消息
   ↓
2. AgentLoop.run() 调用 initialize_mcp()
   ↓
3. MCPClientManager.connect_all()
   ├── 连接 server1 (stdio)
   ├── 连接 server2 (sse)
   └── 获取每个服务器的工具列表
   ↓
4. MCPRegistry.load_tools()
   ├── 为 tool1 创建 MCPToolAdapter
   ├── 为 tool2 创建 MCPToolAdapter
   └── ...
   ↓
5. AgentLoop.tools.register(adapter)
   └── ToolRegistry 统一管理所有工具
   ↓
6. LLM 调用时，tools.get_definitions() 包含 MCP 工具
   ↓
7. LLM 返回 tool_calls
   ↓
8. AgentLoop 执行工具
   ├── 内置工具：直接执行
   └── MCP 工具：MCPToolAdapter.execute()
       └── MCPClientManager.call_tool()
           └── 转发到对应的 MCP 服务器
```

## 关键设计决策

### 1. 为什么使用适配器模式？

- **单一职责**：每个类只做一件事
- **开闭原则**：不修改 MCP SDK 或 OwnBot 核心代码
- **可测试性**：可以 mock 适配器进行测试

### 2. 为什么延迟导入？

```
ownbot/agent/loop.py ──► ownbot/mcp/tools.py
       ▲                       │
       │                       ▼
       └───────────────── ownbot/agent/tools/base.py
              (循环导入！)
```

延迟导入打破循环：只在需要时导入

### 3. 为什么工具名要加前缀？

```python
# 没有前缀 - 命名冲突！
server1: read_file  →  read_file
server2: read_file  →  read_file (冲突！)

# 有前缀 - 命名空间隔离
server1: read_file  →  mcp_server1_read_file
server2: read_file  →  mcp_server2_read_file
```

## 测试策略

```python
# 单元测试：使用 Mock 模拟 MCP 服务器
async def test_mcp_tool_adapter():
    mock_mcp_tool = MagicMock()
    mock_mcp_tool.name = "read_file"
    mock_mcp_tool.inputSchema = {...}

    adapter = MCPToolAdapter(
        server_name="filesystem",
        mcp_tool=mock_mcp_tool,
        client_manager=mock_manager
    )

    assert adapter.name == "mcp_filesystem_read_file"
```

## 扩展思路

### 1. 添加新的传输方式

```python
async def _connect_websocket(self, config):
    ws = await websockets.connect(config.url)
    return WebSocketSession(ws)
```

### 2. 添加连接池

```python
class MCPClientManager:
    def __init__(self):
        self._connection_pool = {}

    async def get_connection(self, server_name):
        if server_name not in self._connection_pool:
            self._connection_pool[server_name] = await self.connect(server_name)
        return self._connection_pool[server_name]
```

### 3. 添加健康检查

```python
async def health_check(self, server_name: str) -> bool:
    try:
        conn = self._connections[server_name]
        await asyncio.wait_for(conn.session.list_tools(), timeout=5)
        return True
    except Exception:
        return False
```

## 总结

通过这次开发，我们学习到：

1. **适配器模式**：如何集成两个不兼容的接口
2. **异步资源管理**：AsyncExitStack 的使用
3. **延迟导入**：解决 Python 循环导入问题
4. **配置驱动设计**：通过配置灵活控制功能
5. **错误处理**：自定义异常提供清晰的错误信息

MCP 集成使 OwnBot 具备了无限的扩展可能，任何支持 MCP 的工具都可以无缝接入！
