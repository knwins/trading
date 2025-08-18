# 实盘交易系统 - OSCent服务

基于回测验证的SharpeOptimizedStrategy策略的实盘交易系统，专为OSCent系统设计。

## 🚀 系统概述

### 核心特性
- **策略验证**: 基于回测验证的SharpeOptimizedStrategy策略
- **实时交易**: 支持Binance实盘交易
- **风险管理**: 多层次风险控制机制
- **系统监控**: 实时健康检查和性能监控
- **通知告警**: Telegram实时通知
- **日志记录**: 完整的交易和系统日志

### 技术架构
```
实盘交易系统
├── 数据层 (Binance API)
├── 策略层 (SharpeOptimizedStrategy)
├── 风控层 (RiskManager)
├── 执行层 (TradeExecutor)
├── 监控层 (SystemMonitor)
└── 通知层 (Telegram/Email)
```

## 📋 系统要求

### 硬件要求
- CPU: 2核心以上
- 内存: 4GB以上
- 存储: 10GB可用空间
- 网络: 稳定的互联网连接

### 软件要求
- Python 3.8+
- Linux/Windows/macOS
- Git

### 依赖包
```bash
pip install -r requirements.txt
```

## 🔧 安装配置

### 1. 克隆项目
```bash
git clone <repository-url>
cd xniu-trading
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
```bash
# Binance API配置
export BINANCE_API_KEY="your_api_key"
export BINANCE_API_SECRET="your_api_secret"

# Telegram通知配置（可选）
export TELEGRAM_TOKEN="your_telegram_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

### 4. 配置文件
编辑 `config.py` 文件，调整交易参数：
```python
# 交易配置
TRADING_CONFIG = {
    'SYMBOL': 'ETHUSDT',      # 交易对
    'TIMEFRAME': '1h',        # 时间框架
    'BASE_QUANTITY': 0.01,    # 基础交易量
}

# 风险管理配置
RISK_CONFIG = {
    'MAX_POSITION_SIZE': 0.1,  # 最大仓位比例
    'STOP_LOSS_RATIO': 0.02,   # 止损比例
    'TAKE_PROFIT_RATIO': 0.04, # 止盈比例
    'MAX_DAILY_LOSS': 0.05,    # 最大日亏损
}
```

## 🚀 启动服务

### 使用部署脚本（推荐）
```bash
# 启动服务
./deploy.sh start

# 查看状态
./deploy.sh status

# 查看日志
./deploy.sh logs

# 停止服务
./deploy.sh stop

# 重启服务
./deploy.sh restart
```

### 直接启动
```bash
python oscent_service.py
```

## 📊 系统监控

### 健康检查
系统自动监控以下指标：
- CPU使用率
- 内存使用率
- 磁盘使用率
- 网络IO
- 交易状态
- 盈亏情况

### 告警机制
- **CPU > 90%**: 严重告警
- **内存 > 95%**: 严重告警
- **总亏损 > 10%**: 严重告警
- **日亏损 > 5%**: 警告

### 监控命令
```bash
# 启动监控
python system_monitor.py

# 导出监控数据
python -c "from system_monitor import SystemMonitor; monitor = SystemMonitor(); monitor.export_metrics()"
```

## 📈 交易策略

### 策略概述
基于SharpeOptimizedStrategy的多因子量化策略：

1. **技术指标**: ADX, RSI, MACD, EMA, ATR, OBV等
2. **信号过滤**: 价格偏离、RSI超买超卖、波动率等
3. **动态阈值**: 基于市场状态的动态调整
4. **风险管理**: 多层次止损止盈机制

### 策略参数
```python
OPTIMIZED_STRATEGY_CONFIG = {
    'windows': {
        'short': 300,  # 短期窗口
        'long': 600,   # 长期窗口
    },
    'signal_direction': {
        'long_threshold': 0.1,   # 多头阈值
        'short_threshold': -0.1, # 空头阈值
    },
    'final_score_weights': {
        'signal_weight': 0.6,    # 信号权重
        'trend_weight': 0.4,     # 趋势权重
    }
}
```

## 🛡️ 风险管理

### 风险控制机制
1. **仓位控制**: 最大仓位比例限制
2. **止损机制**: 固定止损 + 动态止损
3. **止盈机制**: 固定止盈 + 技术止盈
4. **日亏损限制**: 防止单日过度亏损
5. **信号过滤**: 多重过滤机制

### 风险参数
```python
RISK_PARAMS = {
    'max_position_size': 0.1,    # 最大仓位10%
    'stop_loss_ratio': 0.02,     # 止损2%
    'take_profit_ratio': 0.04,   # 止盈4%
    'max_daily_loss': 0.05,      # 最大日亏损5%
}
```

## 📝 日志系统

### 日志文件
- `logs/realtime_trading_YYYYMMDD_HHMMSS.log`: 交易日志
- `logs/system_monitor_YYYYMMDD_HHMMSS.log`: 监控日志
- `logs/oscent_service_YYYYMMDD_HHMMSS.log`: 服务日志

### 日志级别
- **INFO**: 正常操作信息
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **DEBUG**: 调试信息

### 日志查看
```bash
# 查看实时日志
tail -f logs/realtime_trading_*.log

# 查看错误日志
grep "ERROR" logs/*.log

# 查看交易记录
cat trade_history.json
```

## 🔔 通知系统

### Telegram通知
配置Telegram机器人后，系统会发送以下通知：
- 交易执行通知
- 止损止盈通知
- 系统告警通知
- 每日交易总结

### 通知配置
```python
NOTIFICATION_CONFIG = {
    'telegram_token': 'your_token',
    'telegram_chat_id': 'your_chat_id',
    'alert_enabled': True,
}
```

## 📊 性能指标

### 回测结果
基于历史数据的回测表现：
- **收益率**: 101.67%
- **胜率**: 68.8%
- **交易次数**: 16次
- **最大回撤**: 36.3%
- **夏普比率**: 0.45

### 实盘监控
- 实时盈亏统计
- 交易频率监控
- 信号质量分析
- 风险指标跟踪

## 🛠️ 故障排除

### 常见问题

#### 1. API连接失败
```bash
# 检查网络连接
ping api.binance.com

# 检查API密钥
echo $BINANCE_API_KEY
```

#### 2. 策略信号异常
```bash
# 检查数据质量
python signals_sharpe.py

# 查看策略日志
grep "信号" logs/*.log
```

#### 3. 系统资源不足
```bash
# 检查系统资源
htop
df -h
free -h
```

### 调试模式
```bash
# 启用调试日志
export LOG_LEVEL=DEBUG
python oscent_service.py
```

## 🔄 维护管理

### 日常维护
```bash
# 清理旧日志
./deploy.sh clean

# 备份数据
./deploy.sh backup

# 更新依赖
./deploy.sh install
```

### 系统升级
```bash
# 停止服务
./deploy.sh stop

# 备份数据
./deploy.sh backup

# 更新代码
git pull

# 重启服务
./deploy.sh start
```

## 📞 技术支持

### 联系方式
- 邮箱: support@example.com
- 文档: [系统文档](https://docs.example.com)
- 问题反馈: [GitHub Issues](https://github.com/example/issues)

### 技术支持时间
- 工作日: 9:00-18:00
- 紧急情况: 24/7

## 📄 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。

## ⚠️ 免责声明

本系统仅供学习和研究使用，不构成投资建议。使用本系统进行实盘交易的风险由用户自行承担。请谨慎使用，合理控制风险。 