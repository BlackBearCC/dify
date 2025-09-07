# -*- coding: utf-8 -*-
"""
加密货币监控系统主入口
"""

import sys
import signal
from crypto_monitor_controller import CryptoMonitorController


def signal_handler(signum, frame):
    """信号处理器"""
    print("\n🛑 收到停止信号，正在关闭系统...")
    if hasattr(signal_handler, 'controller'):
        signal_handler.controller.stop_monitoring()
    sys.exit(0)


def main():
    """主函数"""
    print("=" * 50)
    print("🚀 加密货币24小时监控系统启动")
    print("=" * 50)
    
    try:
        # 初始化系统控制器
        controller = CryptoMonitorController()
        signal_handler.controller = controller
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 显示系统状态
        status = controller.get_system_status()
        print("\n📊 系统状态:")
        print(f"  名称: {status['config']['name']}")
        print(f"  版本: {status['config']['version']}")
        print(f"  运行模式: {status['config']['mode']}")
        print(f"  分析师: {', '.join(status['analysts'])}")
        print(f"  LLM客户端: {', '.join(status['llm_clients'])}")
        
        # 启动监控
        controller.start_monitoring()
        
        print("\n" + "=" * 50)
        print("✅ 系统运行中... 按 Ctrl+C 停止")
        print("=" * 50)
        
        # 保持程序运行
        try:
            while controller.is_running:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None)
    
    except Exception as e:
        print(f"❌ 系统启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()