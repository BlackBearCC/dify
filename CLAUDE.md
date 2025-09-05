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
