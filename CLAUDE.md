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

## Dify Workflow DSL Development Rules

### DSL文件格式规范

#### 1. **基本文件结构**
Dify工作流DSL文件必须遵循以下YAML格式结构：

```yaml
app:
  description: '应用描述'
  icon: 🤖  # 表情符号图标
  icon_background: '#4F46E5'  # 背景颜色代码
  mode: workflow  # 必须是workflow模式
  name: 应用名称

workflow:
  environment_variables: []  # 环境变量数组
  features:  # 功能配置
    file_upload:
      image:
        enabled: false
        number_limits: 3
        transfer_methods: [local_file, remote_url]
    opening_statement: |
      多行开场白内容
    retriever_resource:
      enabled: false
    suggested_questions:
      - 建议问题1
      - 建议问题2
    # 其他功能配置...
  graph:  # 工作流图结构
    edges: []  # 边连接
    nodes: []  # 节点定义
```

#### 2. **节点配置规范**

##### 开始节点 (Start Node)
```yaml
- data:
    desc: 工作流开始
    selected: false
    title: 开始
    type: start
    variables:  # 输入变量定义
    - description: 变量描述
      label: 显示标签
      max_length: 4000
      options: []  # 选择类型时的选项
      required: true
      type: paragraph  # 类型: text-input, paragraph, select等
      variable: variable_name
  height: 118
  id: 'unique_node_id'  # 必须是字符串格式
  position: {x: 80, y: 282}
  type: custom
  width: 244
```

##### LLM节点 (LLM Node)
```yaml
- data:
    context:
      enabled: false
      variable_selector: []
    desc: 使用大语言模型处理
    model:
      completion_params:
        frequency_penalty: 0.1
        max_tokens: 2048
        presence_penalty: 0.1
        temperature: 0.7
        top_p: 0.95
      mode: chat
      name: gpt-3.5-turbo
      provider: openai
    prompt_template:
    - id: unique_prompt_id
      role: system
      text: |
        系统提示词内容
        使用变量引用: {{#node_id.variable_name#}}
    - id: unique_user_prompt_id
      role: user
      text: '{{#start_node_id.input_variable#}}'
    selected: false
    title: LLM
    type: llm
    variables: []
    vision:
      enabled: false
  height: 98
  id: 'llm_node_id'
  position: {x: 384, y: 282}
  type: custom
  width: 244
```

##### 结束节点 (End Node)
```yaml
- data:
    desc: 输出最终结果
    outputs:
    - value_selector: ['llm_node_id', 'text']
      variable: result
    selected: false
    title: 结束
    type: end
  height: 90
  id: 'end_node_id'
  position: {x: 688, y: 282}
  type: custom
  width: 244
```

#### 3. **边连接配置 (Edges)**
```yaml
edges:
- data:
    isInIteration: false
    sourceType: start
    targetType: llm
  id: source_id-source-target_id-target
  source: 'source_node_id'
  sourceHandle: source
  target: 'target_node_id'
  targetHandle: target
  type: custom
  zIndex: 0
```

#### 4. **变量引用语法**
- **正确格式**: `{{#node_id.variable_name#}}`
- **系统变量**: 使用预定义的系统变量名
- **节点输出**: 引用其他节点的输出结果

#### 5. **重要配置要求**

##### 必须字段检查清单:
- [ ] 所有节点ID必须是字符串格式 (用引号包围)
- [ ] 每个节点必须有position坐标
- [ ] 每个节点必须有height和width
- [ ] prompt_template中每个条目必须有唯一的id
- [ ] edges必须正确连接所有节点
- [ ] 变量引用必须使用正确的语法格式

##### 功能配置规范:
```yaml
features:
  file_upload:
    image:
      enabled: false  # 明确禁用不需要的功能
      number_limits: 3
      transfer_methods: [local_file, remote_url]
  opening_statement: |
    使用多行字符串格式
    支持换行和格式化
  retriever_resource:
    enabled: false  # 明确设置状态
  sensitive_word_avoidance:
    enabled: false
  speech_to_text:
    enabled: false
  suggested_questions:
    - 问题1
    - 问题2
  suggested_questions_after_answer:
    enabled: false
  text_to_speech:
    enabled: false
```

#### 6. **常见错误避免**

##### ❌ 不要这样做:
```yaml
# 错误的版本声明
version: 0.3.1
kind: app

# 错误的节点ID格式
id: 1736424593742  # 数字格式

# 错误的变量引用
text: "{{start.user_input}}"  # 缺少#符号

# 错误的环境变量格式
environment_variables:
- name: var_name
  type: string  # 应该是value_type
  value: value
```

##### ✅ 正确做法:
```yaml
# 正确的基本结构 - 不需要version和kind

# 正确的节点ID格式
id: '1736424593742'  # 字符串格式

# 正确的变量引用
text: "{{#1736424593742.user_input#}}"

# 正确的环境变量格式
environment_variables: []  # 简化为空数组或省略
```

#### 7. **DSL测试和验证**

##### 导入前检查:
1. **YAML语法验证**: 确保文件是有效的YAML格式
2. **必填字段检查**: 所有必需的字段都已填写
3. **ID唯一性验证**: 所有节点和边的ID都是唯一的
4. **引用完整性**: 所有变量引用都指向存在的节点和变量
5. **图结构完整**: 节点之间的连接形成完整的工作流

##### 导入后验证:
1. **功能完整性**: 所有定义的功能都能正常工作
2. **变量传递**: 数据能正确在节点间传递
3. **LLM响应**: 模型调用能返回预期结果
4. **错误处理**: 异常情况能得到适当处理

### DSL开发最佳实践

#### 1. **设计原则**
- **简单优于复杂**: 优先使用基础节点而非复杂节点
- **清晰的数据流**: 确保数据在节点间的传递路径清晰
- **合理的错误处理**: 考虑各种异常情况的处理方式
- **用户体验优化**: 提供有意义的开场白和建议问题

#### 2. **性能优化**
- **合理的参数设置**: 根据实际需求设置max_tokens等参数
- **避免冗余处理**: 不要创建不必要的中间节点
- **缓存机制利用**: 合理利用Dify的内建缓存功能

#### 3. **维护性考虑**
- **描述性命名**: 节点和变量使用有意义的名称
- **适当的注释**: 在复杂的prompt中添加说明
- **版本兼容性**: 确保DSL与目标Dify版本兼容

### 故障排除指南

#### 常见导入错误:
1. **"missing value type"**: 检查environment_variables的value_type字段
2. **"invalid node configuration"**: 验证节点的必需字段
3. **"variable reference error"**: 检查变量引用语法
4. **"graph validation failed"**: 确保节点连接完整

#### 调试技巧:
1. **逐步构建**: 从简单的三节点结构开始
2. **单独测试**: 分别验证每个组件的功能
3. **日志分析**: 查看Dify后台的错误日志
4. **参考示例**: 对比成功的DSL文件格式
