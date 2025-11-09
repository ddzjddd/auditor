"""
结构化日志系统
支持JSON格式日志和追踪ID
"""
import sys
import json
from typing import Any, Dict
from loguru import logger
from datetime import datetime
import uuid

from config import get_config


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self):
        self.config = get_config()
        self._setup_logger()
    
    def _setup_logger(self):
        """配置日志器"""
        # 移除默认handler
        logger.remove()
        
        # 控制台输出
        if self.config.enable_json_log:
            logger.add(
                sys.stderr,
                format=self._json_formatter,
                level=self.config.log_level,
                serialize=True
            )
        else:
            logger.add(
                sys.stderr,
                format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
                level=self.config.log_level,
                colorize=True
            )
        
        # 文件输出
        if self.config.log_file:
            logger.add(
                self.config.log_file,
                format=self._json_formatter if self.config.enable_json_log else "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                level=self.config.log_level,
                rotation="10 MB",
                retention="7 days",
                serialize=self.config.enable_json_log
            )
    
    def _json_formatter(self, record: Dict[str, Any]) -> str:
        """JSON格式格式化器"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "module": record["name"],
            "function": record["function"],
            "line": record["line"],
        }
        
        # 添加额外字段
        if "trace_id" in record["extra"]:
            log_data["trace_id"] = record["extra"]["trace_id"]
        if "tool_name" in record["extra"]:
            log_data["tool_name"] = record["extra"]["tool_name"]
        if "tool_args" in record["extra"]:
            log_data["tool_args"] = record["extra"]["tool_args"]
        
        return json.dumps(log_data, ensure_ascii=False)
    
    def get_logger(self, trace_id: str = None):
        """获取带追踪ID的日志器"""
        if trace_id is None:
            trace_id = str(uuid.uuid4())
        
        return logger.bind(trace_id=trace_id)


# 全局日志器实例
_structured_logger: StructuredLogger = None


def setup_logging():
    """初始化日志系统"""
    global _structured_logger
    _structured_logger = StructuredLogger()
    return _structured_logger.get_logger()


def get_logger(trace_id: str = None):
    """获取日志器"""
    if _structured_logger is None:
        setup_logging()
    return _structured_logger.get_logger(trace_id)

