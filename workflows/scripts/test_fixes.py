#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的系统
"""

import time
import sys
import os

# 添加路径
sys.path.append('.')
sys.path.append('crypto_monitor_project')

from crypto_monitor_project import CryptoMonitorController

def main():
    """测试修复后的系统"""
    print("启动智能交易主脑系统...")
    
    try:
        # 初始化控制器
        controller = CryptoMonitorController('crypto_monitor_project/config/crypto_monitor_config.yaml')
        
        print("="*60)
        print("智能交易主脑已就绪！")
        print("="*60)
        
        # 测试启动监控（短时间）
        print("启动监控系统测试...")
        controller.start_monitoring()
        
        # 运行10秒测试
        print("运行10秒测试...")
        time.sleep(10)
        
        # 停止系统
        print("停止系统...")
        controller.stop_monitoring()
        print("系统已停止，测试完成！")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()