"""Observability and logging utilities for OwnBot.

Provides colored, structured logging output using rich library
to help developers visualize the Agent Loop execution.
"""

from __future__ import annotations

from typing import Any

from loguru import logger
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme

# Create a custom theme for OwnBot
OWNBOT_THEME = Theme(
    {
        "thought": "blue",
        "reasoning": "magenta",
        "action": "yellow",
        "observation": "cyan",
        "final": "green",
        "error": "red",
        "info": "white",
        "warning": "orange3",
        "debug": "dim",
    }
)

# Global console instance
console = Console(theme=OWNBOT_THEME)


def setup_logging():
    """Setup unified logging with rich handler."""
    # Remove default handler
    logger.remove()

    # Add rich handler for nice console output
    logger.add(
        RichHandler(
            console=console,
            show_path=False,
            show_time=True,
            rich_tracebacks=True,
        ),
        level="INFO",
    )

    # Also add file handler for persistent logs
    logger.add(
        "~/.ownbot/logs/ownbot.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
    )


class AgentLogger:
    """Structured logger for Agent Loop observability.

    Provides colored output for different stages of the agent loop:
    - [模型推理] Magenta - Hidden model reasoning shown only in logs
    - [工具前说明] Blue - Model-provided note before a tool call
    - [调用工具] Yellow - Tool execution
    - [观察结果] Cyan - Tool results
    - [最终回复] Green - Final answer
    - [错误] Red - Errors
    """

    def __init__(self, session_key: str):
        self.session_key = session_key
        self.iteration = 0

    def start_iteration(self, iteration: int):
        """Log the start of a new iteration."""
        self.iteration = iteration
        console.print()
        console.rule(f"[bold blue]Iteration {iteration}[/bold blue]", style="blue")

    def log_reasoning(self, reasoning: str):
        """Log hidden model reasoning in magenta for debugging only."""
        display = reasoning[:1500] + "..." if len(reasoning) > 1500 else reasoning
        panel = Panel(
            Text(display, style="reasoning"),
            title="[bold magenta]🧠 模型推理[/bold magenta]",
            border_style="magenta",
            padding=(1, 2),
        )
        console.print(panel)

    def log_thought(self, thought: str):
        """Log model-provided note before a tool call."""
        panel = Panel(
            Text(thought, style="thought"),
            title="[bold blue]📝 工具前说明[/bold blue]",
            border_style="blue",
            padding=(1, 2),
        )
        console.print(panel)

    def log_action(self, action: str, action_input: dict[str, Any]):
        """Log tool action in yellow."""
        import json

        content = f"[bold]{action}[/bold]\n"
        content += f"参数: {json.dumps(action_input, ensure_ascii=False, indent=2)}"

        panel = Panel(
            Text.from_markup(content),
            title="[bold yellow]🔧 调用工具[/bold yellow]",
            border_style="yellow",
            padding=(1, 2),
        )
        console.print(panel)

    def log_observation(self, result: str):
        """Log tool observation in cyan."""
        # Truncate long results
        display_result = result[:500] + "..." if len(result) > 500 else result

        panel = Panel(
            Text(display_result, style="observation"),
            title="[bold cyan]👁️ 观察结果[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
        console.print(panel)

    def log_final_answer(self, answer: str):
        """Log final answer in green."""
        panel = Panel(
            Text(answer, style="final"),
            title="[bold green]✅ 最终回复[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
        console.print(panel)

    def log_error(self, error: str):
        """Log error in red."""
        panel = Panel(
            Text(error, style="error"),
            title="[bold red]❌ 错误[/bold red]",
            border_style="red",
            padding=(1, 2),
        )
        console.print(panel)

    def log_progress(self, message: str):
        """Log progress message."""
        console.print(f"[dim blue]⏳ {message}[/dim blue]")


def create_agent_logger(session_key: str) -> AgentLogger:
    """Create a new AgentLogger instance for a session."""
    return AgentLogger(session_key)


def log_session_start(session_key: str, message: str):
    """Log the start of a new session."""
    console.print()
    console.rule(f"[bold green]🚀 新会话: {session_key}[/bold green]", style="green")
    console.print(
        f"[dim]用户消息: {message[:100]}...[/dim]"
        if len(message) > 100
        else f"[dim]用户消息: {message}[/dim]"
    )
    console.print()


def log_session_end(session_key: str):
    """Log the end of a session."""
    console.print()
    console.rule(f"[bold dim]会话结束: {session_key}[/bold dim]", style="dim")
    console.print()


# Initialize logging on module import
setup_logging()
