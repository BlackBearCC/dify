# -*- coding: utf-8 -*-
# 导入新的日志系统
from .logger import (
    log, debug, info, warning, error, critical, botinfo, exception,
    get_logger, set_telegram_integration, SmartLogger, LogLevel
)

# 向后兼容
safe_print = log

def init_console_encoding():
    """空函数，保持兼容性"""
    pass

__all__ = [
    'log', 'debug', 'info', 'warning', 'error', 'critical', 'botinfo', 'exception',
    'get_logger', 'set_telegram_integration', 'SmartLogger', 'LogLevel',
    'safe_print', 'init_console_encoding'
]