import os
import logging
from sys import stdout
from .config import settings

# 确保 logs 目录存在（对应 .gitignore 里的 logs/）
LOG_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def setup_logger(name: str = "ai_copilot") -> logging.Logger:
    """
    配置并返回一个全局的 Logger 实例。
    同时输出到控制台和本地文件。
    """
    logger = logging.getLogger(name)

    # 避免重复添加 Handler 导致日志重复打印
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # 定义日志输出格式
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(module)s:%(funcName)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # 1. 控制台处理器 (StreamHandler)
        console_handler = logging.StreamHandler(stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 2. 文件处理器 (FileHandler) - 按 utf-8 编码写入文件
        log_file_path = os.path.join(LOG_DIR, "app.log")
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 导出一个实例化好的 logger 供全局使用
logger = setup_logger()