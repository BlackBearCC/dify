# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dify is an open-source platform for developing LLM applications with an intuitive interface combining agentic AI workflows, RAG pipelines, agent capabilities, and model management.

The codebase consists of:

- **Backend API** (`/api`): Python Flask application with Domain-Driven Design architecture
- **Frontend Web** (`/web`): Next.js 15 application with TypeScript and React 19
- **Docker deployment** (`/docker`): Containerized deployment configurations

## Development Commands

### Backend (API)

All Python commands must be prefixed with `uv run --project api`:

```bash
# Start development servers
./dev/start-api                   # Start API server
./dev/start-worker                # Start Celery worker

# Run tests
uv run --project api pytest      # Run all tests
uv run --project api pytest tests/unit_tests/     # Unit tests only
uv run --project api pytest tests/integration_tests/  # Integration tests

# Code quality
./dev/reformat                    # Run all formatters and linters
uv run --project api ruff check --fix ./    # Fix linting issues
uv run --project api ruff format ./         # Format code
uv run --project api mypy .                 # Type checking
```

### Frontend (Web)

```bash
cd web
pnpm lint                         # Run ESLint
pnpm eslint-fix                   # Fix ESLint issues
pnpm test                         # Run Jest tests
```

## Testing Guidelines

### Backend Testing

- Use `pytest` for all backend tests
- Write tests first (TDD approach)
- Test structure: Arrange-Act-Assert

## Code Style Requirements

### Python

- Use type hints for all functions and class attributes
- No `Any` types unless absolutely necessary
- Implement special methods (`__repr__`, `__str__`) appropriately

### TypeScript/JavaScript

- Strict TypeScript configuration
- ESLint with Prettier integration
- Avoid `any` type

## Important Notes

- **Environment Variables**: Always use UV for Python commands: `uv run --project api <command>`
- **Comments**: Only write meaningful comments that explain "why", not "what"
- **File Creation**: Always prefer editing existing files over creating new ones
- **Documentation**: Don't create documentation files unless explicitly requested
- **Code Quality**: Always run `./dev/reformat` before committing backend changes

## Common Development Tasks

### Adding a New API Endpoint

1. Create controller in `/api/controllers/`
1. Add service logic in `/api/services/`
1. Update routes in controller's `__init__.py`
1. Write tests in `/api/tests/`

## Project-Specific Conventions

- All async tasks use Celery with Redis as broker

## Claude Code Development Rules

### Core Principles

#### 1. **Functionality Parity**
- **100% 功能对等**: When refactoring or modularizing code, ensure ZERO functionality loss
- **不要冗余功能**: Remove unnecessary abstractions, default values, and mock data
- **不要遗漏功能**: Maintain complete feature compatibility with original implementation
- **失败即抛异常**: Don't mask failures with default returns - let exceptions bubble up

#### 2. **Code Architecture**
- **避免过度设计**: Don't create unnecessary "engines", "managers", or abstract layers
- **功能直接实现**: Implement features directly in the main controller when appropriate
- **模块化但不过度抽象**: Organize code into modules but avoid unnecessary abstraction layers
- **保持简单**: Simple, direct implementations are often better than over-engineered solutions

#### 3. **Original Code Respect**
- **完全理解原始架构**: Fully analyze the original code structure before refactoring
- **保留核心逻辑**: Maintain the original business logic and data flow patterns
- **使用原始配置**: Use existing configuration files, prompts, and data formats
- **智能缓存策略**: Implement existing caching mechanisms (like `get_today_analysis`)

#### 4. **Error Handling**
- **不要默认数据**: Never return default/mock data when real data fails
- **不要掩盖错误**: Don't silently handle errors - let them surface
- **快速失败**: Fail fast and provide clear error messages
- **异常优于默认值**: Throw exceptions rather than return placeholder values

#### 5. **Data Processing**
- **真实数据流**: Ensure data flows exactly as in the original system
- **格式化精确**: Match original data formatting requirements precisely  
- **计算准确**: Technical indicators and calculations must be identical
- **缓存智能**: Implement intelligent caching with dependency tracking

#### 6. **Integration Requirements**
- **Prompt文件集成**: Use existing prompt files, not hardcoded templates
- **配置驱动**: All parameters must be configurable via YAML files
- **数据库完全兼容**: Database schemas and operations must match original
- **API客户端复用**: Reuse existing LLM and data API clients

### Anti-Patterns to Avoid

#### ❌ **Don't Create These:**
- "华尔街引擎" or similar unnecessarily named abstractions
- Default/mock data when real data is unavailable  
- Simplified versions of complex original logic
- New abstractions that weren't in the original code
- Hardcoded prompts when prompt files exist

#### ❌ **Don't Do These:**
- Skip understanding the original code architecture
- Create "improved" versions without user request
- Hide errors behind default return values
- Oversimplify complex analysis workflows
- Break existing caching and dependency mechanisms

#### ❌ **Don't Return These:**
- "暂无数据" when APIs fail - throw exceptions instead
- Placeholder analysis results - fail transparently
- Mock technical indicators - calculate real ones or fail
- Generic error messages - provide specific failure details

### Required Analysis Before Changes

#### Before Any Refactoring:
1. **完整分析原始代码**: Read and understand the complete original implementation
2. **识别所有功能点**: List every feature, method, and capability  
3. **理解数据流**: Map the complete data flow from input to output
4. **检查依赖关系**: Understand all dependencies and caching mechanisms
5. **验证配置使用**: Ensure all configuration parameters are preserved

#### Quality Gates:
- **功能测试**: Every original feature must work identically
- **数据验证**: All data processing must produce identical results
- **错误处理**: Error cases must fail in the same way as original
- **性能保持**: Performance characteristics should be maintained or improved

### Code Quality Standards

- **类型安全**: Use proper type hints, avoid `Any` types
- **异常处理**: Comprehensive error handling with meaningful messages  
- **代码清晰**: Clear, readable code with logical structure
- **文档准确**: Accurate docstrings and comments explaining business logic
- **测试完整**: Comprehensive tests covering all functionality

### When in Doubt

- **Ask for clarification** rather than making assumptions
- **Preserve original behavior** rather than "improving" it
- **Fail explicitly** rather than returning defaults
- **Keep it simple** rather than over-engineering

## Financial Data Development Rules

### Core Principles for Financial Code

#### 1. **Data Accuracy is Paramount**
- **真实数据优先**: Only use real data from verified sources
- **不要虚构数据**: Never create fake estimates or multiply real data arbitrarily
- **明确标注估算**: If estimation is required, clearly mark it as such
- **数据来源透明**: Always specify data sources and their limitations

#### 2. **Code Simplicity Requirements** 
- **变量名要简单**: Use simple, clear variable names like `price`, `volume`, `data`
- **避免复杂抽象**: Don't create unnecessary managers, engines, or abstract classes
- **直接实现功能**: Implement features directly without over-engineering
- **一个功能一个文件**: Keep related functionality in single, focused files

#### 3. **Financial Data Integrity**
- **不要估算周月数据**: Never multiply daily data by 7 or 30 for weekly/monthly estimates
- **显示实际可得数据**: Show only what data is actually available
- **API限制要说明**: Clearly state when data is unavailable due to API limitations
- **错误要明确报告**: Report data collection failures explicitly

#### 4. **Code Structure Standards**
```python
# ✅ GOOD - Simple and clear
price = ticker.get_price()
volume = ticker.get_volume()
if price > 100:
    return "high"

# ❌ BAD - Over-complicated
financial_data_processor = FinancialDataProcessingEngine()
market_metrics_analyzer = MarketMetricsAnalysisManager()
price_threshold_configuration = PriceThresholdConfigurationHandler()
```

#### 5. **Variable Naming Rules**
- **简单英文名**: `price`, `volume`, `data`, `result`
- **避免长描述性名称**: Not `comprehensive_market_data_collection_result`
- **直观易懂**: Code should be readable by any developer
- **不要缩写**: Use `price` not `prc`, `data` not `dt`

#### 6. **Function Design Rules**
- **功能单一**: Each function does one thing well
- **参数简单**: Minimal parameters, clear types
- **返回值明确**: Return what you promise to return
- **错误处理直接**: Raise exceptions for failures

### Anti-Patterns for Financial Code

#### ❌ **Never Do These:**
- Create weekly/monthly estimates by multiplying daily data
- Use complex class hierarchies for simple data operations
- Hide data limitations behind "smart defaults"
- Name variables like `comprehensive_etf_data_aggregation_result`
- Create managers for simple API calls
- Estimate financial flows without real data

#### ❌ **Avoid These Patterns:**
```python
# DON'T - Over-engineered
class FinancialDataAggregationManager:
    def __init__(self):
        self.comprehensive_data_processor = DataProcessorEngine()
        
# DON'T - Fake estimates  
weekly_flow = daily_flow * 7  # This is wrong!

# DON'T - Complex variable names
bitcoin_etf_comprehensive_flow_analysis_result = get_data()
```

#### ✅ **Do These Instead:**
```python
# DO - Simple and direct
def get_etf_data():
    data = api.fetch_etf_prices()
    return data

# DO - Clear limitations
def get_weekly_flow():
    # Weekly flow data not available from this API
    raise NotImplementedError("Weekly flow data not supported")

# DO - Simple names
etf_data = get_etf_data()
price = etf_data['price']
```

## Crypto Monitor Configuration Rules

### Configuration File Management

#### 1. **Master Configuration File**
- **配置文件路径**: `C:\Users\TYZS\PycharmProjects\dify\workflows\scripts\crypto_monitor_project\config\crypto_monitor_config.yaml`
- **配置驱动开发**: All important variables, parameters, and settings MUST be stored in this YAML file
- **代码中禁止硬编码**: Never hardcode crypto symbols, intervals, thresholds, or any business parameters in Python code
- **动态配置加载**: Code should read configuration at runtime and respect changes

#### 2. **Configuration Usage Requirements**
```python
# ✅ GOOD - Read from configuration
major_symbols = self.settings.monitor.primary_symbols + self.settings.monitor.secondary_symbols

# ❌ BAD - Hardcoded values
major_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']  # DON'T DO THIS!
```

#### 3. **Important Parameters to Configure**
- **监控币种**: `监控币种.主要币种` and `监控币种.次要币种`
- **技术指标参数**: RSI periods, MACD settings, MA periods
- **触发条件**: Analysis intervals, thresholds, cooldown times
- **风险管理**: Position sizes, leverage, stop-loss/take-profit
- **API配置**: Model selections, timeouts, retry counts
- **交易参数**: Order types, minimum quantities, slippage

#### 4. **Configuration Anti-Patterns**
- ❌ Hardcoding crypto symbols in data collection methods
- ❌ Fixed intervals that ignore configuration settings
- ❌ Embedded thresholds in business logic
- ❌ Model selections hardcoded in analyst classes
- ❌ API endpoints or timeouts not configurable

#### 5. **Dynamic Configuration Loading**
```python
# ✅ GOOD - Dynamic configuration usage
def get_monitoring_symbols(self):
    return {
        'primary_symbols': self.settings.monitor.primary_symbols or [],
        'secondary_symbols': self.settings.monitor.secondary_symbols or []
    }

# ✅ GOOD - Configurable thresholds
rsi_overbought = self.settings.indicators.rsi.overbought_line
rsi_oversold = self.settings.indicators.rsi.oversold_line
```

#### 6. **Configuration Validation Rules**
- All configuration changes should be validated at startup
- Invalid symbols should be rejected with clear error messages
- Parameter ranges should be checked (e.g., RSI period > 0)
- Required fields should have validation

### Code Quality Checklist

Before submitting crypto monitor code:
- [ ] All crypto symbols read from configuration file
- [ ] All intervals and thresholds configurable
- [ ] No hardcoded business parameters in Python code
- [ ] Configuration changes reflected immediately
- [ ] All variable names are simple and clear
- [ ] No fake estimates or arbitrary multiplications
- [ ] Data sources are clearly documented
- [ ] Error cases are handled explicitly
- [ ] Functions are small and focused
- [ ] No unnecessary abstractions or managers
- [ ] Financial accuracy is maintained
