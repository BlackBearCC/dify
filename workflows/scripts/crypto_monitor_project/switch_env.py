#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API环境切换脚本 - 一体化版本
支持包月API和流量API切换
"""

import os
import sys
import requests
import subprocess
from typing import Dict, Any


class EnvSwitcher:
    """环境切换器"""
    
    def __init__(self):
        self.environments = {
            "1": {
                "name": "包月API - 大陆首选",
                "url": "https://clubcdn.383338.xyz",
                "token": "sk-NgqOJ3hniOEXCqGZs2iVIv7cwyKeFWa4N3W9GAEb4BthSF0J",
                "description": "大陆CDN加速"
            },
            "2": {
                "name": "包月API - 大陆次选",
                "url": "https://club.claudemax.xyz", 
                "token": "sk-NgqOJ3hniOEXCqGZs2iVIv7cwyKeFWa4N3W9GAEb4BthSF0J",
                "description": "大陆次选"
            },
            "3": {
                "name": "包月API - 全球线路",
                "url": "https://club.claudecode.site",
                "token": "sk-NgqOJ3hniOEXCqGZs2iVIv7cwyKeFWa4N3W9GAEb4BthSF0J",
                "description": "主站点全球加速"
            },
            "4": {
                "name": "包月API - 全球加速",
                "url": "https://club.383338.xyz",
                "token": "sk-NgqOJ3hniOEXCqGZs2iVIv7cwyKeFWa4N3W9GAEb4BthSF0J",
                "description": "全球加速"
            },
            "5": {
                "name": "流量API",
                "url": "https://api.anthropic.com",
                "token": "ck_54b914d0077c32f6185498ed03299b6d",
                "description": "官方流量计费API"
            }
        }
    
    def display_menu(self):
        """显示菜单"""
        print("\n" + "="*60)
        print("🔧 API环境切换工具")
        print("="*60)
        print("当前环境:")
        current_url = os.getenv('ANTHROPIC_BASE_URL', '未设置')
        current_token = os.getenv('ANTHROPIC_AUTH_TOKEN', '未设置')
        print(f"  URL: {current_url}")
        print(f"  Token: {current_token[:20]}..." if len(current_token) > 20 else f"  Token: {current_token}")
        print("="*60)
        print("选择环境:")
        for key, env in self.environments.items():
            print(f"  {key}. {env['name']}")
            print(f"     {env['description']} - {env['url']}")
        print("  t. 测试当前连接")
        print("  v. 查看环境变量详情")
        print("  r. 重新加载系统环境变量")
        print("  0. 退出")
        print("="*60)
    
    def set_environment(self, choice: str) -> bool:
        """设置环境"""
        if choice in self.environments:
            return self._set_api_environment(choice)
        else:
            print("❌ 无效选择")
            return False
    
    def _set_api_environment(self, choice: str) -> bool:
        """设置API环境"""
        env = self.environments[choice]
        
        # 如果是流量API，需要用户输入token
        if choice == "5" and env['token'] == "YOUR_TOKEN_HERE":
            print("\n请输入您的流量API Token:")
            token = input("Token: ").strip()
            if not token:
                print("❌ Token不能为空")
                return False
            env['token'] = token
        
        try:
            # 先保存到系统环境变量
            if sys.platform == "win32":
                # Windows系统 - 使用setx命令保存到用户环境变量
                result1 = subprocess.run(['setx', 'ANTHROPIC_BASE_URL', env['url']], 
                                       capture_output=True, text=True, shell=True)
                result2 = subprocess.run(['setx', 'ANTHROPIC_AUTH_TOKEN', env['token']], 
                                       capture_output=True, text=True, shell=True)
                
                if result1.returncode == 0 and result2.returncode == 0:
                    print("✅ 环境变量已保存到系统")
                else:
                    print("⚠️ 保存到系统环境变量时出现问题，但当前会话已设置")
            else:
                # Linux/Mac系统 - 提示用户手动设置
                print("⚠️ Linux/Mac系统需要手动设置环境变量:")
                print(f"   export ANTHROPIC_BASE_URL='{env['url']}'")
                print(f"   export ANTHROPIC_AUTH_TOKEN='{env['token']}'")
                print("   请将上述命令添加到 ~/.bashrc 或 ~/.zshrc 文件中")
            
            # 设置当前会话的环境变量
            os.environ['ANTHROPIC_BASE_URL'] = env['url']
            os.environ['ANTHROPIC_AUTH_TOKEN'] = env['token']
            
            print(f"✅ 已切换到: {env['name']}")
            print(f"   URL: {env['url']}")
            print(f"   描述: {env['description']}")
            print(f"   Token: {env['token'][:20]}...")
            
            if sys.platform == "win32":
                print("💡 提示: 环境变量已保存，新开的命令行窗口将自动使用新设置")
            
            return True
            
        except Exception as e:
            print(f"❌ 设置失败: {e}")
            return False
    
    def test_connection(self) -> bool:
        """测试当前连接"""
        current_url = os.getenv('ANTHROPIC_BASE_URL')
        current_token = os.getenv('ANTHROPIC_AUTH_TOKEN')
        
        if not current_url or not current_token:
            print("❌ 当前环境未设置完整")
            return False
        
        print(f"\n🔍 测试连接...")
        print(f"   URL: {current_url}")
        print(f"   Token: {current_token[:20]}...")
        
        try:
            headers = {
                'Authorization': f'Bearer {current_token}',
                'Content-Type': 'application/json'
            }
            
            test_payload = {
                "model": "claude-3-sonnet-20240229",
                "max_tokens": 10,
                "messages": [{"role": "user", "content": "Hello"}]
            }
            
            response = requests.post(
                f"{current_url}/v1/messages",
                json=test_payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                print("✅ 连接测试成功")
                return True
            else:
                print(f"❌ 连接测试失败: {response.status_code}")
                if response.text:
                    print(f"   错误: {response.text[:200]}")
                return False
                
        except requests.exceptions.Timeout:
            print("❌ 连接超时")
            return False
        except Exception as e:
            print(f"❌ 连接测试异常: {e}")
            return False
    
    def view_environment_variables(self):
        """查看环境变量详情"""
        print("\n" + "="*60)
        print("📋 环境变量详情")
        print("="*60)
        
        # 获取当前环境变量
        current_url = os.getenv('ANTHROPIC_BASE_URL')
        current_token = os.getenv('ANTHROPIC_AUTH_TOKEN')
        
        print("当前设置的环境变量:")
        print(f"  ANTHROPIC_BASE_URL: {current_url if current_url else '未设置'}")
        print(f"  ANTHROPIC_AUTH_TOKEN: {current_token if current_token else '未设置'}")
        
        # 显示Token的详细信息
        if current_token:
            print(f"\nToken详情:")
            print(f"  长度: {len(current_token)} 字符")
            print(f"  前缀: {current_token[:10]}...")
            print(f"  后缀: ...{current_token[-10:]}")
            
            # 判断Token类型
            if current_token.startswith('ck_'):
                print(f"  类型: 包月API Token")
            elif current_token.startswith('sk-'):
                print(f"  类型: 官方API Token")
            else:
                print(f"  类型: 未知类型")
        
        # 显示URL的详细信息
        if current_url:
            print(f"\nURL详情:")
            print(f"  协议: {current_url.split('://')[0] if '://' in current_url else '未知'}")
            print(f"  域名: {current_url.split('://')[1].split('/')[0] if '://' in current_url else '未知'}")
            
            # 判断URL类型
            if 'clubcdn.383338.xyz' in current_url:
                print(f"  类型: 包月API - 大陆首选 (CDN加速)")
            elif 'club.claudemax.xyz' in current_url:
                print(f"  类型: 包月API - 大陆次选")
            elif 'club.claudecode.site' in current_url:
                print(f"  类型: 包月API - 全球线路")
            elif 'club.383338.xyz' in current_url:
                print(f"  类型: 包月API - 全球加速")
            elif 'api.anthropic.com' in current_url:
                print(f"  类型: 官方流量API")
            else:
                print(f"  类型: 自定义API")
        
        # 显示系统环境变量状态
        print(f"\n系统环境变量状态:")
        try:
            if sys.platform == "win32":
                # Windows系统
                import subprocess
                result_url = subprocess.run(['reg', 'query', 'HKCU\\Environment', '/v', 'ANTHROPIC_BASE_URL'], 
                                          capture_output=True, text=True, shell=True)
                result_token = subprocess.run(['reg', 'query', 'HKCU\\Environment', '/v', 'ANTHROPIC_AUTH_TOKEN'], 
                                            capture_output=True, text=True, shell=True)
                
                if result_url.returncode == 0:
                    print(f"  ANTHROPIC_BASE_URL: 已保存到系统环境变量")
                else:
                    print(f"  ANTHROPIC_BASE_URL: 未保存到系统环境变量")
                
                if result_token.returncode == 0:
                    print(f"  ANTHROPIC_AUTH_TOKEN: 已保存到系统环境变量")
                else:
                    print(f"  ANTHROPIC_AUTH_TOKEN: 未保存到系统环境变量")
            else:
                # Linux/Mac系统
                print(f"  系统: Linux/Mac (需要手动检查 ~/.bashrc 或 ~/.zshrc)")
        except Exception as e:
            print(f"  检查系统环境变量时出错: {e}")
        
        print("="*60)
    
    def reload_system_environment(self):
        """重新加载系统环境变量"""
        print("\n🔄 重新加载系统环境变量...")
        
        try:
            if sys.platform == "win32":
                # Windows系统 - 从注册表读取环境变量
                import winreg
                
                # 读取用户环境变量
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                    try:
                        url_value, _ = winreg.QueryValueEx(key, "ANTHROPIC_BASE_URL")
                        os.environ['ANTHROPIC_BASE_URL'] = url_value
                        print(f"✅ 重新加载 ANTHROPIC_BASE_URL: {url_value}")
                    except FileNotFoundError:
                        print("⚠️ 系统环境变量中未找到 ANTHROPIC_BASE_URL")
                    
                    try:
                        token_value, _ = winreg.QueryValueEx(key, "ANTHROPIC_AUTH_TOKEN")
                        os.environ['ANTHROPIC_AUTH_TOKEN'] = token_value
                        print(f"✅ 重新加载 ANTHROPIC_AUTH_TOKEN: {token_value[:20]}...")
                    except FileNotFoundError:
                        print("⚠️ 系统环境变量中未找到 ANTHROPIC_AUTH_TOKEN")
                
                print("💡 提示: 当前会话的环境变量已更新")
                
            else:
                # Linux/Mac系统
                print("⚠️ Linux/Mac系统需要手动重新加载环境变量")
                print("   请运行: source ~/.bashrc 或 source ~/.zshrc")
                
        except Exception as e:
            print(f"❌ 重新加载环境变量失败: {e}")
            print("💡 建议: 重新启动命令行窗口以加载最新的环境变量")
    
    def run(self):
        """运行主程序"""
        while True:
            self.display_menu()
            
            try:
                choice = input("\n请选择 (0-5, t, v, r): ").strip().lower()
                
                if choice == "0":
                    print("\n👋 退出")
                    break
                elif choice == "t":
                    self.test_connection()
                elif choice == "v":
                    self.view_environment_variables()
                elif choice == "r":
                    self.reload_system_environment()
                elif choice in self.environments:
                    self.set_environment(choice)
                else:
                    print("❌ 无效选择")
                
                input("\n按回车键继续...")
                
            except KeyboardInterrupt:
                print("\n\n👋 用户取消")
                break
            except Exception as e:
                print(f"\n❌ 错误: {e}")
                input("按回车键继续...")


def main():
    """主函数"""
    print("🚀 API环境切换工具")
    switcher = EnvSwitcher()
    switcher.run()


if __name__ == "__main__":
    main()
