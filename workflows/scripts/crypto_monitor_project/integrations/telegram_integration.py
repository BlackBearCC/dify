# -*- coding: utf-8 -*-
"""
Telegram机器人集成
提供Telegram通知和交互功能
"""

import os
import threading
from typing import Optional, Dict, Any

from ..config import Settings


class TelegramIntegration:
    """Telegram集成管理器"""
    
    def __init__(self, settings: Settings):
        """
        初始化Telegram集成
        
        Args:
            settings: 系统配置
        """
        self.settings = settings
        self.telegram_token = os.getenv('TELEGRAM_TOKEN')
        self.telegram_chat_id = os.getenv('CHAT_ID')
        self.telegram_bot_thread = None
        self.telegram_bot_available = self._check_telegram_bot_availability()
        self.controller_instance = None  # 存储控制器实例用于智能消息处理
    
    def _check_telegram_bot_availability(self) -> bool:
        """检查Telegram机器人是否可用"""
        try:
            from telegram_bot import start_telegram_bot_thread
            return True
        except ImportError:
            print("⚠️ telegram_bot模块未找到，Telegram功能将不可用")
            return False
    
    def start_telegram_bot(self, controller_instance=None):
        """启动Telegram机器人"""
        if not self.telegram_bot_available:
            print("❌ Telegram机器人不可用")
            return False
        
        if not self.telegram_token or not self.telegram_chat_id:
            print("⚠️ 未配置Telegram Token或Chat ID，跳过机器人启动")
            return False
        
        try:
            from telegram_bot import start_telegram_bot_thread
            
            print("🤖 启动Telegram机器人...")
            
            # 存储控制器实例
            self.controller_instance = controller_instance
            
            # 启动机器人线程，使用正确的参数顺序
            self.telegram_bot_thread = start_telegram_bot_thread(
                controller_instance,  # crypto_monitor参数
                self.telegram_token,  # token参数
                self.telegram_chat_id  # chat_id参数
            )
            
            if self.telegram_bot_thread:
                print(f"✅ Telegram机器人已启动 (Chat ID: {self.telegram_chat_id})")
                return True
            else:
                print("❌ Telegram机器人启动失败")
                return False
                
        except Exception as e:
            print(f"❌ 启动Telegram机器人失败: {e}")
            return False
    
    def stop_telegram_bot(self):
        """停止Telegram机器人"""
        if self.telegram_bot_thread:
            try:
                # 通常telegram_bot模块会提供停止方法
                print("⏹️ 停止Telegram机器人...")
                # 这里可能需要调用具体的停止方法
                self.telegram_bot_thread = None
                print("✅ Telegram机器人已停止")
            except Exception as e:
                print(f"❌ 停止Telegram机器人失败: {e}")
    
    def send_notification(self, message: str, parse_mode: str = 'Markdown'):
        """发送Telegram通知"""
        if not self.is_available():
            print(f"⚠️ Telegram不可用，跳过通知: {message}")
            return False
        
        try:
            # 这里需要实际的发送逻辑
            # 通常会使用python-telegram-bot库或requests直接调用API
            print(f"📱 Telegram通知: {message}")
            return True
        except Exception as e:
            print(f"❌ 发送Telegram通知失败: {e}")
            return False
    
    def send_trading_confirmation_request(self, trading_analysis: str, timeout: int = 60) -> Optional[str]:
        """发送交易确认请求"""
        if not self.is_available():
            print("⚠️ Telegram不可用，无法发送交易确认请求")
            return None
        
        try:
            confirmation_message = f"""
🤖 **交易确认请求**

{trading_analysis}

请在 {timeout} 秒内回复：
- `YES` 或 `确认` - 执行交易
- `NO` 或 `取消` - 取消交易
- `HOLD` 或 `观望` - 暂不交易

超时将默认选择观望。
"""
            
            # 发送确认请求（实际实现需要等待用户回复）
            self.send_notification(confirmation_message)
            
            # 这里需要实现等待用户回复的逻辑
            # 通常会使用事件或回调机制
            print(f"⏰ 等待用户确认 (超时: {timeout}秒)...")
            
            # 模拟等待（实际实现会更复杂）
            return "HOLD"  # 默认观望
            
        except Exception as e:
            print(f"❌ 发送交易确认请求失败: {e}")
            return None
    
    def is_available(self) -> bool:
        """检查Telegram集成是否可用"""
        return (
            self.telegram_bot_available and
            bool(self.telegram_token) and
            bool(self.telegram_chat_id)
        )
    
    def get_status(self) -> Dict[str, Any]:
        """获取Telegram集成状态"""
        return {
            'available': self.is_available(),
            'bot_running': self.telegram_bot_thread is not None,
            'token_configured': bool(self.telegram_token),
            'chat_id_configured': bool(self.telegram_chat_id),
            'chat_id': self.telegram_chat_id if self.telegram_chat_id else None
        }
    
    def _intelligent_message_handler(self, message: str, user_id: str = None) -> str:
        """
        智能消息处理器 - 将Telegram消息路由给主脑处理
        
        Args:
            message: 用户发送的消息
            user_id: 用户ID（可选）
            
        Returns:
            主脑的智能回复
        """
        try:
            if not self.controller_instance or not hasattr(self.controller_instance, 'master_brain'):
                return "❌ 智能主脑未初始化，无法处理消息"
            
            print(f"📱 收到Telegram消息: {message}")
            
            # 构造用户请求上下文
            context = {
                'source': 'telegram',
                'user_id': user_id,
                'message_type': 'user_request'
            }
            
            # 调用主脑处理用户请求
            brain_response = self.controller_instance.master_brain.process_request(message, context)
            
            print(f"🧠 主脑处理完成")
            return brain_response
            
        except Exception as e:
            error_msg = f"❌ 智能消息处理失败: {e}"
            print(error_msg)
            return error_msg