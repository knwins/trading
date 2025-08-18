# 🚀 实盘交易系统 - 快速启动指南

基于回测验证的SharpeOptimizedStrategy策略的实盘交易系统，专为OSCent系统设计。

## ⚡ 5分钟快速启动

### 1️⃣ 环境准备
```bash
# 安装Python依赖
pip install -r requirements.txt

# 或安装核心依赖
pip install python-binance psutil python-telegram-bot pandas numpy
```

### 2️⃣ 配置API密钥
```bash
# 设置环境变量
export BINANCE_API_KEY="your_api_key"
export BINANCE_API_SECRET="your_api_secret"

# Windows系统
set BINANCE_API_KEY=your_api_key
set BINANCE_API_SECRET=your_api_secret
```

### 3️⃣ 测试系统
```bash
# 运行演示脚本
python demo_realtime_system.py

# 或运行测试脚本
python test_realtime_system.py
```

### 4️⃣ 启动实盘交易
```bash
# 直接启动
python realtime_trading_system.py

# 或使用部署脚本
./deploy.sh start          # Linux/macOS
deploy.bat start           # Windows
```

## 📊 系统特性

### ✅ 核心功能
- **实时数据获取**: Binance API集成
- **智能信号生成**: SharpeOptimizedStrategy策略
- **风险管理**: 多层次风险控制
- **动态止损止盈**: 基于技术指标
- **系统监控**: 实时健康检查
- **通知告警**: Telegram集成
- **完整日志**: 结构化日志记录

### 📈 策略表现
- **收益率**: 101.67%
- **胜率**: 68.8%
- **交易次数**: 16次
- **夏普比率**: 0.45

## 🔧 配置说明

### 交易参数 (config.py)
```python
TRADING_CONFIG = {
    'SYMBOL': 'ETHUSDT',      # 交易对
    'TIMEFRAME': '2h',        # 时间框架
}

# 风险管理
RISK_CONFIG = {
    'MAX_POSITION_SIZE': 0.1,  # 最大仓位10%
    'STOP_LOSS_RATIO': 0.02,   # 止损2%
    'TAKE_PROFIT_RATIO': 0.04, # 止盈4%
}
```

### 环境变量
```bash
# 必需
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# 可选 (通知功能)
TELEGRAM_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 🛠️ 管理命令

### 服务管理
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

### 系统维护
```bash
# 安装依赖
./deploy.sh install

# 清理日志
./deploy.sh clean

# 备份数据
./deploy.sh backup
```

## 📁 文件结构

```
xniu-trading/
├── realtime_trading_system.py    # 主程序
├── oscent_service.py             # OSCent服务
├── system_monitor.py             # 系统监控
├── demo_realtime_system.py       # 演示脚本
├── test_realtime_system.py       # 测试脚本
├── deploy.sh                     # Linux部署脚本
├── deploy.bat                    # Windows部署脚本
├── requirements.txt              # 依赖包
├── config.py                     # 配置文件
├── strategy.py                   # 交易策略
├── feature_engineer.py           # 特征工程
└── logs/                         # 日志目录
```

## 🔍 监控和日志

### 日志文件
- `logs/realtime_trading_*.log`: 交易日志
- `logs/system_monitor_*.log`: 监控日志
- `logs/oscent_service_*.log`: 服务日志

### 实时监控
```bash
# 查看实时日志
tail -f logs/realtime_trading_*.log

# 查看错误日志
grep "ERROR" logs/*.log

# 查看交易记录
cat trade_history.json
```

## ⚠️ 重要提醒

### 安全注意事项
1. **API密钥安全**: 不要在代码中硬编码API密钥
2. **测试模式**: 首次使用建议在测试网运行
3. **风险控制**: 合理设置仓位大小和止损
4. **监控告警**: 配置Telegram通知及时了解系统状态

### 免责声明
- 本系统仅供学习和研究使用
- 不构成投资建议
- 使用本系统进行实盘交易的风险由用户自行承担
- 请谨慎使用，合理控制风险

## 🆘 故障排除

### 常见问题

#### 1. API连接失败
```bash
# 检查网络连接
ping api.binance.com

# 检查API密钥
echo $BINANCE_API_KEY
```

#### 2. 依赖包缺失
```bash
# 重新安装依赖
pip install -r requirements.txt

# 或手动安装
pip install python-binance psutil python-telegram-bot
```

#### 3. 策略信号异常
```bash
# 检查数据质量
python signals_sharpe.py

# 查看策略日志
grep "信号" logs/*.log
```

### 获取帮助
- 查看详细文档: `README_REALTIME.md`
- 运行演示脚本: `python demo_realtime_system.py`
- 检查系统状态: `./deploy.sh status`

## 🎯 下一步

1. **配置真实API密钥**
2. **调整交易参数**
3. **启动实盘交易**
4. **监控系统运行**
5. **分析交易结果**

---

**🚀 祝您交易顺利！** 