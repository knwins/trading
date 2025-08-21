# DeepSeek AI信号整合模式配置说明

## 概述

本系统支持在回测和实盘模式下灵活控制DeepSeek AI信号整合功能，确保回测时不加载DeepSeek AI信号，只在实盘交易时使用。

## 配置参数

### 1. 基础配置

在 `config.py` 的 `OPTIMIZED_STRATEGY_CONFIG` 中添加以下配置：

```python
# DeepSeek AI信号整合配置
'enable_deepseek_integration': False,  # 是否启用DeepSeek AI信号整合
'deepseek_mode': 'realtime_only',      # 模式: 'realtime_only'(仅实盘), 'backtest_only'(仅回测), 'both'(都启用)
'deepseek_weight': 0.3,                # DeepSeek信号权重 (0-1)
```

### 2. 模式说明

| 模式值 | 说明 | 适用场景 |
|--------|------|----------|
| `realtime_only` | 仅实盘模式启用DeepSeek | 回测时不使用AI信号，实盘时使用 |
| `backtest_only` | 仅回测模式启用DeepSeek | 回测时使用AI信号，实盘时不使用 |
| `both` | 两种模式都启用DeepSeek | 回测和实盘都使用AI信号 |

## 使用方法

### 1. 回测模式

在回测时，策略会自动以 `backtest` 模式初始化：

```python
# main.py 中自动设置
strategy_instance = strategy_class(
    config=OPTIMIZED_STRATEGY_CONFIG, 
    data_loader=data_loader, 
    mode='backtest'  # 回测模式
)
```

### 2. 实盘模式

在实盘交易时，策略以 `realtime` 模式初始化：

```python
# quick_signal.py 中设置
strategy = SharpeOptimizedStrategy(
    config=OPTIMIZED_STRATEGY_CONFIG, 
    data_loader=data_loader, 
    mode='realtime'  # 实盘模式
)
```

## 配置示例

### 示例1：回测时不使用DeepSeek，实盘时使用

```python
OPTIMIZED_STRATEGY_CONFIG = {
    # ... 其他配置 ...
    'enable_deepseek_integration': True,
    'deepseek_mode': 'realtime_only',  # 仅实盘启用
    'deepseek_weight': 0.3,
}
```

**效果：**
- 回测时：DeepSeek整合器禁用，使用纯技术指标信号
- 实盘时：DeepSeek整合器启用，结合AI分析和技术指标

### 示例2：回测时使用DeepSeek，实盘时不使用

```python
OPTIMIZED_STRATEGY_CONFIG = {
    # ... 其他配置 ...
    'enable_deepseek_integration': True,
    'deepseek_mode': 'backtest_only',  # 仅回测启用
    'deepseek_weight': 0.3,
}
```

**效果：**
- 回测时：DeepSeek整合器启用，用于策略验证
- 实盘时：DeepSeek整合器禁用，使用纯技术指标信号

### 示例3：两种模式都使用DeepSeek

```python
OPTIMIZED_STRATEGY_CONFIG = {
    # ... 其他配置 ...
    'enable_deepseek_integration': True,
    'deepseek_mode': 'both',  # 都启用
    'deepseek_weight': 0.3,
}
```

**效果：**
- 回测时：DeepSeek整合器启用
- 实盘时：DeepSeek整合器启用

## 日志输出

系统会根据配置输出相应的日志信息：

### 启用时
```
[2025-08-21 11:44:34] ✅ DeepSeek信号整合器已启用 (运行模式: realtime, 配置模式: realtime_only)
```

### 禁用时
```
[2025-08-21 11:44:34] ℹ️ DeepSeek信号整合器已禁用 (运行模式: backtest, 配置模式: realtime_only)
```

## 注意事项

1. **API密钥配置**：确保在 `.env` 文件中配置了 `DEEPSEEK_API_KEY`
2. **网络连接**：DeepSeek API需要网络连接，离线环境无法使用
3. **性能影响**：启用DeepSeek会增加API调用延迟，建议在实盘时使用
4. **成本考虑**：DeepSeek API调用会产生费用，请根据使用量控制成本

## 推荐配置

对于生产环境，推荐使用以下配置：

```python
OPTIMIZED_STRATEGY_CONFIG = {
    # ... 其他配置 ...
    'enable_deepseek_integration': True,
    'deepseek_mode': 'realtime_only',  # 仅实盘启用
    'deepseek_weight': 0.3,            # 适中的权重
    'cache_timeout': 300,              # 5分钟缓存，减少API调用
}
```

这样配置可以：
- 回测时使用纯技术指标，确保回测结果的准确性
- 实盘时结合AI分析，提高交易决策质量
- 通过缓存机制控制API调用频率和成本 