# 🚀 实盘交易系统

基于回测验证的SharpeOptimizedStrategy策略的实盘交易系统，专为OSCent系统设计。

## 📋 系统特性

- ✅ **实时数据获取**: Binance API集成
- ✅ **智能信号生成**: SharpeOptimizedStrategy策略
- ✅ **多层次风险管理**: 动态止损止盈
- ✅ **系统监控**: 实时健康检查
- ✅ **通知告警**: Telegram集成
- ✅ **完整日志**: 结构化日志记录

## 🚀 快速开始

### 一键启动
```bash
# 设置API密钥
export BINANCE_API_KEY="your_api_key"
export BINANCE_API_SECRET="your_api_secret"

# 启动系统
python start_trading.py
```

### 分步启动
```bash
# 1. 安装依赖
pip install python-binance psutil python-telegram-bot

# 2. 配置API密钥
export BINANCE_API_KEY="your_api_key"
export BINANCE_API_SECRET="your_api_secret"

# 3. 测试系统
python demo_realtime_system.py

# 4. 启动交易
python realtime_trading_system.py
```

## 📊 策略表现

- **收益率**: 101.67%
- **胜率**: 68.8%
- **交易次数**: 16次
- **夏普比率**: 0.45

## 📁 文件结构

```
xniu-trading/
├── realtime_trading_system.py    # 主程序
├── start_trading.py              # 一键启动脚本
├── demo_realtime_system.py       # 演示脚本
├── test_realtime_system.py       # 测试脚本
├── oscent_service.py             # OSCent服务
├── system_monitor.py             # 系统监控
├── deploy.sh                     # Linux部署脚本
├── deploy.bat                    # Windows部署脚本
├── config.py                     # 配置文件
├── strategy.py                   # 交易策略
├── feature_engineer.py           # 特征工程
├── requirements.txt              # 依赖包
├── 使用指导.md                   # 使用指导
├── 快速参考.md                   # 快速参考
├── QUICK_START.md               # 快速启动指南
├── README_REALTIME.md           # 详细说明文档
└── logs/                         # 日志目录
```

## ⚙️ 配置说明

### 交易参数 (config.py)
```python
TRADING_CONFIG = {
    'SYMBOL': 'ETHUSDT',      # 交易对
    'TIMEFRAME': '2h',        # 时间框架
}

# 风险控制
'MAX_POSITION_SIZE': 0.1,     # 最大仓位10%
'STOP_LOSS_RATIO': 0.02,      # 止损2%
'TAKE_PROFIT_RATIO': 0.04,    # 止盈4%
```

### 环境变量
```bash
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
TELEGRAM_TOKEN=your_token        # 可选
TELEGRAM_CHAT_ID=your_chat_id    # 可选
```

## 🛠️ 常用命令

| 功能 | 命令 |
|------|------|
| 一键启动 | `python start_trading.py` |
| 启动服务 | `python realtime_trading_system.py` |
| 查看状态 | `./deploy.sh status` |
| 查看日志 | `./deploy.sh logs` |
| 停止服务 | `./deploy.sh stop` |
| 重启服务 | `./deploy.sh restart` |

## 📊 系统监控

### 查看实时状态
```bash
tail -f logs/realtime_trading_*.log
```

### 查看交易记录
```bash
cat trade_history.json
```

### 系统监控
```bash
python system_monitor.py
```

## 📖 使用指导

- **使用指导**: `使用指导.md` - 详细使用说明
- **快速参考**: `快速参考.md` - 常用命令速查
- **快速启动**: `QUICK_START.md` - 5分钟快速启动
- **详细文档**: `README_REALTIME.md` - 完整技术文档

## 🔧 故障排除

| 问题 | 解决方案 |
|------|----------|
| API连接失败 | 检查网络和API密钥 |
| 依赖包缺失 | `pip install -r requirements.txt` |
| 信号异常 | 检查数据质量和策略参数 |
| 系统异常 | 查看日志文件排查问题 |

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

## 🆘 获取帮助

- 查看详细文档: `README_REALTIME.md`
- 运行演示脚本: `python demo_realtime_system.py`
- 检查系统状态: `./deploy.sh status`

## 📞 技术支持

如有问题，请查看：
1. 故障排除章节
2. 日志文件
3. 系统监控

---

**🎯 开始您的量化交易之旅！**

**一键启动: `python start_trading.py`** 