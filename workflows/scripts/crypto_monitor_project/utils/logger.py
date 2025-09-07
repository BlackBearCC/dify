# -*- coding: utf-8 -*-
"""
高效日志系统 - 支持快速定位和Telegram推送
"""

import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import threading
import queue
import asyncio
from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    BOTINFO = 25  # 自定义级别，会推送到Telegram


class TelegramLogger:
    """Telegram推送日志处理器"""
    
    def __init__(self, telegram_integration=None):
        self.telegram_integration = telegram_integration
        self.message_queue = queue.Queue()
        self.worker_thread = None
        self.running = False
        
    def start(self):
        """启动Telegram推送线程"""
        if self.telegram_integration and not self.running:
            self.running = True
            self.worker_thread = threading.Thread(target=self._worker, daemon=True)
            self.worker_thread.start()
            
    def stop(self):
        """停止Telegram推送线程"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=1)
    
    def send_message(self, message: str, level: str = "INFO"):
        """异步发送消息到Telegram"""
        if self.telegram_integration and self.running:
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_msg = f"🤖 [{level}] {timestamp}\n{message}"
            self.message_queue.put(formatted_msg)
    
    def _worker(self):
        """后台工作线程"""
        while self.running:
            try:
                message = self.message_queue.get(timeout=1)
                if self.telegram_integration:
                    self.telegram_integration.send_notification(message)
                self.message_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Telegram推送失败: {e}")


class SmartLogger:
    """智能日志系统"""
    
    def __init__(self, name: str = "CryptoMonitor", 
                 log_dir: str = "logs",
                 telegram_integration=None):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 创建logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # 防止重复添加handler
        if not self.logger.handlers:
            self._setup_handlers()
        
        # Telegram推送
        self.telegram_logger = TelegramLogger(telegram_integration)
        self.telegram_logger.start()
        
        # 添加自定义BOTINFO级别
        logging.addLevelName(25, "BOTINFO")
    
    def _setup_handlers(self):
        """设置日志处理器"""
        # 文件处理器 - 详细日志
        log_file = self.log_dir / f"{self.name}_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        
        # 控制台处理器 - 简洁输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(logging.INFO)
        self.logger.addHandler(console_handler)
    
    def _get_caller_info(self) -> str:
        """获取调用者信息"""
        import inspect
        frame = inspect.currentframe()
        try:
            # 向上查找到真正的调用者
            caller_frame = frame.f_back.f_back.f_back
            if caller_frame:
                filename = os.path.basename(caller_frame.f_code.co_filename)
                line_no = caller_frame.f_lineno
                func_name = caller_frame.f_code.co_name
                return f"{filename}:{line_no} {func_name}()"
        except:
            pass
        finally:
            del frame
        return "unknown"
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        caller_info = self._get_caller_info()
        self.logger.debug(f"[{caller_info}] {message}", **kwargs)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        caller_info = self._get_caller_info()
        self.logger.info(f"[{caller_info}] {message}", **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        caller_info = self._get_caller_info()
        self.logger.warning(f"[{caller_info}] {message}", **kwargs)
    
    def error(self, message: str, **kwargs):
        """错误日志"""
        caller_info = self._get_caller_info()
        self.logger.error(f"[{caller_info}] {message}", **kwargs)
    
    def critical(self, message: str, **kwargs):
        """严重错误日志"""
        caller_info = self._get_caller_info()
        self.logger.critical(f"[{caller_info}] {message}", **kwargs)
    
    def botinfo(self, message: str, **kwargs):
        """机器人信息日志 - 会推送到Telegram"""
        caller_info = self._get_caller_info()
        full_message = f"[{caller_info}] {message}"
        self.logger.log(25, full_message, **kwargs)  # BOTINFO level
        
        # 发送到Telegram
        self.telegram_logger.send_message(message, "BOTINFO")
    
    def exception(self, message: str, **kwargs):
        """异常日志 - 包含堆栈信息"""
        caller_info = self._get_caller_info()
        self.logger.exception(f"[{caller_info}] {message}", **kwargs)
    
    def close(self):
        """关闭日志系统"""
        self.telegram_logger.stop()
        for handler in self.logger.handlers:
            handler.close()


# 全局日志实例
_logger_instance: Optional[SmartLogger] = None
_logger_lock = threading.Lock()


def get_logger(name: str = "CryptoMonitor", 
               telegram_integration=None) -> SmartLogger:
    """获取全局日志实例"""
    global _logger_instance
    
    with _logger_lock:
        if _logger_instance is None:
            _logger_instance = SmartLogger(name, telegram_integration=telegram_integration)
        return _logger_instance


def set_telegram_integration(telegram_integration):
    """设置Telegram集成"""
    global _logger_instance
    if _logger_instance:
        _logger_instance.telegram_logger.telegram_integration = telegram_integration
        _logger_instance.telegram_logger.start()


# 便捷函数
def log(message: str, level: str = "INFO"):
    """简单日志函数 - 向后兼容"""
    logger = get_logger()
    level_map = {
        "DEBUG": logger.debug,
        "INFO": logger.info,
        "WARNING": logger.warning,
        "ERROR": logger.error,
        "CRITICAL": logger.critical,
        "BOTINFO": logger.botinfo
    }
    
    log_func = level_map.get(level.upper(), logger.info)
    log_func(message)


def debug(message: str):
    """调试日志"""
    get_logger().debug(message)


def info(message: str):
    """信息日志"""
    get_logger().info(message)


def warning(message: str):
    """警告日志"""
    get_logger().warning(message)


def error(message: str):
    """错误日志"""
    get_logger().error(message)


def critical(message: str):
    """严重错误日志"""
    get_logger().critical(message)


def botinfo(message: str):
    """机器人信息日志 - 推送到Telegram"""
    get_logger().botinfo(message)


def exception(message: str):
    """异常日志"""
    get_logger().exception(message)


# 设置默认日志级别的映射
__all__ = [
    'SmartLogger', 'TelegramLogger', 'LogLevel',
    'get_logger', 'set_telegram_integration',
    'log', 'debug', 'info', 'warning', 'error', 'critical', 'botinfo', 'exception'
]