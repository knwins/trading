# Telegram通知配置指南

## 📱 概述

本交易系统支持通过Telegram发送实时交易信号、交易执行结果和系统状态通知。

## 🚀 功能特性

- ✅ **交易信号通知** - 实时推送多头/空头/观望信号
- ✅ **交易执行通知** - 开仓/平仓操作提醒
- ✅ **系统状态通知** - 启动、停止、警告等状态
- ✅ **错误警报通知** - 系统异常和错误提醒
- ✅ **富文本格式** - 支持HTML格式，消息清晰易读

## 🔧 配置步骤

### 步骤1: 创建Telegram Bot

1. 在Telegram中搜索并添加 `@BotFather`
2. 发送 `/newbot` 命令开始创建机器人
3. 按提示输入机器人名称和用户名
4. 创建成功后，BotFather会提供一个**Bot Token**，保存此Token

示例：
```
123456789:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPQQ
```

### 步骤2: 获取Chat ID

1. 向您刚创建的机器人发送任意消息（如："Hello"）
2. 在浏览器中访问以下URL（替换YOUR_BOT_TOKEN）：
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
3. 在返回的JSON中找到 `chat.id` 字段，这就是您的**Chat ID**

示例JSON响应：
```json
{
  "result": [
    {
      "message": {
        "chat": {
          "id": 123456789,  // 这是您的Chat ID
          "username": "your_username"
        }
      }
    }
  ]
}
```

### 步骤3: 配置系统

有两种配置方式：

#### 方式1: 环境变量配置（推荐）

创建 `.env` 文件并添加：
```bash
TELEGRAM_BOT_TOKEN=123456789:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPQQ
TELEGRAM_CHAT_ID=123456789
```

#### 方式2: 直接修改配置文件

编辑 `config.py` 文件，在 `TELEGRAM_CONFIG` 中设置：
```python
TELEGRAM_CONFIG = {
    'BOT_TOKEN': '123456789:AABBCCDDEEFFGGHHIIJJKKLLMMNNOOPPQQ',
    'CHAT_ID': '123456789',
    'ENABLED': True,
    # ... 其他配置
}
```

## 🧪 测试配置

配置完成后，运行测试脚本验证：

```bash
python tools/test_telegram.py
```

成功的测试结果示例：
```
🚀 Telegram通知功能测试
==================================================
✅ Telegram通知器初始化成功
📱 Bot Token: 123456789:...
💬 Chat ID: 123456789

📡 测试1: 连接测试
✅ Telegram通知测试成功
✅ 多头信号通知已发送
✅ 空头信号通知已发送
...
🎉 所有测试完成！
```

## 📊 通知消息示例

### 交易信号通知

```
🚨 ETHUSDT交易信号

🟢 多头信号
💰 当前价格: $4,250.50
📊 综合评分: 0.732
🔍 信号原因: RSI从超卖反弹，MACD金叉确认

🕐 时间: 2025-08-21 14:30:15
📊 时间框架: 1h
```

### 交易执行通知

```
📈 ETHUSDT交易执行

🎯 操作: 开仓 - 做多
💰 价格: $4,245.50
📊 数量: 0.5000 ETH

🕐 时间: 2025-08-21 14:30:20
```

### 系统状态通知

```
🚀 交易系统启动

ETHUSDT交易系统已成功启动
正在监控市场信号...

🕐 时间: 2025-08-21 14:00:00
```

## 🔧 自定义配置

### 通知类型控制

在 `config.py` 中可以控制不同类型的通知：

```python
TELEGRAM_CONFIG = {
    'NOTIFICATION_TYPES': {
        'SIGNALS': True,    # 交易信号通知
        'TRADES': True,     # 交易执行通知
        'ERRORS': True,     # 错误通知
        'STATUS': False,    # 状态通知（可关闭）
    }
}
```

### 消息格式设置

```python
TELEGRAM_CONFIG = {
    'MESSAGE_FORMAT': {
        'PARSE_MODE': 'HTML',           # HTML 或 Markdown
        'DISABLE_WEB_PREVIEW': True,    # 禁用网页预览
    }
}
```

## 🛠️ 程序集成

在您的交易逻辑中使用Telegram通知：

```python
from utils.telegram_notifier import notify_signal, notify_trade, notify_error

# 发送交易信号通知
notify_signal(
    signal=1,           # 1=多头, -1=空头, 0=观望
    price=4250.50,      # 当前价格
    score=0.732,        # 信号评分
    reason="技术指标确认多头趋势"
)

# 发送交易执行通知
notify_trade(
    action='open',      # 'open' 或 'close'
    side='long',        # 'long' 或 'short'
    price=4245.50,      # 执行价格
    quantity=0.5,       # 交易数量
    pnl=17.63          # 盈亏（平仓时）
)

# 发送错误通知
notify_error(
    error_msg="API连接失败",
    context="获取市场数据时发生错误"
)
```

## 🔒 安全注意事项

1. **保护Bot Token** - 不要将Bot Token提交到代码仓库
2. **使用环境变量** - 建议使用 `.env` 文件存储敏感信息
3. **限制机器人权限** - 只向信任的人员提供Chat ID
4. **定期更新Token** - 定期重新生成Bot Token确保安全

## ❓ 常见问题

### Q: 收不到通知消息怎么办？

1. 检查Bot Token和Chat ID是否正确
2. 确认已向机器人发送过消息（激活对话）
3. 检查机器人是否被用户屏蔽
4. 运行测试脚本确认配置

### Q: 如何获取群组的Chat ID？

1. 将机器人添加到群组
2. 在群组中发送消息提及机器人（@your_bot_name）
3. 访问getUpdates API查看群组的Chat ID（通常是负数）

### Q: 消息格式乱码怎么办？

确保所有Python文件都使用UTF-8编码，并在消息中使用HTML格式。

### Q: 如何禁用某些类型的通知？

在 `config.py` 的 `TELEGRAM_CONFIG` 中设置对应的通知类型为 `False`。

---

📞 **技术支持**: 如有问题，请查看项目文档或提交Issue。