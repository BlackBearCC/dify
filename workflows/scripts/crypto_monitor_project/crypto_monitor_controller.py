# -*- coding: utf-8 -*-
"""
加密货币监控系统主控制器 - 重构版本
轻量级协调器，遵循单一职责原则，协调各服务模块工作
"""

from typing import Dict, List, Any, Optional
from pathlib import Path

# 导入处理 - 支持直接运行和模块导入
try:
    # 作为模块导入时使用相对导入
    from .config import ConfigManager, Settings
    from .database import DatabaseManager
    from .core import IndicatorCalculator, MasterBrain
    from .trading import PortfolioManager
    from .integrations import TelegramIntegration
    from .services import AnalysisService, DataService, FormattingService, MonitoringService
except ImportError:
    # 直接运行时使用绝对导入
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    
    from crypto_monitor_project.config import ConfigManager, Settings
    from crypto_monitor_project.database import DatabaseManager
    from crypto_monitor_project.core import IndicatorCalculator, MasterBrain
    from crypto_monitor_project.trading import PortfolioManager
    from crypto_monitor_project.integrations import TelegramIntegration
    from crypto_monitor_project.services import AnalysisService, DataService, FormattingService, MonitoringService


class CryptoMonitorController:
    """加密货币监控系统控制器 - 轻量级协调器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化监控系统控制器"""
        # 加载环境变量
        self._load_environment_variables()
        
        print("🚀 初始化加密货币监控系统...")
        
        # 初始化核心组件
        self._initialize_core_components(config_path)
        
        # 初始化服务层
        self._initialize_services()
        
        # 设置服务间的协调关系
        self._setup_service_coordination()
        
        print("🎉 系统初始化完成！")
    
    def _initialize_core_components(self, config_path: Optional[str]):
        """初始化核心组件"""
        # 配置管理
        self.config_manager = ConfigManager(config_path)
        self.settings = self.config_manager.load_config()
        print(f"✅ 配置加载完成: {self.settings.system.name} v{self.settings.system.version}")
        
        # 数据库管理
        self.db_manager = DatabaseManager(self.settings)
        print("✅ 数据库初始化完成")
        
        # 技术指标计算器
        self.indicator_calculator = IndicatorCalculator(self.settings)
        print("✅ 技术指标计算器初始化完成")
        
        # LLM客户端
        self.llm_clients = self._initialize_llm_clients()
        
        # 交易管理器
        self.portfolio_manager = PortfolioManager(self.settings, self.db_manager, self.llm_clients)
        print("✅ 交易管理器初始化完成")
        
        # Telegram集成
        self.telegram_integration = TelegramIntegration(self.settings)
        print("✅ Telegram集成初始化完成")
    
    def _initialize_services(self):
        """初始化服务层"""
        # 数据服务
        self.data_service = DataService(self.settings, self.db_manager)
        print("✅ 数据服务初始化完成")
        
        # 分析服务
        self.analysis_service = AnalysisService(
            self.settings, self.db_manager, self.data_service.data_collector, self.llm_clients
        )
        print("✅ 分析服务初始化完成")
        
        # 格式化服务
        self.formatting_service = FormattingService(self.settings)
        print("✅ 格式化服务初始化完成")
        
        # 智能主脑（需要访问Controller来调用其他功能）
        self.master_brain = MasterBrain(self)
        print("✅ 智能主脑初始化完成")
        
        # 监控服务（需要主脑实例）
        self.monitoring_service = MonitoringService(
            self.settings, self.db_manager, self.data_service, 
            self.indicator_calculator, self.master_brain
        )
        print("✅ 监控服务初始化完成")
    
    def _setup_service_coordination(self):
        """设置服务间的协调关系"""
        # 设置监控服务的分析触发回调
        self.monitoring_service.set_analysis_callback(self._on_analysis_triggered)
    
    def _on_analysis_triggered(self, symbol: str, reason: str, market_conditions: Dict[str, Any]):
        """
        当监控服务触发分析时的回调处理
        
        Args:
            symbol: 币种符号
            reason: 触发原因
            market_conditions: 市场条件
        """
        # 这里可以添加额外的分析触发逻辑，比如发送通知等
        print(f"📊 分析已触发: {symbol} - {reason}")
    
    def _load_environment_variables(self):
        """加载环境变量"""
        try:
            import os
            from pathlib import Path
            
            # 查找.env文件
            env_paths = [
                Path(__file__).parent / ".env",
                Path(__file__).parent.parent / ".env",
                Path(__file__).parent.parent.parent / ".env"
            ]
            
            for env_path in env_paths:
                if env_path.exists():
                    print(f"Loading environment from: {env_path}")
                    
                    # 简单的.env文件解析
                    with open(env_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('\"\'')
                                os.environ[key] = value
                    return
            
            print("Warning: No .env file found")
                
        except Exception as e:
            print(f"Warning: Failed to load environment variables: {e}")
    
    def _initialize_llm_clients(self) -> Dict[str, Any]:
        """初始化LLM客户端"""
        clients = {}
        
        try:
            # 导入LLM客户端
            try:
                from .llm_client import create_claude_client, create_doubao_client
            except ImportError:
                try:
                    from llm_client import create_claude_client, create_doubao_client
                except ImportError:
                    try:
                        # 最后尝试从项目目录导入
                        from crypto_monitor_project.llm_client import create_claude_client, create_doubao_client
                    except ImportError:
                        print("⚠️ LLM客户端导入失败，部分功能可能不可用")
                        return {}
            
            import os
            
            # 初始化豆包客户端
            doubao_key = os.getenv('DOUBAO_API_KEY')
            if doubao_key and create_doubao_client:
                clients['doubao'] = create_doubao_client(doubao_key)
                print("✅ 豆包客户端初始化完成")
            else:
                print("⚠️ 未配置DOUBAO_API_KEY，豆包客户端不可用")
            
            # 初始化Claude客户端
            claude_key = os.getenv('CLAUDE_API_KEY')
            if claude_key and create_claude_client:
                clients['claude'] = create_claude_client(claude_key)
                print("✅ Claude客户端初始化完成")
            else:
                print("⚠️ 未配置CLAUDE_API_KEY，Claude客户端不可用")
            
            return clients
            
        except Exception as e:
            print(f"⚠️ LLM客户端初始化失败: {e}")
            return {}
    
    def _get_llm_client_for_analyst(self, analyst_name: str):
        """为分析师获取对应的LLM客户端"""
        config_map = {
            '技术分析师': self.settings.api.technical_analyst,
            '市场分析师': self.settings.api.market_analyst,
            '基本面分析师': self.settings.api.fundamental_analyst,
            '宏观分析师': self.settings.api.macro_analyst,
            '首席分析师': self.settings.api.chief_analyst,
            '研究部门总监': self.settings.api.research_director
        }
        
        config = config_map.get(analyst_name)
        if not config:
            return self.llm_clients.get('doubao')
        
        return self.llm_clients.get(config.provider, self.llm_clients.get('doubao'))
    
    # ============= 监控系统控制接口 =============
    
    def start_monitoring(self):
        """启动监控系统"""
        success = self.monitoring_service.start_monitoring()
        if success:
            self._start_telegram_bot()
    
    def stop_monitoring(self):
        """停止监控系统"""
        self.monitoring_service.stop_monitoring()
        # 注释掉自动停止Telegram机器人，让其保持运行
        # self._stop_telegram_bot()
    
    def stop_telegram_bot_only(self):
        """仅停止Telegram机器人（监控系统继续运行）"""
        self._stop_telegram_bot()
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """获取监控状态"""
        return self.monitoring_service.get_monitoring_status()
    
    # ============= 分析接口 =============
    
    def ask_claude_with_data(self, question: str, symbols=None) -> str:
        """
        多分析师协作分析
        
        Args:
            question: 分析问题
            symbols: 要分析的币种列表
            
        Returns:
            str: 分析结果
        """
        if symbols is None:
            symbols = self.settings.monitor.primary_symbols
        elif isinstance(symbols, str):
            symbols = [symbols]
        
        print(f"🏛️ 启动多分析师协作分析")
        print(f"📊 分析币种: {', '.join([s.replace('USDT', '') for s in symbols])}")
        print("="*80)
        
        # 使用分析服务进行全面分析
        analysis_results = self.analysis_service.conduct_comprehensive_analysis(symbols)
        
        # 生成研究摘要
        research_summary = self.analysis_service.generate_research_summary(
            analysis_results['symbol_analyses'],
            analysis_results['macro_analysis'],
            analysis_results['sentiment_analysis']
        )
        
        # 将研究摘要添加到分析结果中
        analysis_results['research_summary'] = research_summary
        
        # 进行交易分析
        trading_analysis = self.portfolio_manager.conduct_trading_analysis(analysis_results, question)
        
        # 组合最终输出
        final_output = f"{research_summary}\n\n{'-'*80}\n\n{trading_analysis}"
        
        print("\n" + "="*80)
        return final_output
    
    def manual_analysis(self, symbol: str) -> str:
        """
        手动触发分析
        
        Args:
            symbol: 币种符号
            
        Returns:
            str: 分析结果消息
        """
        try:
            # 标准化symbol格式
            normalized_symbol = self.data_service.normalize_symbol(symbol)
            
            # 验证币种
            if not self.data_service.validate_symbol(symbol):
                available_symbols = self.data_service.get_available_symbols()
                return f"❌ {symbol} 不在监控列表中，可用币种: {', '.join(available_symbols)}"
            
            # 使用监控服务强制触发分析
            success = self.monitoring_service.force_analysis(normalized_symbol, "手动触发分析")
            
            if success:
                return f"✅ {normalized_symbol.replace('USDT', '')} 手动分析完成"
            else:
                return f"❌ 手动分析失败"
            
        except Exception as e:
            return f"❌ 手动分析失败: {e}"
    
    def analyze_kline_data(self, symbol: str) -> str:
        """
        技术分析K线数据
        
        Args:
            symbol: 币种符号
            
        Returns:
            str: 技术分析结果
        """
        try:
            normalized_symbol = self.data_service.normalize_symbol(symbol)
            return self.analysis_service.technical_analyst.analyze_crypto_technical(normalized_symbol)
        except Exception as e:
            return f"❌ 技术分析失败: {e}"
    
    def analyze_market_sentiment(self) -> str:
        """
        市场情绪分析
        
        Returns:
            str: 市场情绪分析结果
        """
        try:
            # 获取市场数据
            global_data = self.data_service.collect_global_market_data() or {}
            trending_data = self.data_service.collect_trending_data() or []
            
            return self.analysis_service.market_analyst.analyze_market_sentiment(global_data, trending_data)
        except Exception as e:
            return f"❌ 市场情绪分析失败: {e}"
    
    # ============= 配置管理接口 =============
    
    def set_monitoring_symbols(self, primary_symbols: List[str], secondary_symbols: List[str] = None) -> str:
        """设置动态监控币种列表"""
        try:
            if secondary_symbols is None:
                secondary_symbols = []
            
            # 验证币种格式
            all_symbols = primary_symbols + secondary_symbols
            for symbol in all_symbols:
                if not isinstance(symbol, str) or not symbol.endswith('USDT'):
                    return f"❌ 币种格式错误: {symbol}，应为BTCUSDT格式"
            
            # 更新配置
            self.settings.monitor.primary_symbols = primary_symbols
            self.settings.monitor.secondary_symbols = secondary_symbols
            
            # 保存配置更改
            self.config_manager.save_dynamic_config({
                'monitor': {
                    'primary_symbols': primary_symbols,
                    'secondary_symbols': secondary_symbols
                }
            })
            
            primary_display = [s.replace('USDT', '') for s in primary_symbols]
            secondary_display = [s.replace('USDT', '') for s in secondary_symbols] if secondary_symbols else []
            
            return f"✅ 监控币种已更新\n主要币种: {', '.join(primary_display)}\n次要币种: {', '.join(secondary_display) if secondary_display else '无'}"
            
        except Exception as e:
            return f"❌ 设置监控币种失败: {e}"
    
    def get_monitoring_symbols(self) -> Dict[str, List[str]]:
        """获取当前监控币种列表"""
        return {
            'primary_symbols': self.settings.monitor.primary_symbols or [],
            'secondary_symbols': self.settings.monitor.secondary_symbols or [],
            'total_count': len((self.settings.monitor.primary_symbols or []) + (self.settings.monitor.secondary_symbols or []))
        }
    
    def set_heartbeat_interval(self, interval_seconds: float) -> str:
        """设置心跳监控间隔时间"""
        try:
            if interval_seconds < 60:
                return "❌ 心跳间隔不能少于60秒"
            if interval_seconds > 3600:
                return "❌ 心跳间隔不能超过1小时"
            
            # 更新配置
            self.settings.triggers.normal_interval = int(interval_seconds)
            
            # 保存配置更改
            self.config_manager.save_dynamic_config({
                'triggers': {
                    'normal_interval': int(interval_seconds)
                }
            })
            
            minutes = interval_seconds / 60
            return f"✅ 心跳间隔已设置为 {interval_seconds} 秒 ({minutes:.1f} 分钟)"
            
        except Exception as e:
            return f"❌ 设置心跳间隔失败: {e}"
    
    def get_heartbeat_settings(self) -> Dict[str, Any]:
        """获取当前心跳设置"""
        return {
            'normal_interval': self.settings.triggers.normal_interval,
            'fetch_interval': self.settings.kline.fetch_interval,
            'special_conditions_enabled': True,
            'next_heartbeat_estimate': f"{self.settings.triggers.normal_interval}秒后"
        }
    
    # ============= 交易接口 =============
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取交易账户信息"""
        return self.portfolio_manager.get_account_info()
    
    def execute_trade(self, symbol: str, side: str, quantity: float, 
                     order_type: str = "MARKET", price: Optional[float] = None) -> Dict[str, Any]:
        """执行交易"""
        return self.portfolio_manager.execute_trade(symbol, side, quantity, order_type, price)
    
    # ============= 系统状态接口 =============
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            db_stats = self.db_manager.get_database_stats()
            cache_stats = self.data_service.get_cache_stats()
            monitoring_status = self.monitoring_service.get_monitoring_status()
            
            return {
                'config': {
                    'name': self.settings.system.name,
                    'version': self.settings.system.version,
                    'mode': self.settings.system.mode
                },
                'database': db_stats,
                'cache': cache_stats,
                'monitoring': monitoring_status,
                'llm_clients': list(self.llm_clients.keys()),
                'trading': self.portfolio_manager.get_account_info(),
                'telegram': self.telegram_integration.get_status()
            }
            
        except Exception as e:
            return {'error': f"获取系统状态失败: {e}"}
    
    # ============= Telegram集成 =============
    
    def _start_telegram_bot(self):
        """启动Telegram机器人"""
        try:
            self.telegram_integration.start_telegram_bot(self)
        except Exception as e:
            print(f"❌ 启动Telegram机器人失败: {e}")
    
    def _stop_telegram_bot(self):
        """停止Telegram机器人"""
        try:
            self.telegram_integration.stop_telegram_bot()
        except Exception as e:
            print(f"❌ 停止Telegram机器人失败: {e}")
            
    # ============= 智能主脑接口 =============
    
    def process_user_message(self, message: str, source: str = "direct") -> str:
        """
        处理用户消息 - 智能主脑接口
        
        Args:
            message: 用户消息
            source: 消息来源
            
        Returns:
            str: 主脑的智能响应
        """
        try:
            print(f"🧠 主脑开始处理用户消息: {message}")
            context = {
                'source': source,
                'message_type': 'user_request'
            }
            response = self.master_brain.process_request(message, context)
            print(f"🧠 主脑处理完成，响应长度: {len(response)} 字符")
            return response
        except Exception as e:
            error_msg = f"❌ 处理用户消息失败: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return error_msg

def main():
    """主函数 - 用于直接运行智能交易主脑系统"""
    import time
    import os
    from pathlib import Path
    
    print("智能交易主脑系统 v2.0")
    print("=" * 50)
    
    try:
        # 获取正确的配置文件路径
        current_dir = Path(__file__).parent
        config_path = current_dir / "config" / "crypto_monitor_config.yaml"
        
        print(f"配置文件路径: {config_path}")
        if not config_path.exists():
            print(f"错误: 配置文件不存在 {config_path}")
            return
        
        # 初始化系统
        controller = CryptoMonitorController(str(config_path))
        
        print("系统启动成功！可用功能：")
        print("1. 启动心跳监控 - 主脑自主决策")
        print("2. 直接与主脑对话")
        print("3. Telegram智能交互（如果已配置）")
        
        print("系统初始化完成！")
        print("🤖 启动智能监控和 Telegram 机器人...")
        print("📱 用户可通过 Telegram 直接与主脑对话")
        print("启动心跳监控...")
        
        # 启动心跳监控
        controller.start_monitoring()
        
        # 持续运行，不自动停止
        print("系统已启动，持续监控中...")
        print("如需停止，请按 Ctrl+C")
        
        try:
            # 持续运行，直到手动中断
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            print("\n收到停止信号，但保持 Telegram 机器人运行...")
            controller.stop_monitoring()  # 只停止监控，不停止机器人
            print("监控已停止，但 Telegram 机器人仍在运行")
        
    except Exception as e:
        print(f"系统启动失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()