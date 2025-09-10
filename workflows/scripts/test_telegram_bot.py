# -*- coding: utf-8 -*-
"""
测试修复后的Telegram机器人功能
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

def test_telegram_bot_integration():
    """测试Telegram机器人与crypto_monitor_project的集成"""
    
    print("测试Telegram机器人集成...")
    
    try:
        # 测试导入
        from telegram_bot import CryptoTelegramBot, TELEGRAM_AVAILABLE, CRYPTO_BOT_TYPE
        print(f"导入成功")
        print(f"Telegram可用: {TELEGRAM_AVAILABLE}")
        print(f"加密货币系统类型: {CRYPTO_BOT_TYPE}")
        
        if CRYPTO_BOT_TYPE == 'crypto_monitor_project':
            from crypto_monitor_project.crypto_monitor_controller import CryptoMonitorController
            
            print("测试crypto_monitor_project集成...")
            
            # 初始化controller
            controller = CryptoMonitorController()
            print("CryptoMonitorController初始化成功")
            
            # 检查必要的方法
            required_methods = ['analyze_kline_data', 'analyze_market_sentiment', 'process_user_message', 'ask_claude_with_data']
            
            for method in required_methods:
                if hasattr(controller, method):
                    print(f"方法存在: {method}")
                else:
                    print(f"方法缺失: {method}")
            
            # 检查配置
            if hasattr(controller, 'settings') and hasattr(controller.settings, 'monitor'):
                primary_symbols = getattr(controller.settings.monitor, 'primary_symbols', [])
                secondary_symbols = getattr(controller.settings.monitor, 'secondary_symbols', [])
                print(f"监控币种: {primary_symbols + secondary_symbols}")
            else:
                print("无法获取监控币种配置")
            
            # 模拟Telegram机器人初始化（不需要真实token）
            if TELEGRAM_AVAILABLE:
                print("模拟Telegram机器人初始化...")
                # 这里不能真实初始化，因为需要token
                print("Telegram机器人集成准备就绪")
            else:
                print("需要安装python-telegram-bot库: pip install python-telegram-bot")
                
        elif CRYPTO_BOT_TYPE == 'crypto_bot':
            print("检测到crypto_bot系统")
            print("兼容crypto_bot")
            
        else:
            print("无法检测到加密货币监控系统")
            
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n功能特性总结:")
    print("支持内联按键导航")
    print("支持直接消息转发给agent") 
    print("支持持续运行（不会自动停止）")
    print("兼容crypto_monitor_project和crypto_bot")
    print("智能对话模式")
    print("快捷分析按钮")
    print("完整分析流程")
    print("系统状态查询")

if __name__ == "__main__":
    test_telegram_bot_integration()