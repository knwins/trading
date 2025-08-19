# 实盘交易系统

基于SharpeOptimizedStrategy策略的实盘交易系统，支持在CentOS7上自动运行。

## 🚀 功能特性

- **智能交易策略**: 基于Sharpe比率优化的多因子交易策略
- **实时监控**: 系统状态、性能、健康度实时监控
- **风险管理**: 多层次风险控制机制
- **自动运行**: 支持CentOS7 systemd服务管理
- **通知系统**: Telegram实时通知
- **日志管理**: 完整的日志记录和轮转
- **健康检查**: 系统健康状态检查

## 📋 系统要求

- **操作系统**: CentOS 7 或更高版本
- **Python**: Python 3.8+
- **内存**: 最少2GB RAM
- **磁盘**: 最少10GB可用空间
- **网络**: 稳定的互联网连接

## 🛠️ 快速安装

### 1. 克隆项目

```bash
git clone <repository-url>
cd xniu-trading
```

### 2. 运行安装脚本

```bash
# 给脚本执行权限
chmod +x deploy.sh

# 以root权限运行安装脚本
sudo ./deploy.sh
```

### 3. 配置API密钥

```bash
# 编辑环境变量文件
sudo vim /opt/trading/.env
```

配置以下参数：
```env
# 交易所API配置
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET=your_binance_secret

# Telegram通知配置
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# 系统配置
TRADING_ENABLED=true
SANDBOX_MODE=true
LOG_LEVEL=INFO
```

### 4. 启动系统

```bash
# 启动交易系统
sudo /opt/trading/start.sh

# 检查系统状态
sudo /opt/trading/status.sh
```

## 📊 系统架构

```
xniu-trading/
├── trading.py    # 实盘交易系统主程序
├── service.py               # 系统服务管理
├── monitor.py               # 系统监控模块
├── strategy.py              # 交易策略实现
├── data_loader.py           # 数据加载器
├── feature_engineer.py      # 特征工程
├── config.py                # 配置文件
├── deploy.sh                # 部署脚本
├── requirements.txt         # Python依赖
└── logs/                    # 日志目录
```

## 🔧 管理命令

### 服务管理

```bash
# 启动系统
sudo /opt/trading/start.sh

# 停止系统
sudo /opt/trading/stop.sh

# 查看状态
sudo /opt/trading/status.sh

# 查看日志
sudo /opt/trading/logs.sh
```

### 系统监控

```bash
# 实时监控
python3 monitor.py monitor --interval 30

# 健康检查
python3 monitor.py health-check
```

### 服务管理

```bash
# 安装服务
python3 service.py install

# 卸载服务
python3 service.py uninstall

# 启动服务
python3 service.py start

# 停止服务
python3 service.py stop

# 重启服务
python3 service.py restart

# 查看服务状态
python3 service.py status

# 查看服务日志
python3 service.py logs
```

## 📈 策略说明

### SharpeOptimizedStrategy

基于Sharpe比率优化的多因子交易策略，包含以下组件：

1. **技术指标评分**: RSI、MACD、布林带等技术指标
2. **趋势强度评分**: 多时间框架趋势分析
3. **风险评分**: 波动率和回撤控制
4. **信号过滤**: 多层信号过滤机制

### 风险控制

- **仓位控制**: 最大仓位10%
- **止损机制**: 5%止损
- **止盈机制**: 10%止盈
- **日损失限制**: 最大日损失2%
- **回撤控制**: 最大回撤15%

## 🔍 监控指标

### 系统指标
- CPU使用率
- 内存使用率
- 磁盘使用率
- 网络IO

### 交易指标
- 信号数量
- 交易数量
- 错误数量
- 最后信号时间

### 网络指标
- API延迟
- 连接状态
- 错误率

## 📝 日志说明

### 日志文件位置
- 交易日志: `/opt/trading/logs/live_trading_*.log`
- 监控日志: `/opt/trading/logs/monitor.log`
- 服务日志: `/opt/trading/logs/service_manager.log`

### 日志级别
- `INFO`: 一般信息
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

### 查看日志
```bash
# 实时查看交易日志
tail -f /opt/trading/logs/live_trading_*.log

# 查看系统服务日志
journalctl -u trading-system -f

# 查看监控服务日志
journalctl -u trading-monitor -f
```

## 🚨 告警机制

### 告警类型
- **系统告警**: CPU、内存、磁盘使用率过高
- **网络告警**: API延迟过高、连接断开
- **交易告警**: 错误过多、长时间无信号

### 告警通知
- Telegram机器人通知
- 系统日志记录
- 邮件通知（可选）

## 🔒 安全配置

### 系统安全
- 专用系统用户 `trading`
- 文件权限限制
- SELinux配置
- 防火墙规则

### API安全
- API密钥环境变量存储
- 测试网模式支持
- 访问频率限制
- 错误重试机制

## 📊 性能优化

### 系统优化
- 文件描述符限制: 65536
- 进程数限制: 4096
- 日志轮转: 30天保留
- 内存监控

### 网络优化
- 连接池管理
- 超时设置
- 重试机制
- 负载均衡

## 🐛 故障排除

### 常见问题

1. **服务启动失败**
   ```bash
   # 检查服务状态
   systemctl status trading-system
   
   # 查看详细日志
   journalctl -u trading-system -n 100
   ```

2. **API连接失败**
   ```bash
   # 检查网络连接
   ping api.binance.com
   
   # 检查API密钥配置
   cat /opt/trading/.env
   ```

3. **内存使用过高**
   ```bash
   # 查看内存使用
   free -h
   
   # 查看进程内存
   ps aux --sort=-%mem | head -10
   ```

4. **磁盘空间不足**
   ```bash
   # 查看磁盘使用
   df -h
   
   # 清理日志文件
   find /opt/trading/logs -name "*.log" -mtime +30 -delete
   ```

### 调试模式

```bash
# 启用调试日志
export LOG_LEVEL=DEBUG

# 运行调试模式
python3 trading.py --debug
```

## 📞 技术支持

### 联系方式
- 邮箱: support@example.com
- Telegram: @trading_support
- 文档: [项目Wiki](https://github.com/example/trading-system/wiki)

### 问题反馈
1. 查看日志文件
2. 运行健康检查
3. 收集系统信息
4. 提交问题报告

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📈 更新日志

### v1.0.0 (2025-08-18)
- 初始版本发布
- 基础交易功能
- 系统监控
- 自动部署

---

**注意**: 本系统仅供学习和研究使用，实际交易请谨慎操作，投资有风险！ 