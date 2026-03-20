# OwnBot 开发指南

本指南介绍 OwnBot 项目的开发工具链和最佳实践。

## 🚀 快速开始

### 安装开发依赖

```bash
# 安装项目及所有开发依赖
pip install -e ".[dev]"

# 安装 pre-commit hooks
pre-commit install
```

### 验证安装

```bash
# 运行测试
make test

# 检查代码质量
make lint
make type-check
```

## 🛠️ 开发工具

### Makefile 命令

我们提供了 Makefile 来简化常见任务：

```bash
make help              # 显示所有可用命令
make install-dev       # 安装开发依赖
make test              # 运行所有测试
make test-unit         # 仅运行单元测试
make coverage          # 生成测试覆盖率报告
make lint              # 运行代码检查
make format            # 格式化代码
make type-check        # 运行类型检查
make pre-commit        # 运行所有 pre-commit hooks
make clean             # 清理构建产物
```

### 测试

#### 运行测试

```bash
# 运行所有测试
pytest

# 运行单元测试（推荐）
pytest tests/unit -v

# 运行测试并生成覆盖率报告
pytest --cov=ownbot --cov-report=html

# 并行运行测试（更快）
pytest -n auto

# 运行特定测试
pytest tests/unit/test_config.py -v

# 运行标记为慢的测试
pytest -m slow

# 跳过慢的测试
pytest -m "not slow"
```

#### 测试结构

```
tests/
├── conftest.py           # pytest 配置和 fixtures
├── unit/                 # 单元测试
│   ├── test_types.py
│   ├── test_exceptions.py
│   ├── test_config.py
│   └── ...
└── integration/          # 集成测试
    └── test_config_integration.py
```

#### 编写测试

```python
# tests/unit/test_my_module.py
import pytest
from ownbot.my_module import MyClass

class TestMyClass:
    """Test MyClass functionality."""

    def test_basic_functionality(self):
        """Test basic functionality."""
        obj = MyClass()
        result = obj.do_something()
        assert result == "expected"

    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test async functionality."""
        obj = MyClass()
        result = await obj.do_something_async()
        assert result == "expected"

    @pytest.mark.slow
    def test_slow_operation(self):
        """Test that takes a long time."""
        # This test will be skipped with -m "not slow"
        pass
```

### 代码质量工具

#### Ruff (Linting & Formatting)

Ruff 用于代码检查和格式化，替代了 flake8、black、isort 等多个工具：

```bash
# 检查代码
ruff check ownbot tests

# 自动修复问题
ruff check --fix ownbot tests

# 格式化代码
ruff format ownbot tests

# 检查格式
ruff format --check ownbot tests
```

配置位于 `pyproject.toml` 的 `[tool.ruff]` 部分。

#### mypy (Type Checking)

```bash
# 运行类型检查
mypy ownbot

# 严格模式
mypy ownbot --strict
```

配置位于 `pyproject.toml` 的 `[tool.mypy]` 部分。

#### Pre-commit Hooks

Pre-commit 在提交前自动运行代码检查：

```bash
# 安装 hooks
pre-commit install

# 手动运行所有 hooks
pre-commit run --all-files

# 运行特定 hook
pre-commit run ruff

# 跳过 hooks 提交（不推荐）
git commit -m "message" --no-verify
```

配置位于 `.pre-commit-config.yaml`。

### 代码覆盖率

```bash
# 生成覆盖率报告
pytest --cov=ownbot --cov-report=html

# 查看 HTML 报告
open htmlcov/index.html

# 生成 XML 报告（用于 CI）
pytest --cov=ownbot --cov-report=xml
```

配置位于 `pyproject.toml` 的 `[tool.coverage.*]` 部分。

## 🔧 配置详解

### pyproject.toml

项目的核心配置文件，包含：

- `[project]`: 项目元数据和依赖
- `[project.optional-dependencies]`: 开发依赖
- `[tool.pytest.ini_options]`: pytest 配置
- `[tool.mypy]`: mypy 类型检查配置
- `[tool.ruff]`: Ruff 代码检查配置
- `[tool.coverage.*]`: 覆盖率配置

### GitHub Actions

CI/CD 配置位于 `.github/workflows/ci.yml`：

- **Lint**: 代码检查和格式化验证
- **Test**: 多版本 Python 测试 (3.11, 3.12, 3.13)
- **Integration Tests**: 集成测试（可选）
- **Security**: 安全扫描 (bandit)
- **Build**: 包构建验证

## 📝 开发规范

### 代码风格

1. **导入排序**: 使用 Ruff 自动处理
   ```python
   from __future__ import annotations

   # 标准库
   import asyncio
   from pathlib import Path

   # 第三方库
   import httpx
   from loguru import logger

   # 本项目
   from ownbot.types import JsonDict
   ```

2. **类型注解**: 所有函数都必须有类型注解
   ```python
   def process_data(data: JsonDict) -> str:
       ...

   async def fetch_data(url: str) -> dict[str, Any]:
       ...
   ```

3. **文档字符串**: 使用 Google 风格
   ```python
   def my_function(arg1: str, arg2: int) -> bool:
       """
       Brief description.

       Longer description if needed.

       Args:
           arg1: Description of arg1
           arg2: Description of arg2

       Returns:
           Description of return value

       Raises:
           ValueError: When input is invalid
       """
   ```

### 测试规范

1. **测试类命名**: `Test{ClassName}`
2. **测试方法命名**: `test_{scenario}_{expected_behavior}`
3. **使用 pytest.mark**: 标记慢测试、集成测试等
4. **Fixture 复用**: 在 `conftest.py` 中定义共享 fixtures

### Git 提交规范

提交信息格式：

```
<type>: <subject>

<body> (optional)

<footer> (optional)
```

类型：
- `feat`: 新功能
- `fix`: 修复
- `docs`: 文档
- `style`: 格式（不影响代码运行）
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

示例：
```
feat: add support for WhatsApp voice messages

Implement audio transcription for WhatsApp voice messages
using the OpenAI Whisper API.
```

## 🐛 调试技巧

### 日志

项目使用 Loguru 进行日志记录：

```python
from loguru import logger

logger.debug("Debug message: {}", variable)
logger.info("Info message")
logger.warning("Warning: {}", warning_msg)
logger.error("Error occurred", exc_info=True)
```

### 调试测试

```bash
# 详细输出
pytest -v --tb=long

# 在第一个失败处停止
pytest -x

# 进入 PDB 调试
pytest --pdb

# 只运行失败的测试
pytest --lf
```

## 📦 发布流程

1. 更新版本号 (`ownbot/__init__.py`)
2. 更新 CHANGELOG
3. 运行完整测试：`make test`
4. 构建包：`make build`
5. 检查包：`make check`
6. 发布：`make upload`

## 🔗 有用链接

- [pytest 文档](https://docs.pytest.org/)
- [Ruff 文档](https://docs.astral.sh/ruff/)
- [mypy 文档](https://mypy.readthedocs.io/)
- [pre-commit 文档](https://pre-commit.com/)
