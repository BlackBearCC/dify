# -*- coding: utf-8 -*-
"""
监控服务 - 处理系统监控循环和心跳决策
接管Controller中的监控循环逻辑，实现心跳监控和触发条件判断
"""

import time
import threading
from typing import Dict, List, Any, Callable, Optional

from ..config import Settings
from ..core import IndicatorCalculator, MasterBrain
from ..database import DatabaseManager, MarketData
from .data_service import DataService


class MonitoringService:
    """监控服务 - 单一职责：系统监控循环和心跳决策"""
    
    def __init__(self, settings: Settings, db_manager: DatabaseManager, 
                 data_service: DataService, indicator_calculator: IndicatorCalculator,
                 master_brain: MasterBrain):
        """
        初始化监控服务
        
        Args:
            settings: 系统配置
            db_manager: 数据库管理器
            data_service: 数据服务
            indicator_calculator: 技术指标计算器
            master_brain: 智能主脑
        """
        self.settings = settings
        self.db_manager = db_manager
        self.data_service = data_service
        self.indicator_calculator = indicator_calculator
        self.master_brain = master_brain
        
        # 监控状态
        self.is_running = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.last_analysis_time: Dict[str, float] = {}
        
        # 回调函数（用于通知Controller）
        self._on_analysis_triggered: Optional[Callable] = None
    
    def set_analysis_callback(self, callback: Callable):
        """
        设置分析触发回调函数
        
        Args:
            callback: 当需要触发分析时调用的回调函数
        """
        self._on_analysis_triggered = callback
    
    def start_monitoring(self) -> bool:
        """
        启动监控循环 - 纯待机模式，只通过Telegram控制
        
        Returns:
            bool: 启动是否成功
        """
        if self.is_running:
            print("⚠️ 监控系统已在运行")
            return False
        
        print("🔄 启动监控系统（待机模式）...")
        
        # 测试连接
        if not self._test_connections():
            print("❌ 连接测试失败，停止启动")
            return False
        
        self.is_running = True
        
        print("✅ 监控系统已启动（待机模式）")
        print("📱 系统待机中，请通过Telegram机器人进行控制")
        
        return True
    
    def stop_monitoring(self):
        """停止监控循环"""
        if not self.is_running:
            print("⚠️ 监控系统未在运行")
            return
        
        print("⏹️ 停止监控系统...")
        self.is_running = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        
        print("✅ 监控系统已停止")
    
    def _test_connections(self) -> bool:
        """测试所有连接"""
        print("🔍 测试系统连接...")
        connection_status = self.data_service.test_all_connections()
        
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
        
        while self.is_running:
            try:
                # 动态获取当前监控币种（支持主脑实时调整）
                monitoring_info = self._get_monitoring_symbols()
                primary_symbols = monitoring_info['primary_symbols']
                secondary_symbols = monitoring_info['secondary_symbols']
                all_symbols = primary_symbols + secondary_symbols
                
                if not all_symbols:
                    print("⚠️ 当前无监控币种，等待主脑设置...")
                    time.sleep(30)  # 等待30秒后重新检查
                    continue
                
                # 收集K线数据
                kline_data = self.data_service.collect_kline_data(all_symbols)
                
                # 处理每个币种
                for symbol in all_symbols:
                    if not self.is_running:
                        break
                    
                    symbol_klines = kline_data.get(symbol, [])
                    if symbol_klines:
                        self._process_symbol(symbol, symbol_klines)
                
                # 等待下次循环
                time.sleep(self.settings.kline.fetch_interval)
                
            except Exception as e:
                print(f"❌ 监控循环异常: {e}")
                time.sleep(10)
    
    def _process_symbol(self, symbol: str, kline_data: List[Dict[str, Any]]):
        """
        处理单个币种 - 智能主脑决策
        
        Args:
            symbol: 币种符号
            kline_data: K线数据
        """
        try:
            if not kline_data:
                return
            
            # 计算技术指标
            indicators = self.indicator_calculator.calculate_all_indicators(kline_data)
            
            # 保存市场数据
            self._save_market_data(symbol, kline_data[-1], indicators)
            
            # 检查特殊条件
            special_conditions = self.indicator_calculator.check_special_conditions(symbol, indicators)
            
            # 准备决策条件
            current_time = time.time()
            symbol_last_analysis = self.last_analysis_time.get(symbol, 0)
            
            # 获取当前动态心跳设置
            heartbeat_settings = self._get_heartbeat_settings()
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
            
            # 触发主脑决策
            if should_trigger_brain:
                print(f"🧠 触发智能主脑决策: {symbol} - {trigger_reason}")
                
                # 让主脑进行心跳决策
                brain_response = self.master_brain.heartbeat_decision(market_conditions)
                print(f"🧠 主脑决策结果:\n{brain_response}")
                
                # 更新分析时间
                self.last_analysis_time[symbol] = current_time
                
                # 通知Controller触发分析（如果设置了回调）
                if self._on_analysis_triggered:
                    self._on_analysis_triggered(symbol, trigger_reason, market_conditions)
            
        except Exception as e:
            print(f"❌ 处理{symbol}失败: {e}")
    
    def _save_market_data(self, symbol: str, latest_kline: Dict[str, Any], indicators: Dict[str, Any]):
        """保存市场数据到数据库"""
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
    
    def _get_monitoring_symbols(self) -> Dict[str, List[str]]:
        """获取当前监控币种列表"""
        return {
            'primary_symbols': self.settings.monitor.primary_symbols or [],
            'secondary_symbols': self.settings.monitor.secondary_symbols or [],
            'total_count': len((self.settings.monitor.primary_symbols or []) + (self.settings.monitor.secondary_symbols or []))
        }
    
    def _get_heartbeat_settings(self) -> Dict[str, Any]:
        """获取当前心跳设置"""
        return {
            'normal_interval': self.settings.triggers.normal_interval,
            'fetch_interval': self.settings.kline.fetch_interval,
            'special_conditions_enabled': True,
            'next_heartbeat_estimate': f"{self.settings.triggers.normal_interval}秒后"
        }
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        获取监控状态信息
        
        Returns:
            Dict: 监控状态
        """
        return {
            'is_running': self.is_running,
            'monitoring_symbols': self._get_monitoring_symbols(),
            'heartbeat_settings': self._get_heartbeat_settings(),
            'last_analysis_time': dict(self.last_analysis_time),
            'thread_alive': self.monitoring_thread.is_alive() if self.monitoring_thread else False
        }
    
    def force_analysis(self, symbol: str, reason: str = "手动触发") -> bool:
        """
        强制触发单个币种的分析
        
        Args:
            symbol: 币种符号
            reason: 触发原因
            
        Returns:
            bool: 是否成功触发
        """
        try:
            # 收集该币种的数据
            kline_data = self.data_service.collect_kline_data([symbol])
            symbol_klines = kline_data.get(symbol, [])
            
            if not symbol_klines:
                print(f"❌ 无法获取{symbol}的K线数据")
                return False
            
            # 计算技术指标
            indicators = self.indicator_calculator.calculate_all_indicators(symbol_klines)
            
            # 准备市场条件
            market_conditions = {
                'symbol': symbol,
                'latest_price': symbol_klines[-1]['close'],
                'indicators': indicators,
                'special_conditions': [],
                'time_since_last_analysis': 0,
                'normal_interval': self.settings.triggers.normal_interval
            }
            
            print(f"🎯 手动触发分析: {symbol} - {reason}")
            
            # 让主脑进行决策
            brain_response = self.master_brain.heartbeat_decision(market_conditions)
            print(f"🧠 主脑决策结果:\n{brain_response}")
            
            # 更新分析时间
            self.last_analysis_time[symbol] = time.time()
            
            # 通知Controller（如果设置了回调）
            if self._on_analysis_triggered:
                self._on_analysis_triggered(symbol, reason, market_conditions)
            
            return True
            
        except Exception as e:
            print(f"❌ 强制分析{symbol}失败: {e}")
            return False