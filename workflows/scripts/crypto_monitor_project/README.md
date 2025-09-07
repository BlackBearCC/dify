# 加密货币监控系统模块化版本

## 项目结构

```
crypto_monitor_project/
├── config/                    # 配置管理模块
│   ├── __init__.py
│   ├── config_manager.py      # 配置管理器
│   └── settings.py            # 配置数据结构
├── database/                  # 数据库模块
│   ├── __init__.py
│   ├── database_manager.py    # 数据库管理器
│   └── models.py              # 数据模型
├── data/                      # 数据采集模块
│   ├── __init__.py
│   ├── data_collector.py      # 统一数据收集器
│   ├── binance_client.py      # 币安API客户端
│   └── coingecko_client.py    # CoinGecko API客户端
├── core/                      # 技术指标模块
│   ├── __init__.py
│   ├── indicator_calculator.py # 指标计算器
│   ├── rsi.py                 # RSI指标
│   ├── macd.py                # MACD指标
│   └── moving_average.py      # 移动平均线
├── analysis/                  # 分析师模块
│   ├── __init__.py
│   ├── base_analyst.py        # 基础分析师
│   ├── technical_analyst.py   # 技术分析师
│   ├── market_analyst.py      # 市场分析师
│   ├── fundamental_analyst.py # 基本面分析师
│   └── chief_analyst.py       # 首席分析师
├── crypto_monitor_controller.py # 主控制器
├── main.py                    # 程序入口
├── __init__.py               # 模块初始化
└── README.md                 # 项目说明
```

## 模块职责

### 1. 配置管理模块 (`config/`)
- 统一管理所有系统配置
- 支持YAML配置文件解析
- 提供类型安全的配置对象

### 2. 数据库模块 (`database/`)
- 管理SQLite数据库操作
- 定义数据模型和表结构
- 提供CRUD接口和数据清理

### 3. 数据采集模块 (`data/`)
- 统一管理多个数据源
- 实现数据缓存和频率控制
- 支持币安、CoinGecko等API

### 4. 技术指标模块 (`core/`)
- 计算RSI、MACD、移动平均线等指标
- 提供技术分析信号检测
- 支持自定义指标参数

### 5. 分析师模块 (`analysis/`)
- 多个专业分析师角色
- 基于LLM的智能分析
- 支持技术面、基本面、市场面分析

### 6. 主控制器
- 整合所有模块功能
- 实现监控循环和事件触发
- 提供系统状态管理

## 使用方法

```python
from crypto_monitor_project import CryptoMonitorController

# 初始化系统
controller = CryptoMonitorController()

# 启动监控
controller.start_monitoring()

# 手动分析
result = controller.manual_analysis('BTCUSDT')

# 获取系统状态
status = controller.get_system_status()
```

## 优势

1. **模块化设计**: 每个模块职责单一，便于维护和扩展
2. **类型安全**: 使用dataclass和类型提示，减少运行时错误
3. **配置驱动**: 所有参数通过配置文件管理，便于调整
4. **错误处理**: 完善的异常处理和日志记录
5. **测试友好**: 模块化便于单元测试和集成测试

## 版本信息

- 版本: 2.0.0
- 重构: 从单体文件拆分为模块化架构
- 兼容: 保持原有功能的同时提升代码质量