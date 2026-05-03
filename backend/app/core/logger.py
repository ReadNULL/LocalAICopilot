import logging
import sys
from pathlib import Path
from datetime import datetime

from app.core.config import settings


def setup_logger(name: str = "app") -> logging.Logger:
    """
    创建并返回一个标准 Logger
    """

    logger = logging.getLogger(name)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # =========================
    # 日志格式
    # =========================
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
        "%Y-%m-%d %H:%M:%S"
    )

    # =========================
    # 控制台输出
    # =========================
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # =========================
    # 文件日志（按天）
    # =========================
    log_dir = settings.DATA_DIR / "logs"
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# =========================
# 全局 logger（推荐直接用）
# =========================
logger = setup_logger("LocalAICopilot")