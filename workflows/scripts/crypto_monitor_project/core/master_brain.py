# -*- coding: utf-8 -*-
"""
智能交易主脑 - LLM Master Brain
通过function calling协调所有agent能力
"""

import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

from ..config import Settings
from ..database import DatabaseManager
from ..data import DataCollector
from ..analysis import PromptManager


class MasterBrain:
    """智能交易主脑 - 通过LLM和function calling协调所有能力"""
    
    def __init__(self, controller_instance):
        """
        初始化主脑
        
        Args:
            controller_instance: CryptoMonitorController实例，用于访问所有组件
        """
        self.controller = controller_instance
        self.settings = controller_instance.settings
        self.prompt_manager = PromptManager()
        
        # 获取主脑使用的LLM客户端（使用首席分析师的配置）
        self.llm_client = controller_instance._get_llm_client_for_analyst('首席分析师')
        
        print("🧠 智能交易主脑初始化完成")
    
    def get_master_brain_prompt(self) -> str:
        """获取主脑提示词"""
        return """你是加密货币交易系统的智能主脑，负责协调和决策所有交易相关活动。

## 你的核心能力
你可以通过function calling调用以下专业能力：

### 分析能力
1. **technical_analysis** - 技术分析师：分析K线数据、技术指标
2. **market_sentiment_analysis** - 市场分析师：分析市场情绪、热点趋势
3. **fundamental_analysis** - 基本面分析师：分析币种基本面数据
4. **macro_analysis** - 宏观分析师：分析宏观经济环境
5. **comprehensive_analysis** - 多分析师协作：完整的多维度分析

### 交易能力
6. **get_account_status** - 获取交易账户状态
7. **get_current_positions** - 获取当前持仓信息
8. **trading_analysis** - 交易分析师：基于研究制定交易策略
9. **execute_trade** - 执行交易（需要确认）

### 监控能力
10. **get_market_data** - 获取实时市场数据
11. **get_system_status** - 获取系统运行状态
12. **manual_trigger_analysis** - 手动触发特定币种分析

### 动态控制能力（新增）
13. **set_monitoring_symbols** - 动态设置监控币种列表
14. **get_monitoring_symbols** - 获取当前监控币种列表
15. **set_heartbeat_interval** - 设置心跳监控间隔时间
16. **get_heartbeat_settings** - 获取当前心跳设置

### 通知能力
17. **send_telegram_notification** - 发送Telegram通知

## 工作原则
1. **智能决策**：根据用户请求和市场情况，智能选择合适的能力组合
2. **风险优先**：任何交易决策都要优先考虑风险控制
3. **透明执行**：清晰说明你的思考过程和调用的能力
4. **主动监控**：在心跳模式下主动分析市场并做出决策
5. **动态调整**：根据市场变化主动调整监控币种和心跳频率
6. **资源优化**：合理分配监控资源，专注于最有价值的交易机会

## 响应格式
- 首先说明你的理解和计划
- 然后调用相应的function
- 最后总结结果并给出建议

现在，请根据用户的请求，智能地调用合适的能力来完成任务。"""

    def process_request(self, request: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        处理用户请求或心跳事件
        
        Args:
            request: 用户请求或系统事件描述
            context: 附加上下文信息
            
        Returns:
            主脑的响应和处理结果
        """
        try:
            # 准备上下文信息
            context_info = self._prepare_context(context or {})
            
            # 构造完整prompt
            full_prompt = f"""
{self.get_master_brain_prompt()}

## 当前上下文
{context_info}

## 用户请求/系统事件
{request}

请智能分析并执行相应操作。
"""
            
            # 准备function definitions
            functions = self._get_function_definitions()
            
            # 调用LLM with function calling
            response = self._call_llm_with_functions(full_prompt, functions)
            
            return response
            
        except Exception as e:
            error_msg = f"❌ 主脑处理请求失败: {e}"
            print(error_msg)
            return error_msg
    
    def heartbeat_decision(self, market_conditions: Dict[str, Any]) -> str:
        """
        心跳决策 - 主脑根据市场情况自主决策
        
        Args:
            market_conditions: 当前市场情况
            
        Returns:
            主脑的决策和执行结果
        """
        heartbeat_request = f"""
## 心跳监控事件
当前市场情况：{json.dumps(market_conditions, ensure_ascii=False, indent=2, default=self._json_serializer)}

请作为智能主脑，分析当前市场情况并决定是否需要采取行动：
1. 是否需要进行深度分析？
2. 是否有交易机会？
3. 是否需要发送通知？
4. 还是继续观望？

请基于你的专业判断，调用合适的能力。
"""
        
        return self.process_request(heartbeat_request, {
            'event_type': 'heartbeat',
            'timestamp': datetime.now().isoformat()
        })
    
    def _prepare_context(self, context: Dict[str, Any]) -> str:
        """准备上下文信息"""
        context_lines = [
            f"系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"监控币种: {', '.join([s.replace('USDT', '') for s in self.settings.monitor.primary_symbols])}",
            f"系统模式: {self.settings.system.mode}"
        ]
        
        if context:
            context_lines.extend([f"{k}: {v}" for k, v in context.items()])
        
        return '\n'.join(context_lines)
    
    def _get_function_definitions(self) -> List[Dict[str, Any]]:
        """获取所有可用的function definitions"""
        return [
            {
                "name": "technical_analysis",
                "description": "执行技术分析",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "交易对，如BTCUSDT"}
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "market_sentiment_analysis", 
                "description": "分析市场情绪",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "fundamental_analysis",
                "description": "执行基本面分析", 
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "交易对，如BTCUSDT"}
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "macro_analysis",
                "description": "执行宏观分析",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "comprehensive_analysis",
                "description": "执行多分析师协作的完整分析",
                "parameters": {
                    "type": "object", 
                    "properties": {
                        "question": {"type": "string", "description": "分析问题或主题"},
                        "symbols": {"type": "array", "items": {"type": "string"}, "description": "要分析的交易对列表"}
                    },
                    "required": ["question"]
                }
            },
            {
                "name": "get_account_status",
                "description": "获取交易账户状态",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "get_current_positions",
                "description": "获取当前持仓信息", 
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "trading_analysis",
                "description": "执行交易分析和策略制定",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "analysis_results": {"type": "string", "description": "基础分析结果"},
                        "question": {"type": "string", "description": "交易相关问题"}
                    },
                    "required": ["analysis_results", "question"]
                }
            },
            {
                "name": "get_market_data",
                "description": "获取实时市场数据",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbols": {"type": "array", "items": {"type": "string"}, "description": "交易对列表"}
                    }
                }
            },
            {
                "name": "manual_trigger_analysis", 
                "description": "手动触发特定币种的完整分析",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "交易对，如BTCUSDT"}
                    },
                    "required": ["symbol"]
                }
            },
            {
                "name": "send_telegram_notification",
                "description": "发送Telegram通知",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "通知消息内容"}
                    },
                    "required": ["message"]
                }
            },
            {
                "name": "get_system_status",
                "description": "获取系统运行状态",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "set_monitoring_symbols",
                "description": "设置动态监控币种列表",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "primary_symbols": {
                            "type": "array", 
                            "items": {"type": "string"}, 
                            "description": "主要监控币种列表，如[\"BTCUSDT\", \"ETHUSDT\"]"
                        },
                        "secondary_symbols": {
                            "type": "array", 
                            "items": {"type": "string"}, 
                            "description": "次要监控币种列表，如[\"SOLUSDT\"]"
                        }
                    },
                    "required": ["primary_symbols"]
                }
            },
            {
                "name": "get_monitoring_symbols",
                "description": "获取当前监控币种列表",
                "parameters": {"type": "object", "properties": {}}
            },
            {
                "name": "set_heartbeat_interval",
                "description": "设置心跳监控间隔时间",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "interval_seconds": {
                            "type": "number", 
                            "description": "心跳间隔秒数，如300表示5分钟"
                        }
                    },
                    "required": ["interval_seconds"]
                }
            },
            {
                "name": "get_heartbeat_settings",
                "description": "获取当前心跳设置",
                "parameters": {"type": "object", "properties": {}}
            }
        ]
    
    def _call_llm_with_functions(self, prompt: str, functions: List[Dict[str, Any]]) -> str:
        """调用LLM with function calling"""
        if not self.llm_client:
            return "❌ LLM客户端未初始化"
        
        try:
            # 不同的LLM客户端可能有不同的function calling接口
            # 这里先用简单的方式实现，后续可以扩展
            
            # 构造带function信息的prompt - 简化版本
            function_list = "\n".join([f"- {f['name']}: {f['description']}" for f in functions])
            enhanced_prompt = f"""{prompt}

可用的函数调用:
{function_list}

如果需要调用函数，请用以下格式：
FUNCTION_CALL: function_name(param1=value1, param2=value2)

注意：字符串参数要用引号，数组参数用方括号。
"""
            
            response = self.llm_client.call(enhanced_prompt)
            
            # 解析是否包含function call
            processed_response = self._process_function_calls(response)
            
            return processed_response
            
        except Exception as e:
            return f"❌ LLM调用失败: {e}"
    
    def _process_function_calls(self, response: str) -> str:
        """处理响应中的function calls - 简化版本"""
        lines = response.split('\n')
        processed_lines = []
        
        for line in lines:
            if line.strip().startswith('FUNCTION_CALL:'):
                # 解析并执行function call
                try:
                    func_call = line.replace('FUNCTION_CALL:', '').strip()
                    result = self._execute_function_call(func_call)
                    processed_lines.append(f"📞 执行: {func_call}")
                    processed_lines.append(f"📋 结果: {result}")
                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    processed_lines.append(f"❌ 函数调用失败: {e}")
                    processed_lines.append(f"详细错误: {error_detail}")
            else:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _execute_function_call(self, func_call: str) -> str:
        """执行具体的function call"""
        try:
            # 简单的函数调用解析（实际项目中可以用更完善的解析器）
            if 'technical_analysis(' in func_call:
                symbol = self._extract_param(func_call, 'symbol')
                return self.controller.analyze_kline_data(symbol)
            
            elif 'market_sentiment_analysis(' in func_call:
                return self.controller.analyze_market_sentiment()
            
            elif 'fundamental_analysis(' in func_call:
                symbol = self._extract_param(func_call, 'symbol') 
                return self.controller.analyze_fundamental_data(symbol)
            
            elif 'macro_analysis(' in func_call:
                return self.controller.analyze_macro_data()
            
            elif 'comprehensive_analysis(' in func_call:
                question = self._extract_param(func_call, 'question')
                symbols = self._extract_param(func_call, 'symbols')
                # symbols 现在可能是列表或字符串
                if isinstance(symbols, str) and symbols:
                    symbols = [symbols]  # 单个symbol转为列表
                return self.controller.ask_claude_with_data(question, symbols)
            
            elif 'get_account_status(' in func_call:
                return json.dumps(self.controller.get_account_info(), ensure_ascii=False, indent=2, default=self._json_serializer)
            
            elif 'get_current_positions(' in func_call:
                # 获取当前持仓信息
                positions = self.controller.portfolio_manager.get_positions()
                return json.dumps(positions, ensure_ascii=False, indent=2, default=self._json_serializer)
            
            elif 'manual_trigger_analysis(' in func_call:
                symbol = self._extract_param(func_call, 'symbol')
                if symbol:
                    return self.controller.manual_analysis(symbol)
                else:
                    # 尝试从symbols参数获取（数组格式）
                    symbols = self._extract_param(func_call, 'symbols')
                    if symbols and isinstance(symbols, list):
                        results = []
                        for s in symbols:
                            result = self.controller.manual_analysis(s)
                            results.append(f"{s}: {result}")
                        return "\n".join(results)
                    else:
                        return "❌ 未找到有效的symbol或symbols参数"
            
            elif 'send_telegram_notification(' in func_call:
                message = self._extract_param(func_call, 'message')
                result = self.controller.telegram_integration.send_notification(message)
                return f"通知发送{'成功' if result else '失败'}"
            
            elif 'get_system_status(' in func_call:
                return json.dumps(self.controller.get_system_status(), ensure_ascii=False, indent=2, default=self._json_serializer)
            
            elif 'set_monitoring_symbols(' in func_call:
                primary_symbols = self._extract_param(func_call, 'primary_symbols')
                secondary_symbols = self._extract_param(func_call, 'secondary_symbols') or []
                return self.controller.set_monitoring_symbols(primary_symbols, secondary_symbols)
            
            elif 'get_monitoring_symbols(' in func_call:
                return json.dumps(self.controller.get_monitoring_symbols(), ensure_ascii=False, indent=2)
            
            elif 'set_heartbeat_interval(' in func_call:
                interval_seconds = self._extract_param(func_call, 'interval_seconds')
                return self.controller.set_heartbeat_interval(float(interval_seconds))
            
            elif 'get_heartbeat_settings(' in func_call:
                return json.dumps(self.controller.get_heartbeat_settings(), ensure_ascii=False, indent=2)
            
            else:
                return f"❌ 未知的函数调用: {func_call}"
                
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            return f"❌ 函数执行失败: {e}\n详细错误: {error_detail}"
    
    def _extract_param(self, func_call: str, param_name: str) -> Optional[str]:
        """从函数调用字符串中提取参数值"""
        try:
            import re
            
            # 简单的参数提取 - 数组参数特殊处理
            if param_name == 'symbols' and '[' in func_call and ']' in func_call:
                pattern = f'{param_name}=(\\[[^\\]]+\\])'
                match = re.search(pattern, func_call)
                if match:
                    array_str = match.group(1)
                    # 简单解析数组内容
                    array_content = array_str[1:-1].strip()  # 移除[]
                    if array_content:
                        items = [item.strip().strip('"\'') for item in array_content.split(',')]
                        return items
                    return []
            
            # 普通参数处理 - 简化版
            pattern = f'{param_name}=([^,)]+)'
            match = re.search(pattern, func_call)
            if match:
                value = match.group(1).strip()
                # 移除引号
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                return value if value else None
            return None
        except Exception as e:
            print(f"⚠️ 参数提取失败 {param_name}: {e}")
            return None
    
    def _json_serializer(self, obj):
        """自定义JSON序列化器 - 处理不可序列化的类型"""
        import numpy as np
        
        if isinstance(obj, np.bool_):
            return bool(obj)  # numpy bool转为Python bool
        elif isinstance(obj, np.integer):
            return int(obj)   # numpy int转为Python int
        elif isinstance(obj, np.floating):
            return float(obj) # numpy float转为Python float
        elif isinstance(obj, np.ndarray):
            return obj.tolist() # numpy数组转为列表
        elif hasattr(obj, '__dict__'):
            return str(obj)  # 对象转为字符串
        elif callable(obj):
            return str(obj)  # 函数转为字符串
        else:
            return str(obj)  # 其他类型转为字符串