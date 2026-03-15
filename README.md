<div align="center">

# 🤖 OwnBot

**零基础入门 Agent 开发 —— 极简代码、零框架依赖、保姆教学，打造你自己的 OpenClaw**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg?style=flat-square&logo=python)](https://www.python.org/) [![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE) [![Code Style](https://img.shields.io/badge/Code%20Style-Black-black.svg?style=flat-square)](https://github.com/psf/black) [![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg?style=flat-square)](CONTRIBUTING.md)

[English](./README_EN.md) | **中文**

</div>

---

## ✨ 项目简介

> 🎓 **这是一个面向学习者的 Agent 入门项目**

**OwnBot** 是一个专为**学生党**和**Agent 技术爱好者**设计的**学习项目**。我们的目标是：

- 📚 **帮助理解 Agent 原理** - 从零开始实现 Agent Loop + ReAct 架构，不依赖任何 Agent 开发框架
- 💡 **最少最简洁的代码** - 每一行代码都有清晰的注释，易于理解
- 🎯 **最通俗易懂** - 用最直观的方式展示 Agent 的工作流程
- 🔧 **可运行的完整系统** - 不只是概念，而是真正能工作的智能助手

### 🌟 为什么选择 OwnBot？

市面上有很多 Agent 框架（如 LangChain、LangGraph、AutoGPT 等），但它们往往：

- ❌ 封装过度，难以理解底层原理
- ❌ 代码复杂，学习曲线陡峭
- ❌ 依赖众多，环境配置困难

**OwnBot 采用完全不同的思路**：

- ✅ **纯 Python 原生实现** - 不依赖任何 Agent 框架
- ✅ **代码精简清晰** - 核心逻辑只有500 行
- ✅ **从零构建** - 从消息接收到 LLM 调用，每一步都透明可见
- ✅ **即学即用** - 边读代码边理解 Agent 是如何工作的

### 👥 适合谁？

| 人群                          | 收获                              |
| ----------------------------- | --------------------------------- |
| 🎓**AI/CS 学生党**      | 理解 Agent 核心原理，完成课程项目 |
| 🔬**AI 技术爱好者**     | 亲手构建一个可运行的 Agent 系统   |
| 👨‍🏫**教育工作者**    | 作为 Agent 教学的最佳实践案例     |
| 🚀**创业者/独立开发者** | 快速搭建个人 AI 助手原型          |

### 🎯 核心特性

- **🚀 多平台支持** - 同时支持 Telegram 和 WhatsApp，一个机器人，多个入口
- **🧠 智能架构** - 基于 ReAct (Reasoning + Acting) 架构，支持复杂任务处理
- **🛠️ 工具系统** - 内置文件操作、Shell 命令、网络请求等实用工具
- **📦 技能系统** - 模块化技能设计，轻松扩展新功能（如天气查询）
- **💾 记忆管理** - 智能会话管理，支持记忆巩固，保持上下文连贯
- **⚡ 异步高性能** - 基于 Python asyncio，高并发处理能力
- **🔧 易于扩展** - 清晰的模块化设计，方便二次开发

---

## 🚧 项目状态

> 🟢 **Actively maintained** - 项目正在积极开发中

本项目目前处于 **Beta 阶段**，核心功能已经可用，但仍在持续迭代优化中。

> ⚠️ **注意**：作为学习项目，代码中难免存在 Bug 或不完善之处。如果你在使用过程中遇到问题，欢迎通过 GitHub Issues 提出批评指正，这对项目改进非常有帮助！

我们欢迎所有形式的反馈和建议！

### 📋 开发路线图

#### ✅ 已实现

- [X] Agent Loop + ReAct 核心架构
- [X] Telegram 通道支持
- [X] WhatsApp 通道支持
- [X] 基础工具系统（文件、Shell、网络）
- [X] 技能系统框架
- [X] 会话、记忆管理

#### 🚧 进行中

- [ ] 👤 **Human-in-the-Loop** - 关键操作需要人工确认
- [ ] 🔌 **MCP 协议支持** - 接入 Model Context Protocol
- [ ] 更完善的文档和教程
- [ ] 更多内置技能（日历、邮件等）

#### 📅 计划中的功能

| 功能                      | 描述                                | 优先级 |
| ------------------------- | ----------------------------------- | ------ |
| 💾**向量数据库**    | 支持 RAG，让 Agent 可以读取本地文档 | 🔴 高  |
| 📱**更多平台**      | Discord、Slack、飞书等平台支持      | 🔴 高  |
| 🧠**多 Agent 协作** | 支持多个 Agent 分工协作完成任务     | 🟡 中  |
| 🎨**Web 管理界面**  | 提供可视化的配置和监控界面          | 🟡 中  |
| 🔊**语音支持**      | 语音输入和语音回复                  | 🟢 低  |

---

## 📸 项目展示

<div align="center">

### 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户交互层 (User Layer)                    │
│    ┌──────────────┐    ┌──────────────┐                         │
│    │   Telegram   │    │   WhatsApp   │                         │
│    └──────┬───────┘    └──────┬───────┘                         │
└───────────┼───────────────────┼─────────────────────────────────┘
            │                   │
            ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                        消息总线层 (Bus Layer)                     │
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
│                        智能核心层 (Agent Layer)                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      AgentLoop                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │   │
│  │  │   ReAct      │  │   Context    │  │   Session    │    │   │
│  │  │   Engine     │  │   Builder    │  │   Manager    │    │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
            │                   │
            ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                        能力扩展层 (Capability Layer)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │    Tools     │  │   Skills     │  │    LLM       │           │
│  │  (文件/Shell) │  │  (天气/扩展)  │  │  (DeepSeek)  │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

</div>

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+ (用于 WhatsApp 支持)
- macOS / Linux / Windows

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/schhaohao/OwnBot.git
cd OwnBot
```

#### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装 Python 依赖
pip install -e .

# 安装 WhatsApp Bridge 依赖
cd whatsapp-bridge && npm install && cd ..
```

#### 3. 初始化配置

```bash
ownbot onboard
```

这会创建默认配置文件在 `~/.ownbot/config.json`

#### 4. 编辑配置

```bash
# 编辑配置文件
vim ~/.ownbot/config.json
```

**最小配置示例：**

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
    "apiBase": "https://api.siliconflow.cn/v1",
    "apiKey": "YOUR_API_KEY",
    "model": "deepseek-ai/DeepSeek-V3.2",
    "temperature": 0.7,
    "maxTokens": 4096
  }
}
```

#### 5. 登录 WhatsApp（如需要）

```bash
ownbot channels login --channel whatsapp
```

whatsapp扫描终端显示的二维码完成登录。

#### 6. 启动服务

```bash
ownbot gateway
```

---

## 📖 使用指南

### 基础对话

直接发送消息给机器人，它会智能回复：

- **简单对话**：`你好`、`介绍一下自己`
- **天气查询**：`北京今天天气怎么样？`
- **文件操作**：`帮我创建一个 todo.txt 文件`
- **网络搜索**：`搜索一下最新的 AI 新闻`

### 工具使用

机器人内置多种工具，可以通过自然语言调用：

| 工具            | 示例                            | 说明            |
| --------------- | ------------------------------- | --------------- |
| `list_files`  | `查看当前目录文件`            | 列出目录内容    |
| `read_file`   | `读取 README.md`              | 读取文件内容    |
| `write_file`  | `创建 test.txt 写入 hello`    | 创建/写入文件   |
| `shell`       | `执行 ls -la`                 | 执行 Shell 命令 |
| `web_request` | `访问 https://api.github.com` | HTTP 请求       |

### 技能系统

技能是预定义的功能模块，放在 `ownbot/skills/` 目录：

```
ownbot/skills/
├── weather/           # 天气查询技能
│   ├── SKILL.md      # 技能定义
├── translate/        # 翻译技能
|   ├── SKILL.md      # 技能定义 
└── your_skill/       # 你的自定义技能
    └── SKILL.md
```

**SKILL.md 格式：**

```markdown
---
name: weather
description: 查询天气信息
emoji: 🌤️
---

# Weather Skill

查询指定城市的天气信息...
```

---

## 🏗️ 系统架构

### 核心模块

| 模块                  | 职责     | 关键类                                                  |
| --------------------- | -------- | ------------------------------------------------------- |
| **Channels**    | 平台接入 | `TelegramChannel`, `WhatsAppChannel`                |
| **Message Bus** | 消息路由 | `MessageBus`, `InboundMessage`, `OutboundMessage` |
| **Agent**       | 智能核心 | `AgentLoop`, `ContextBuilder`, `SessionManager`   |
| **Tools**       | 工具执行 | `ToolRegistry`, `FileSystemTool`, `ShellTool`     |
| **Skills**      | 技能管理 | `SkillLoader`, `Skill`                              |
| **LLM**         | 模型接入 | `LiteLLMProvider`                                     |

### 消息处理流程

```
1. 接收 (Receive)
   └─ 用户发送消息 → Channel 接收

2. 入队 (Enqueue)
   └─ 消息进入 MessageBus 入站队列

3. 处理 (Process)
   └─ AgentLoop 取出消息
      ├─ SessionManager 加载/创建会话
      ├─ ContextBuilder 构建上下文（含 ReAct 提示）
      ├─ LLM 调用（ReAct 循环）
      │   ├─ Thought: 分析思考
      │   ├─ Action: 调用工具
      │   ├─ Observation: 观察结果
      │   └─ Final Answer: 生成回复
      └─ 保存会话状态

4. 出队 (Dequeue)
   └─ 回复进入 MessageBus 出站队列

5. 发送 (Send)
   └─ Channel 发送给用户
```

---

## ⚙️ 配置详解

### 完整配置示例

```json
{
  "adminIds": ["admin_telegram_user_id"], //针对telegram
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

### 配置项说明

#### Telegram 配置

| 配置项             | 类型    | 默认值    | 说明                                   |
| ------------------ | ------- | --------- | -------------------------------------- |
| `adminIds`       | array   | []        | 管理员用户 ID 列表，拥有特殊权限       |
| `enabled`        | boolean | false     | 是否启用                               |
| `token`          | string  | ""        | Bot Token（从 @BotFather 获取）        |
| `allowFrom`      | array   | []        | 允许的用户 ID，`*` 表示所有人        |
| `proxy`          | string  | null      | 代理地址，如 `http://127.0.0.1:7890` |
| `replyToMessage` | boolean | false     | 是否引用原消息回复                     |
| `groupPolicy`    | string  | "mention" | 群组策略：`mention` 或 `open`      |

#### WhatsApp 配置

| 配置项        | 类型    | 默认值                | 说明                  |
| ------------- | ------- | --------------------- | --------------------- |
| `enabled`   | boolean | false                 | 是否启用              |
| `allowFrom` | array   | []                    | 允许的手机号或群组 ID |
| `bridgeUrl` | string  | "ws://localhost:3001" | Bridge 服务地址       |

#### LLM 配置

| 配置项          | 类型   | 默认值                      | 说明            |
| --------------- | ------ | --------------------------- | --------------- |
| `apiBase`     | string | "https://api.openai.com/v1" | API 基础地址    |
| `apiKey`      | string | ""                          | API 密钥        |
| `model`       | string | "gpt-4"                     | 模型名称        |
| `temperature` | float  | 0.7                         | 温度参数（0-2） |
| `maxTokens`   | int    | 8192                        | 最大 Token 数   |

---

## 🛠️ 开发指南

### 项目结构

```
ownbot/
├── __init__.py
├── __main__.py           # 入口点
├── agent/                # 智能核心
│   ├── __init__.py
│   ├── context.py        # 上下文构建
│   ├── loop.py          # Agent Loop + ReAct 主循环
│   └── session.py       # 会话管理
├── bus/                  # 消息总线
│   ├── __init__.py
│   ├── events.py        # 消息事件
│   └── queue.py         # 消息队列
├── channels/             # 平台通道
│   ├── __init__.py
│   ├── base.py          # 基础通道类
│   ├── telegram.py      # Telegram 实现
│   ├── whatsapp.py      # WhatsApp 实现
│   └── manager.py       # 通道管理
├── cli/                  # 命令行
│   └── commands.py
├── config/               # 配置管理
│   ├── __init__.py
│   └── schema.py
├── skills/               # 技能系统
│   ├── loader.py
│   ├── models.py
│   └── weather/         # 示例技能
├── tools/                # 工具系统
│   ├── registry.py
│   └── tools.py
└── utils/                # 工具函数
    └── logger.py
```

### 添加自定义工具

```python
# ownbot/tools/tools.py

async def my_custom_tool(param1: str, param2: int = 10) -> str:
    """
    我的自定义工具
  
    Args:
        param1: 第一个参数
        param2: 第二个参数，默认10
  
    Returns:
        处理结果
    """
    # 实现逻辑
    return f"处理结果: {param1}, {param2}"

# 注册工具
from ownbot.tools.registry import register_tool
register_tool("my_tool", my_custom_tool)
```

### 添加自定义技能

1. 创建技能目录：`ownbot/skills/my_skill/`
2. 创建 `SKILL.md`：

```markdown
---
name: my_skill
description: 我的自定义技能
emoji: 🚀
---

# My Skill

这里是技能的详细说明...
```

#### 示例：创建一个"翻译"技能

**步骤 1：创建技能目录**

```bash
mkdir -p ownbot/skills/translate
```

**步骤 2：创建 SKILL.md 文件**

创建文件 `ownbot/skills/translate/SKILL.md`：

```markdown

---
name: translate
description: 翻译文本（使用 Google Translate）
homepage: https://translate.google.com
metadata:
  ownbot:
    emoji: "🌐"
    requires:
      bins: ["curl"]
---

# Translate Skill

使用 Google Translate 翻译文本。

## 使用示例

翻译英文到中文：
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

##### **使用示例**

用户可以说：

- "把 hello 翻译成中文"
- "翻译 'Good morning' 成日语"
- "这句话用英语怎么说：你好世界"

```

**步骤 3：重启服务**

```bash
# 停止当前服务 (Ctrl+C)
# 重新启动
ownbot gateway
```

启动后查看日志，确认技能已加载：

```
INFO  Loaded skill: weather 🌤️
INFO  Loaded skill: translate 🌐
```

现在你可以对机器人说：

- "翻译 'Hello World' 成中文"
- "把 '早上好' 翻译成英语"

---

## 📜 开源协议

本项目基于 [MIT](LICENSE) 协议开源。

---

## 🙏 致谢

感谢以下开源项目的支持：

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot 框架
- [@whiskeysockets/baileys](https://github.com/WhiskeySockets/Baileys) - WhatsApp Web API
- [Rich](https://github.com/Textualize/rich) - 终端美化

---

## 📮 联系我

- 💬 **Issues**: [GitHub Issues](https://github.com/yourusername/ownbot/issues)
- 📧 **Email**: sunchenhao518@163.com
- 📱 **小红书**: [@真想不到](https://xhslink.com/m/WTYcSpJfdQ) (ID: schhaohao518)

<div align="center">

### 欢迎关注我的小红书

<img src="docs/images/xiaohongshu-qr.jpg" width="200" alt="小红书二维码">

**扫码关注，一起交流！**

</div>

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给我一个 Star！**

**🚀 让我们一起打造更强大的 AI 助手！**

</div>
