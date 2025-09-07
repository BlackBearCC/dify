#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能交易主脑系统 - 使用示例
展示如何使用LLM主脑进行智能交易决策
"""

import time
from crypto_monitor_project import CryptoMonitorController

def main():
    """智能交易主脑使用示例"""
    print("🚀 启动智能交易主脑系统...")
    
    # 初始化控制器（包含智能主脑）
    controller = CryptoMonitorController('crypto_monitor_config.yaml')
    
    print("\n" + "="*80)
    print("🧠 智能交易主脑已就绪！")
    print("="*80)
    
    # 示例1: 启动心跳监控（主脑自主决策）
    print("\n📝 示例1: 启动心跳监控")
    controller.start_monitoring()  # 主脑会在心跳中自主分析和决策
    
    # 示例2: 直接向主脑提问
    print("\n📝 示例2: 直接与主脑对话")
    user_questions = [
        "分析一下当前BTC的情况",
        "现在有什么好的交易机会吗？",
        "帮我看看账户状态",
        "ETH技术面怎么样？"
    ]
    
    for question in user_questions:
        print(f"\n👤 用户: {question}")
        response = controller.process_user_message(question)
        print(f"🧠 主脑: {response}")
        print("-" * 50)
        time.sleep(2)
    
    # 示例3: Telegram消息处理（如果配置了Telegram）
    print("\n📝 示例3: 模拟Telegram消息")
    if controller.telegram_integration.is_available():
        telegram_messages = [
            "快速分析一下市场",
            "BTC现在可以买吗？", 
            "我的持仓情况如何？"
        ]
        
        for msg in telegram_messages:
            print(f"\n📱 Telegram消息: {msg}")
            response = controller.telegram_integration._intelligent_message_handler(msg)
            print(f"🧠 主脑回复: {response}")
            time.sleep(2)
    else:
        print("⚠️ Telegram未配置，跳过Telegram示例")
    
    # 运行一段时间让主脑进行心跳决策
    print("\n⏰ 运行60秒，观察主脑自主决策...")
    time.sleep(60)
    
    # 停止系统
    print("\n🛑 停止系统...")
    controller.stop_monitoring()
    print("✅ 系统已停止")

if __name__ == "__main__":
    main()