#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite Tool for Dify - 启动器
自动安装依赖并启动API服务
"""

import subprocess
import sys
import os

def install_dependencies():
    """安装所需依赖"""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'flask', 'flask-cors'])
        print("Dependencies installed successfully!")
    except subprocess.CalledProcessError:
        print("Failed to install dependencies. Please install manually:")
        print("   pip install flask flask-cors")
        sys.exit(1)

def start_api_server():
    """启动API服务器"""
    print("Starting SQLite Tool API Server...")
    try:
        # 切换到工具目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        # 导入并启动服务器
        from sqlite_api_server import app
        app.run(host='0.0.0.0', port=5555, debug=False)
        
    except ImportError:
        print("Failed to import sqlite_api_server")
        sys.exit(1)
    except Exception as e:
        print(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    print("=" * 50)
    print("SQLite Tool for Dify")
    print("=" * 50)
    
    # 检查并安装依赖
    try:
        import flask
        import flask_cors
        print("Dependencies already installed")
    except ImportError:
        install_dependencies()
    
    # 启动服务器
    start_api_server()