 # -*- coding: utf-8 -*-
"""
加密货币监控系统主控制器 - 完整版本
直接集成所有分析功能，移除不必要的"华尔街引擎"概念
"""

import time
import threading
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime

# 导入处理 - 支持直接运行和模块导入
try:
    # 作为模块导入时使用相对导入
    from .config import ConfigManager, Settings
    from .database import DatabaseManager, MarketData, AnalysisRecord, TriggerEvent
    from .data import DataCollector
    from .core import IndicatorCalculator, MasterBrain
    from .analysis import PromptManager
    from .trading import PortfolioManager
    from .integrations import TelegramIntegration
except ImportError:
    # 直接运行时使用绝对导入
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    
    from crypto_monitor_project.config import ConfigManager, Settings
    from crypto_monitor_project.database import DatabaseManager, MarketData, AnalysisRecord, TriggerEvent
    from crypto_monitor_project.data import DataCollector
    from crypto_monitor_project.core import IndicatorCalculator, MasterBrain
    from crypto_monitor_project.analysis import PromptManager
    from crypto_monitor_project.trading import PortfolioManager
    from crypto_monitor_project.integrations import TelegramIntegration

# 导入LLM客户端
try:
    # 首先尝试从当前目录导入
    from .llm_client import create_claude_client, create_doubao_client
except ImportError:
    try:
        # 如果相对导入失败，尝试直接导入
        from llm_client import create_claude_client, create_doubao_client
    except ImportError:
        try:
            # 最后尝试从上级目录导入
            import sys
            sys.path.append('..')
            from llm_client import create_claude_client, create_doubao_client
        except ImportError:
            print("⚠️ LLM客户端导入失败，部分功能可能不可用")
            create_claude_client = None
            create_doubao_client = None


class CryptoMonitorController:
    """加密货币监控系统控制器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化监控系统控制器"""
        # 加载环境变量
        self._load_environment_variables()
        
        try:
            print("🚀 初始化加密货币监控系统...")
        except UnicodeEncodeError:
            print("Initializing cryptocurrency monitoring system...")
        
        # 加载配置
        self.config_manager = ConfigManager(config_path)
        self.settings = self.config_manager.load_config()
        try:
            print(f"✅ 配置加载完成: {self.settings.system.name} v{self.settings.system.version}")
        except UnicodeEncodeError:
            print(f"Configuration loaded: {self.settings.system.name} v{self.settings.system.version}")
        
        # 初始化数据库
        self.db_manager = DatabaseManager(self.settings)
        try:
            print("✅ 数据库初始化完成")
        except UnicodeEncodeError:
            print("Database initialized")
        
        # 初始化数据收集器
        self.data_collector = DataCollector(self.settings, self.db_manager)
        try:
            print("✅ 数据收集器初始化完成")
        except UnicodeEncodeError:
            print("Data collector initialized")
        
        # 初始化技术指标计算器
        self.indicator_calculator = IndicatorCalculator(self.settings)
        try:
            print("✅ 技术指标计算器初始化完成")
        except UnicodeEncodeError:
            print("Technical indicator calculator initialized")
        
        # 初始化LLM客户端
        self.llm_clients = self._initialize_llm_clients()
        
        # 初始化prompt管理器
        self.prompt_manager = PromptManager()
        
        # 初始化交易管理器
        self.portfolio_manager = PortfolioManager(self.settings, self.db_manager, self.llm_clients)
        try:
            print("✅ 交易管理器初始化完成")
        except UnicodeEncodeError:
            print("Trading manager initialized")
        
        # 初始化Telegram集成
        self.telegram_integration = TelegramIntegration(self.settings)
        try:
            print("✅ Telegram集成初始化完成")
        except UnicodeEncodeError:
            print("Telegram integration initialized")
        
        # 初始化智能主脑（放在最后，因为需要访问所有其他组件）
        self.master_brain = MasterBrain(self)
        try:
            print("✅ 智能主脑初始化完成")
        except UnicodeEncodeError:
            print("Master Brain initialized")
        
        try:
            print("✅ 分析系统初始化完成")
        except UnicodeEncodeError:
            print("Analysis system initialized")
        
        # 运行状态
        self.is_running = False
        self.monitoring_thread = None
        
        try:
            print("🎉 系统初始化完成！")
        except UnicodeEncodeError:
            print("System initialization completed!")
    
    def _load_environment_variables(self):
        """加载环境变量"""
        try:
            from pathlib import Path
            import os
            
            # 查找.env文件
            env_paths = [
                Path(__file__).parent / ".env",  # 当前目录
                Path(__file__).parent.parent / ".env",  # 上级目录
                Path(__file__).parent.parent.parent / ".env"  # 再上级目录
            ]
            
            for env_path in env_paths:
                if env_path.exists():
                    try:
                        print(f"Loading environment from: {env_path}")
                    except UnicodeEncodeError:
                        print(f"Loading environment from: {env_path}")
                    
                    # 简单的.env文件解析
                    with open(env_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"\'')
                                os.environ[key] = value
                    
                    return
            
            try:
                print("Warning: No .env file found")
            except UnicodeEncodeError:
                print("Warning: No .env file found")
                
        except Exception as e:
            try:
                print(f"Warning: Failed to load environment variables: {e}")
            except UnicodeEncodeError:
                print(f"Warning: Failed to load environment variables: {e}")
    
    def _initialize_llm_clients(self) -> Dict[str, Any]:
        """初始化LLM客户端"""
        clients = {}
        
        try:
            if create_doubao_client:
                # 尝试从环境变量获取API密钥
                import os
                doubao_key = os.getenv('DOUBAO_API_KEY')
                if doubao_key:
                    clients['doubao'] = create_doubao_client(doubao_key)
                    try:
                        print("✅ 豆包客户端初始化完成")
                    except UnicodeEncodeError:
                        print("Doubao client initialized")
                else:
                    try:
                        print("⚠️ 未配置DOUBAO_API_KEY，豆包客户端不可用")
                    except UnicodeEncodeError:
                        print("Warning: DOUBAO_API_KEY not configured, Doubao client unavailable")
            
            if create_claude_client:
                claude_key = os.getenv('CLAUDE_API_KEY')
                if claude_key:
                    clients['claude'] = create_claude_client(claude_key)
                    try:
                        print("✅ Claude客户端初始化完成")
                    except UnicodeEncodeError:
                        print("Claude client initialized")
                else:
                    try:
                        print("⚠️ 未配置CLAUDE_API_KEY，Claude客户端不可用")
                    except UnicodeEncodeError:
                        print("Warning: CLAUDE_API_KEY not configured, Claude client unavailable")
            
            return clients
            
        except Exception as e:
            try:
                print(f"⚠️ LLM客户端初始化失败: {e}")
            except UnicodeEncodeError:
                print(f"Warning: LLM client initialization failed: {e}")
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
    
    def start_monitoring(self):
        """启动监控系统"""
        if self.is_running:
            print("⚠️ 监控系统已在运行")
            return
        
        print("🔄 启动监控系统...")
        self.is_running = True
        
        if not self._test_connections():
            print("❌ 连接测试失败，停止启动")
            self.is_running = False
            return
        
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        # 启动Telegram机器人
        self._start_telegram_bot()
        
        print("✅ 监控系统已启动")
    
    def stop_monitoring(self):
        """停止监控系统"""
        if not self.is_running:
            print("⚠️ 监控系统未在运行")
            return
        
        print("⏹️ 停止监控系统...")
        self.is_running = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        # 停止Telegram机器人
        self._stop_telegram_bot()
        
        print("✅ 监控系统已停止")
    
    def _test_connections(self) -> bool:
        """测试所有连接"""
        print("🔍 测试系统连接...")
        connection_status = self.data_collector.test_all_connections()
        
        all_connected = all(connection_status.values())
        if all_connected:
            print("✅ 所有连接测试通过")
        else:
            failed_connections = [k for k, v in connection_status.items() if not v]
            print(f"⚠️ 部分连接失败: {', '.join(failed_connections)}")
        
        return all_connected
    
    def _monitoring_loop(self):
        """主监控循环"""
        print("🔄 进入监控循环...")
        
        last_analysis_time = {}
        
        while self.is_running:
            try:
                # 动态获取当前监控币种（支持主脑实时调整）
                monitoring_info = self.get_monitoring_symbols()
                primary_symbols = monitoring_info['primary_symbols']
                secondary_symbols = monitoring_info['secondary_symbols']
                all_symbols = primary_symbols + secondary_symbols
                
                if not all_symbols:
                    print("⚠️ 当前无监控币种，等待主脑设置...")
                    time.sleep(30)  # 等待30秒后重新检查
                    continue
                    
                kline_data = self.data_collector.collect_kline_data(all_symbols)
                
                for symbol in all_symbols:
                    if not self.is_running:
                        break
                    
                    self._process_symbol(symbol, kline_data.get(symbol, []), last_analysis_time)
                
                time.sleep(self.settings.kline.fetch_interval)
                
            except Exception as e:
                print(f"❌ 监控循环异常: {e}")
                time.sleep(10)
    
    def _process_symbol(self, symbol: str, kline_data: List[Dict[str, Any]], last_analysis_time: Dict[str, float]):
        """处理单个币种 - 智能主脑决策"""
        try:
            if not kline_data:
                return
            
            indicators = self.indicator_calculator.calculate_all_indicators(kline_data)
            self._save_market_data(symbol, kline_data[-1], indicators)
            
            special_conditions = self.indicator_calculator.check_special_conditions(symbol, indicators)
            
            current_time = time.time()
            symbol_last_analysis = last_analysis_time.get(symbol, 0)
            
            # 获取当前动态心跳设置
            heartbeat_settings = self.get_heartbeat_settings()
            current_interval = heartbeat_settings['normal_interval']
            
            # 准备市场条件给主脑决策
            market_conditions = {
                'symbol': symbol,
                'latest_price': kline_data[-1]['close'],
                'indicators': indicators,
                'special_conditions': special_conditions,
                'time_since_last_analysis': current_time - symbol_last_analysis,
                'normal_interval': current_interval
            }
            
            # 判断是否需要触发主脑决策
            should_trigger_brain = False
            trigger_reason = ""
            
            if special_conditions:
                should_trigger_brain = True
                trigger_reason = f"特殊市场条件触发: {', '.join(special_conditions)}"
            elif current_time - symbol_last_analysis >= current_interval:
                should_trigger_brain = True  
                trigger_reason = f"定时心跳监控 (间隔:{current_interval}秒)"
            
            if should_trigger_brain:
                print(f"🧠 触发智能主脑决策: {symbol} - {trigger_reason}")
                
                # 让主脑进行心跳决策
                brain_response = self.master_brain.heartbeat_decision(market_conditions)
                print(f"🧠 主脑决策结果:\n{brain_response}")
                
                last_analysis_time[symbol] = current_time
            
        except Exception as e:
            print(f"❌ 处理{symbol}失败: {e}")
    
    def _save_market_data(self, symbol: str, latest_kline: Dict[str, Any], indicators: Dict[str, Any]):
        """保存市场数据"""
        try:
            rsi_value = indicators.get('rsi', {}).get('value')
            macd_data = indicators.get('macd', {})
            ma_data = indicators.get('moving_averages', {})
            
            market_data = MarketData(
                symbol=symbol,
                timestamp=latest_kline['timestamp'],
                price=latest_kline['close'],
                rsi=rsi_value,
                macd=macd_data.get('macd_line'),
                volume=latest_kline['volume'],
                ma_20=ma_data.get('ma_20'),
                ma_50=ma_data.get('ma_50'),
                ma_200=ma_data.get('ma_200')
            )
            
            self.db_manager.save_market_data(market_data)
            
        except Exception as e:
            print(f"❌ 保存{symbol}市场数据失败: {e}")
    
    def _execute_analysis(self, symbol: str, indicators: Dict[str, Any], reason: str):
        """执行完整分析流程"""
        try:
            print(f"📊 开始分析 {symbol.replace('USDT', '')} - {reason}")
            analysis_result = self.ask_claude_with_data(f"{reason} - 请分析当前{symbol}市场状况", [symbol])
            print(f"✅ 分析完成 {symbol.replace('USDT', '')}")
            
        except Exception as e:
            print(f"❌ 执行{symbol}分析失败: {e}")
    
    def ask_claude_with_data(self, question: str, symbols=None) -> str:
        """多分析师协作分析"""
        if symbols is None:
            symbols = self.settings.monitor.primary_symbols
        elif isinstance(symbols, str):
            symbols = [symbols]
            
        print(f"🏛️ 启动多分析师协作分析", flush=True)
        print(f"📊 分析币种: {', '.join([s.replace('USDT', '') for s in symbols])}", flush=True)
        print("="*80, flush=True)

        symbol_analyses = {}
        macro_analysis = None
        sentiment_analysis = None
        
        for symbol in symbols:
            analysis_result = self.conduct_independent_coin_analysis(symbol)
            symbol_analyses[symbol] = analysis_result
            
            if macro_analysis is None:
                macro_analysis = analysis_result['macro_analysis']
            if sentiment_analysis is None:
                sentiment_analysis = analysis_result['sentiment_analysis']
        
        research_summary = self.generate_research_summary(symbol_analyses, macro_analysis, sentiment_analysis)
        
        # 组织研究结果用于交易分析
        research_results = {
            'symbol_analyses': symbol_analyses,
            'macro_analysis': macro_analysis,
            'sentiment_analysis': sentiment_analysis,
            'research_summary': research_summary
        }
        
        # 进行交易分析
        trading_analysis = self.portfolio_manager.conduct_trading_analysis(research_results, question)
        
        # 组合最终输出
        final_output = f"{research_summary}\n\n{'-'*80}\n\n{trading_analysis}"
        
        print("\n" + "="*80, flush=True)
        return final_output
    
    def conduct_independent_coin_analysis(self, symbol: str) -> Dict[str, Any]:
        """独立币种分析"""
        newly_generated = set()
        
        print(f"🏛️ 启动币种分析: {symbol}")
        print("="*80)
        
        # 1. 宏观分析
        print("🌍 [宏观分析师] 分析全球市场环境...")
        macro_analysis = self.get_today_analysis('macro_analysis', '宏观分析师')
        if macro_analysis is None:
            print("🔄 生成新的宏观分析...")
            macro_analysis = self.analyze_macro_data()
            newly_generated.add('macro_analysis')
            self._save_analysis_record('宏观分析师', None, macro_analysis, '宏观数据分析')
        
        # 2. 市场情绪分析
        print("🔥 [市场分析师] 分析市场情绪...")
        sentiment_analysis = self.get_today_analysis('market_sentiment', '市场分析师')
        if sentiment_analysis is None:
            print("🔄 生成新的市场情绪分析...")
            sentiment_analysis = self.analyze_market_sentiment()
            newly_generated.add('market_sentiment')
            self._save_analysis_record('市场分析师', None, sentiment_analysis, '市场情绪分析')
        
        # 3. 技术分析
        print(f"📈 [技术分析师] 分析 {symbol}...")
        technical_analysis = self.analyze_kline_data(symbol)
        self._save_analysis_record('技术分析师', symbol, technical_analysis, f'{symbol}技术分析')
        newly_generated.add(f'technical_analysis_{symbol}')
        
        # 4. 基本面分析
        print(f"📊 [基本面分析师] 分析 {symbol}...")
        fundamental_analysis = self.get_today_analysis(f'fundamental_analysis_{symbol}', '基本面分析师')
        if fundamental_analysis is None:
            print(f"🔄 生成新的{symbol}基本面分析...")
            fundamental_analysis = self.analyze_fundamental_data(symbol)
            newly_generated.add(f'fundamental_analysis_{symbol}')
            self._save_analysis_record('基本面分析师', symbol, fundamental_analysis, f'{symbol}基本面分析')
        
        # 5. 首席分析师整合
        print(f"🎯 [{symbol}首席分析师] 整合分析...")
        dependencies_updated = any(dep in newly_generated for dep in [
            'macro_analysis', 'market_sentiment', 
            f'technical_analysis_{symbol}', f'fundamental_analysis_{symbol}'
        ])
        
        coin_chief_analysis = self.get_today_analysis(f'coin_chief_analysis_{symbol}', f'{symbol}首席分析师')
        if coin_chief_analysis is None or dependencies_updated:
            coin_chief_analysis = self.generate_coin_chief_analysis(
                symbol, technical_analysis, sentiment_analysis, fundamental_analysis, macro_analysis
            )
        
        return {
            'symbol': symbol,
            'macro_analysis': macro_analysis,
            'sentiment_analysis': sentiment_analysis, 
            'technical_analysis': technical_analysis,
            'fundamental_analysis': fundamental_analysis,
            'chief_analysis': coin_chief_analysis,
        }
    
    def analyze_kline_data(self, symbol: str) -> str:
        """技术分析 - 分离系统提示词与实时数据"""
        # 1. 获取系统提示词
        system_prompt = self.prompt_manager.get_technical_analysis_prompt()
        
        # 2. 收集K线数据
        kline_data = self.data_collector.collect_kline_data([symbol]).get(symbol, [])
        if not kline_data:
            raise Exception(f"无法获取{symbol}的K线数据")

        # 3. 计算技术指标
        df = pd.DataFrame(kline_data)
        if len(df) < 50:
            raise Exception(f"数据不足，仅有{len(df)}条数据")

        closes = df['close'].astype(float)
        df['sma_20'] = closes.rolling(window=20).mean()
        df['sma_50'] = closes.rolling(window=50).mean()
        df['rsi'] = self._calculate_rsi(closes)
        df['macd'], df['macd_signal'] = self._calculate_macd(closes)

        # 4. 构建用户消息
        recent_data = df.dropna().tail(10)
        user_message = self._format_technical_data_message(recent_data, symbol)
        
        # 5. 调用LLM（分离模式）
        llm_client = self._get_llm_client_for_analyst('技术分析师')
        return llm_client.call(system_prompt, user_message=user_message, agent_name='技术分析师')
    
    def analyze_market_sentiment(self) -> str:
        """市场情绪分析 - 分离系统提示词与实时数据"""
        # 1. 获取系统提示词
        system_prompt = self.prompt_manager.get_market_sentiment_prompt()
        
        # 2. 收集市场数据
        global_data = self.data_collector.collect_global_market_data()
        trending_data = self.data_collector.collect_trending_data()
        
        # 3. 构建用户消息
        user_message = self._format_market_sentiment_message(global_data, trending_data)
        
        # 4. 调用LLM（分离模式）
        llm_client = self._get_llm_client_for_analyst('市场分析师')
        return llm_client.call(system_prompt, user_message=user_message, agent_name='市场分析师')
    
    def analyze_fundamental_data(self, symbol: str) -> str:
        """基本面分析 - 分离系统提示词与实时数据"""
        # 1. 获取系统提示词
        system_prompt = self.prompt_manager.get_fundamental_analysis_prompt()
        
        # 2. 构建用户消息
        user_message = self._build_fundamental_market_data(symbol)
        
        # 3. 调用LLM（分离模式）
        llm_client = self._get_llm_client_for_analyst('基本面分析师')
        return llm_client.call(system_prompt, user_message=user_message, agent_name='基本面分析师')
    
    def analyze_macro_data(self) -> str:
        """宏观分析 - 分离系统提示词与实时数据"""
        # 1. 获取纯净的系统提示词
        system_prompt = self.prompt_manager.get_macro_analysis_prompt()
        
        # 2. 收集宏观数据
        macro_data = self._collect_macro_data()
        
        # 3. 构建用户消息
        user_message = self._format_macro_data_message(macro_data)
        
        # 4. 调用LLM（分离模式）
        llm_client = self._get_llm_client_for_analyst('宏观分析师')
        return llm_client.call(system_prompt, user_message=user_message, agent_name='宏观分析师')
    
    def generate_coin_chief_analysis(self, symbol: str, technical_analysis: str, 
                                   sentiment_analysis: str, fundamental_analysis: str, 
                                   macro_analysis: str) -> str:
        """首席分析师综合分析 - 分离系统提示词与实时数据"""
        # 1. 获取系统提示词
        system_prompt = self.prompt_manager.get_chief_analysis_prompt()
        
        # 2. 构建用户消息
        user_message = self._format_chief_analysis_message(
            symbol, technical_analysis, sentiment_analysis, fundamental_analysis, macro_analysis
        )
        
        # 3. 调用LLM（分离模式）
        llm_client = self._get_llm_client_for_analyst('首席分析师')
        response = llm_client.call(system_prompt, user_message=user_message, agent_name='首席分析师')
        
        self._save_analysis_record(f'{symbol}首席分析师', symbol, response, f'{symbol}首席分析')
        return response
    
    def generate_research_summary(self, symbol_analyses: Dict[str, Any], 
                                macro_analysis: str, sentiment_analysis: str) -> str:
        """研究综合报告"""
        prompt_file = self.prompt_manager.prompts_dir / "research_summary.txt"
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt_template = f.read().strip()
        
        analysis_reports = self._format_symbol_analyses(symbol_analyses)
        prompt = prompt_template.format(
            symbol_reports=analysis_reports, macro_analysis=macro_analysis,
            sentiment_analysis=sentiment_analysis
        )
        
        llm_client = self._get_llm_client_for_analyst('研究部门总监')
        return llm_client.call(prompt, agent_name='研究部门总监')
    
    def _collect_macro_data(self) -> Dict[str, Any]:
        """收集宏观经济数据 - 集成ETF、美股、黄金数据"""
        try:
            # 使用新的完整宏观数据收集器
            comprehensive_macro = self.data_collector.collect_comprehensive_macro_data()
            
            if comprehensive_macro:
                # 添加加密货币全局数据
                global_data = self.data_collector.collect_global_market_data()
                if global_data:
                    comprehensive_macro['crypto_global'] = global_data
                
                return comprehensive_macro
            else:
                print("⚠️ 宏观数据收集失败，使用备用数据结构")
                return self._get_fallback_macro_data()
            
        except Exception as e:
            print(f"❌ 收集宏观数据失败: {e}")
            import traceback
            error_detail = traceback.format_exc()
            print(f"详细错误: {error_detail}")
            return self._get_fallback_macro_data(error=str(e))
    
    def _get_fallback_macro_data(self, error: str = None) -> Dict[str, Any]:
        """宏观数据收集失败时的备用数据结构"""
        fallback_data = {
            'timestamp': datetime.now().isoformat(),
            'data_completeness': {
                'etf_available': False,
                'stocks_available': False,
                'gold_available': False
            },
            'bitcoin_etf_flows': None,
            'us_stock_indices': None,
            'gold_price': None
        }
        
        if error:
            fallback_data['error'] = error
        
        # 尝试至少获取加密货币全局数据
        try:
            global_data = self.data_collector.collect_global_market_data()
            if global_data:
                fallback_data['crypto_global'] = global_data
                fallback_data['data_completeness']['crypto_global_available'] = True
        except Exception:
            fallback_data['data_completeness']['crypto_global_available'] = False
        
        return fallback_data
    
    def _format_macro_data_message(self, macro_data: Dict[str, Any]) -> str:
        """格式化宏观数据为用户消息 - 支持完整数据结构"""
        if 'error' in macro_data:
            return f"⚠️ 宏观数据收集遇到问题: {macro_data['error']}\n\n请基于一般宏观经济环境分析加密货币市场。"
        
        message_parts = ["请基于以下多维度宏观经济数据分析对加密货币市场的影响：\n"]
        
        # 数据完整性报告
        completeness = macro_data.get('data_completeness', {})
        available_sources = [k for k, v in completeness.items() if v]
        message_parts.append(f"=== 数据源状态 ===")
        message_parts.append(f"可用数据源: {len(available_sources)}/{len(completeness)} 个")
        message_parts.append("")
        
        # Bitcoin ETF资金流向数据
        message_parts.append("=== 比特币ETF资金流向 ===")
        etf_data = macro_data.get('bitcoin_etf_flows')
        if etf_data and completeness.get('etf_available'):
            message_parts.append(f"数据源: {etf_data.get('source', 'Unknown')}")
            message_parts.append(f"当日流向估算: ${etf_data.get('net_inflow_today', 0):,.1f}百万")
            message_parts.append(f"总管理规模: ${etf_data.get('total_aum_estimate', 0):,.0f}万")
            message_parts.append(f"注意: {etf_data.get('note', '数据来源说明')}")
            
            # 显示主要ETF表现（实际数据）
            etf_details = etf_data.get('etf_details', [])
            if etf_details:
                message_parts.append("主要ETF当日表现:")
                for etf in etf_details[:5]:  # 显示前5只
                    symbol = etf.get('symbol', 'N/A')
                    price = etf.get('current_price', 0)
                    change_pct = etf.get('price_change_24h', 0)
                    volume = etf.get('volume_24h', 0)
                    message_parts.append(f"  - {symbol}: ${price:.2f} ({change_pct:+.2f}%) 成交量:{volume:,}")
        else:
            message_parts.append("❌ ETF数据暂时不可用")
            message_parts.append("影响: 无法评估机构资金配置态度及规模变化")
        message_parts.append("")
        
        # 美股主要指数表现
        message_parts.append("=== 美股主要指数表现 ===")
        stock_data = macro_data.get('us_stock_indices')
        if stock_data and completeness.get('stocks_available'):
            message_parts.append(f"数据源: {stock_data.get('source', 'Unknown')}")
            indices = stock_data.get('indices', {})
            
            for idx_code, idx_data in indices.items():
                name = idx_data.get('name', idx_code)
                price = idx_data.get('current_price', 0)
                change_pct = idx_data.get('change_percent', 0)
                message_parts.append(f"{name}: {price:,.2f} ({change_pct:+.2f}%)")
            
            # VIX恐慌指数
            vix_data = stock_data.get('vix', {})
            if vix_data:
                vix_current = vix_data.get('current', 0)
                vix_change = vix_data.get('change', 0)
                message_parts.append(f"VIX恐慌指数: {vix_current:.2f} ({vix_change:+.2f})")
            
            market_sentiment = stock_data.get('market_sentiment', 'unknown')
            message_parts.append(f"市场情绪: {market_sentiment}")
        else:
            message_parts.append("❌ 美股数据暂时不可用")
            message_parts.append("影响: 无法判断加密市场与股票市场的相关性程度")
        message_parts.append("")
        
        # 黄金价格数据
        message_parts.append("=== 黄金价格数据 ===")
        gold_data = macro_data.get('gold_price')
        if gold_data and completeness.get('gold_available'):
            message_parts.append(f"数据源: {gold_data.get('source', 'Unknown')}")
            current_price = gold_data.get('current_price', 0)
            change_24h = gold_data.get('change_24h', 0)
            change_pct = gold_data.get('change_percent', 0)
            message_parts.append(f"现货价格: ${current_price:.2f}/盎司")
            message_parts.append(f"24H变化: ${change_24h:+.2f} ({change_pct:+.2f}%)")
            message_parts.append(f"24H区间: ${gold_data.get('low_24h', 0):.2f} - ${gold_data.get('high_24h', 0):.2f}")
            
            # 技术指标
            tech_indicators = gold_data.get('technical_indicators', {})
            if tech_indicators:
                rsi = tech_indicators.get('rsi_14', 0)
                trend = tech_indicators.get('trend', 'unknown')
                message_parts.append(f"RSI(14): {rsi:.1f}")
                message_parts.append(f"技术趋势: {trend}")
        else:
            message_parts.append("❌ 黄金价格数据暂时不可用")
            message_parts.append("影响: 无法分析加密货币作为通胀对冲工具的当前市场定位")
        message_parts.append("")
        
        # 加密货币全球市场数据
        if 'crypto_global' in macro_data:
            message_parts.append("=== 加密货币全球市场数据 ===")
            global_data = macro_data['crypto_global']
            message_parts.append(f"总市值: ${global_data.get('total_market_cap_usd', 0):,.0f}")
            message_parts.append(f"24H成交量: ${global_data.get('total_volume_24h_usd', 0):,.0f}")  
            message_parts.append(f"24H市值变化: {global_data.get('market_cap_change_percentage_24h_usd', 0):.2f}%")
            message_parts.append(f"活跃加密货币: {global_data.get('active_cryptocurrencies', 0)}")
            message_parts.append("")
        
        # 分析指导
        message_parts.append("=== 分析要点 ===")
        message_parts.append("请重点关注：")
        message_parts.append("1. ETF资金流向与比特币价格走势的相关性")
        message_parts.append("2. 美股市场波动对加密市场的传导效应") 
        message_parts.append("3. 黄金与比特币在避险需求中的竞争关系")
        message_parts.append("4. 宏观流动性环境对整体风险资产的影响")
        
        return "\n".join(message_parts)
    
    def _format_technical_data_message(self, data_df: pd.DataFrame, symbol: str) -> str:
        """格式化技术分析数据为用户消息"""
        message_parts = [
            f"请分析{symbol}的{self.settings.kline.default_period}K线数据：\n",
            "最近10个周期的技术指标数据：",
            "时间戳(time)、开盘价(open)、最高价(high)、最低价(low)、收盘价(close)、成交量(volume)",
            "20期简单移动平均线(sma_20)、50期简单移动平均线(sma_50)",
            "相对强弱指数RSI(rsi)、MACD线(macd)、MACD信号线(macd_signal)\n"
        ]
        
        # 添加具体的数据行
        for _, row in data_df.iterrows():
            line = (f"时间:{row['timestamp']} | "
                   f"开盘:{row['open']:.4f} | "
                   f"最高:{row['high']:.4f} | "
                   f"最低:{row['low']:.4f} | "
                   f"收盘:{row['close']:.4f} | "
                   f"成交量:{row['volume']:.0f} | "
                   f"SMA20:{row.get('sma_20', 'N/A')} | "
                   f"SMA50:{row.get('sma_50', 'N/A')} | "
                   f"RSI:{row.get('rsi', 'N/A')} | "
                   f"MACD:{row.get('macd', 'N/A')} | "
                   f"信号线:{row.get('macd_signal', 'N/A')}")
            message_parts.append(line)
            
        message_parts.append("\n请保持简洁专业，重点关注15分钟级别的短期走势。")
        return "\n".join(message_parts)
    
    def _format_market_sentiment_message(self, global_data: Dict, trending_data: Dict) -> str:
        """格式化市场情绪分析数据为用户消息"""
        message_parts = ["请基于以下多维度数据分析当前加密货币市场情绪：\n"]
        
        # 全球市场数据
        message_parts.append("=== 全球市场数据 ===")
        message_parts.append(self._format_global_data(global_data))
        message_parts.append("")
        
        # 恐贪指数数据
        message_parts.append("=== 恐贪指数 ===")
        message_parts.append("暂无恐贪指数数据")
        message_parts.append("")
        
        # 热门搜索趋势
        message_parts.append("=== 热门搜索趋势 ===")
        message_parts.append(self._format_trending_data(trending_data))
        message_parts.append("")
        
        # 主流币种表现
        message_parts.append("=== 主流币种表现 ===")
        message_parts.append(self._format_major_coins_performance())
        message_parts.append("")
        
        message_parts.append("请提供客观专业的市场情绪评估，重点关注多个指标之间的相互验证。")
        
        return "\n".join(message_parts)
    
    def _format_chief_analysis_message(self, symbol: str, technical_analysis: str, 
                                     sentiment_analysis: str, fundamental_analysis: str, 
                                     macro_analysis: str) -> str:
        """格式化首席分析师数据为用户消息"""
        message_parts = [
            f"请整合以下四个专业代理的分析报告，提供针对{symbol}的全面投资建议：\n",
            "=== 技术分析师报告 ===",
            technical_analysis,
            "\n=== 市场分析师报告 ===",
            sentiment_analysis,
            "\n=== 基本面分析师报告 ===", 
            fundamental_analysis,
            "\n=== 宏观分析师报告 ===",
            macro_analysis,
            f"\n请基于技术面、市场情绪、基本面和宏观面的综合分析，提供针对{symbol}的全面投资建议。",
            "注意平衡各方观点，给出客观专业的结论，重点关注各维度分析的一致性和分歧点。",
            f"请提供具体、可操作的{symbol}投资建议，避免空泛的表述。"
        ]
        
        return "\n".join(message_parts)
    
    def _normalize_symbol(self, symbol: str) -> str:
        """标准化交易对符号 - 支持BTC -> BTCUSDT转换"""
        symbol = symbol.upper().strip()
        
        # 如果已经是完整格式，直接返回
        if symbol.endswith('USDT'):
            return symbol
        
        # 如果是缩写格式，添加USDT后缀
        return f"{symbol}USDT"
    
    # 辅助方法
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """计算RSI"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """计算MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        return macd_line, signal_line
    
    def _format_technical_data(self, data_df: pd.DataFrame) -> str:
        """格式化技术分析数据"""
        lines = []
        for _, row in data_df.iterrows():
            line = (f"时间:{row['timestamp']} | "
                   f"开盘:{row['open']:.4f} | "
                   f"最高:{row['high']:.4f} | "
                   f"最低:{row['low']:.4f} | "
                   f"收盘:{row['close']:.4f} | "
                   f"成交量:{row['volume']:.0f} | "
                   f"SMA20:{row.get('sma_20', 'N/A')} | "
                   f"SMA50:{row.get('sma_50', 'N/A')} | "
                   f"RSI:{row.get('rsi', 'N/A')} | "
                   f"MACD:{row.get('macd', 'N/A')} | "
                   f"信号线:{row.get('macd_signal', 'N/A')}")
            lines.append(line)
        return '\n'.join(lines)
    
    def _format_global_data(self, global_data: Dict) -> str:
        """格式化全球市场数据"""
        if not global_data:
            return "暂无全球市场数据"
        
        lines = [
            f"总市值: ${global_data.get('total_market_cap_usd', 0):,.0f}",
            f"24H成交量: ${global_data.get('total_volume_24h_usd', 0):,.0f}",
            f"24H市值变化: {global_data.get('market_cap_change_percentage_24h_usd', 0):.2f}%",
            f"活跃加密货币: {global_data.get('active_cryptocurrencies', 0)}"
        ]
        return '\n'.join(lines)
    
    def _format_trending_data(self, trending_data: List) -> str:
        """格式化热门币种"""
        if not trending_data:
            return "暂无热门币种数据"
        
        names = []
        for coin in trending_data[:5]:
            name = coin.get('name', coin.get('symbol', 'Unknown'))
            names.append(name)
        return ', '.join(names)
    
    def _format_major_coins_performance(self) -> str:
        """格式化主流币种表现"""
        try:
            # 使用配置文件中的监控币种，而不是硬编码
            major_symbols = (self.settings.monitor.primary_symbols or []) + (self.settings.monitor.secondary_symbols or [])
            performances = []
            
            for symbol in major_symbols:
                price = self.data_collector.get_current_price(symbol)
                if price:
                    performances.append(f"{symbol.replace('USDT', '')}: ${price:.4f}")
            
            return '\n'.join(performances) if performances else "暂无主流币种数据"
        except Exception:
            return "获取主流币种数据失败"
    
    def _build_fundamental_market_data(self, symbol: str) -> str:
        """构建基本面市场数据"""
        try:
            current_price = self.data_collector.get_current_price(symbol)
            stats = self.data_collector.binance_client.get_24hr_stats(symbol)
            
            lines = [f"=== {symbol.replace('USDT', '')} 基本面数据 ==="]
            
            if current_price:
                lines.append(f"当前价格: ${current_price:.4f}")
            
            if stats:
                lines.extend([
                    f"24H变化: {stats.get('price_change_percent', 0):.2f}%",
                    f"24H成交量: {stats.get('volume', 0):,.0f}",
                    f"24H最高: ${stats.get('high_price', 0):.4f}",
                    f"24H最低: ${stats.get('low_price', 0):.4f}"
                ])
            
            return '\n'.join(lines)
        except Exception:
            return f"获取{symbol}基本面数据失败"
    
    def _format_symbol_analyses(self, symbol_analyses: Dict[str, Any]) -> str:
        """格式化币种分析报告"""
        lines = []
        for symbol, analysis in symbol_analyses.items():
            lines.extend([
                f"=== {symbol.replace('USDT', '')} 分析报告 ===",
                f"首席分析师: {analysis.get('chief_analysis', '暂无')}",
                ""
            ])
        return '\n'.join(lines)
    
    def get_today_analysis(self, data_type: str, agent_name: str) -> Optional[str]:
        """获取今日分析缓存"""
        try:
            records = self.db_manager.get_analysis_records(data_type=data_type, agent_name=agent_name, limit=1)
            if records:
                record = records[0]
                if record.timestamp and record.timestamp.date() == datetime.now().date():
                    return record.content
            return None
        except Exception:
            return None
    
    def _save_analysis_record(self, analyst_name: str, symbol: str, content: str, reason: str):
        """保存分析记录"""
        try:
            record = AnalysisRecord(
                data_type='analysis',
                agent_name=analyst_name,
                symbol=symbol,
                content=content,
                summary=reason,
                status='completed'
            )
            self.db_manager.save_analysis_record(record)
            
        except Exception as e:
            print(f"❌ 保存分析记录失败: {e}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            db_stats = self.db_manager.get_database_stats()
            cache_stats = self.data_collector.get_cache_stats()
            
            return {
                'running': self.is_running,
                'config': {
                    'name': self.settings.system.name,
                    'version': self.settings.system.version,
                    'mode': self.settings.system.mode
                },
                'database': db_stats,
                'cache': cache_stats,
                'llm_clients': list(self.llm_clients.keys()),
                'trading': self.portfolio_manager.get_account_info() if hasattr(self, 'portfolio_manager') else None,
                'telegram': self.telegram_integration.get_status() if hasattr(self, 'telegram_integration') else None
            }
            
        except Exception as e:
            return {'error': f"获取系统状态失败: {e}"}
    
    def manual_analysis(self, symbol: str) -> str:
        """手动触发分析"""
        try:
            # 标准化symbol格式 - 支持BTC -> BTCUSDT转换
            normalized_symbol = self._normalize_symbol(symbol)
            all_symbols = (self.settings.monitor.primary_symbols or []) + (self.settings.monitor.secondary_symbols or [])
            
            if normalized_symbol not in all_symbols:
                available_symbols = [s.replace('USDT', '') for s in all_symbols]
                return f"❌ {symbol} 不在监控列表中，可用币种: {', '.join(available_symbols)}"
            
            print(f"🎯 手动分析 {normalized_symbol.replace('USDT', '')}...")
            
            kline_data = self.data_collector.collect_kline_data([normalized_symbol])
            symbol_klines = kline_data.get(normalized_symbol, [])
            
            if not symbol_klines:
                return f"❌ 无法获取 {normalized_symbol} 的K线数据"
            
            analysis_result = self.ask_claude_with_data(f"手动触发分析", [normalized_symbol])
            
            return f"✅ {normalized_symbol.replace('USDT', '')} 手动分析完成"
            
        except Exception as e:
            return f"❌ 手动分析失败: {e}"
    
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
    
    def get_account_info(self) -> Dict[str, Any]:
        """获取交易账户信息"""
        return self.portfolio_manager.get_account_info()
    
    def execute_trade(self, symbol: str, side: str, quantity: float, 
                     order_type: str = "MARKET", price: Optional[float] = None) -> Dict[str, Any]:
        """执行交易"""
        return self.portfolio_manager.execute_trade(symbol, side, quantity, order_type, price)
    
    def set_monitoring_symbols(self, primary_symbols: List[str], secondary_symbols: List[str] = None) -> str:
        """
        设置动态监控币种列表
        
        Args:
            primary_symbols: 主要监控币种列表
            secondary_symbols: 次要监控币种列表
            
        Returns:
            设置结果消息
        """
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
            
            # 保存配置更改（如果需要持久化）
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
        """
        设置心跳监控间隔时间
        
        Args:
            interval_seconds: 心跳间隔秒数
            
        Returns:
            设置结果消息
        """
        try:
            if interval_seconds < 60:
                return "❌ 心跳间隔不能少于60秒"
            if interval_seconds > 3600:
                return "❌ 心跳间隔不能超过1小时"
            
            # 更新配置
            self.settings.triggers.normal_interval = int(interval_seconds)
            
            # 保存配置更改（如果需要持久化）
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
    
    def process_user_message(self, message: str, source: str = "direct") -> str:
        """
        处理用户消息 - 智能主脑接口
        
        Args:
            message: 用户消息
            source: 消息来源 (telegram, direct, etc.)
            
        Returns:
            主脑的智能响应
        """
        try:
            context = {
                'source': source,
                'message_type': 'user_request'
            }
            return self.master_brain.process_request(message, context)
        except Exception as e:
            return f"❌ 处理用户消息失败: {e}"


def main():
    """主函数 - 用于直接运行智能交易主脑系统"""
    import time
    import os
    from pathlib import Path
    
    # 处理输出编码问题
    try:
        print("智能交易主脑系统 v2.0")
        print("=" * 50)
    except UnicodeEncodeError:
        print("Master Brain System v2.0")
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
        
        try:
            print("系统启动成功！可用功能：")
            print("1. 启动心跳监控 - 主脑自主决策")
            print("2. 直接与主脑对话")
            print("3. Telegram智能交互（如果已配置）")
        except UnicodeEncodeError:
            print("System started successfully! Available features:")
            print("1. Start heartbeat monitoring - Master Brain autonomous decisions")
            print("2. Direct chat with Master Brain") 
            print("3. Telegram intelligent interaction (if configured)")
        
        # 演示直接对话
        try:
            print("与智能主脑对话演示：")
        except UnicodeEncodeError:
            print("Master Brain dialogue demo:")
            
        test_questions = [
            "系统状态如何？",
            "当前有什么交易机会吗？", 
            "帮我分析一下BTC"
        ]
        
        for question in test_questions:
            try:
                print(f"用户: {question}")
            except UnicodeEncodeError:
                print(f"User: {question}")
                
            try:
                response = controller.process_user_message(question)
                try:
                    print(f"主脑: {response}")
                except UnicodeEncodeError:
                    print(f"Brain: {response}")
            except Exception as e:
                try:
                    print(f"处理失败: {e}")
                except UnicodeEncodeError:
                    print(f"Processing failed: {e}")
        
        try:
            print("演示完成！系统已就绪")
            print("启动心跳监控...")
        except UnicodeEncodeError:
            print("Demo completed! System ready")
            print("Starting heartbeat monitoring...")
        
        # 启动心跳监控
        controller.start_monitoring()
        
        # 运行一段时间
        try:
            print("运行30秒观察主脑决策...")
        except UnicodeEncodeError:
            print("Running for 30 seconds to observe master brain decisions...")
            
        time.sleep(30)
        
        try:
            print("停止系统...")
        except UnicodeEncodeError:
            print("Stopping system...")
            
        controller.stop_monitoring()
        
    except Exception as e:
        try:
            print(f"系统启动失败: {e}")
        except UnicodeEncodeError:
            print(f"System startup failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()