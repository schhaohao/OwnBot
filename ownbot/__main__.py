from pathlib import Path

# Ensure log directory exists before importing other modules
log_dir = Path("~/.ownbot/logs").expanduser()
log_dir.mkdir(parents=True, exist_ok=True)

# Import and setup logging
from ownbot.utils.logger import setup_logging
setup_logging()

from ownbot.cli import app

if __name__ == "__main__":
    app()
