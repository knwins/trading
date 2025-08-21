#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram通知测试工具

功能：
1. 测试Telegram Bot连接
2. 发送测试信号通知
3. 发送测试交易通知
4. 发送测试状态通知
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.telegram_notifier import TelegramNotifier, notify_signal, notify_trade, notify_status, notify_error
import time

def main():
    """主测试函数"""
    print("🚀 Telegram通知功能测试")
    print("=" * 50)
    
    # 创建通知器
    notifier = TelegramNotifier()
    
    if not notifier.enabled:
        print("❌ Telegram通知未配置")
        print("请设置以下环境变量：")
        print("  TELEGRAM_BOT_TOKEN=your_bot_token")
        print("  TELEGRAM_CHAT_ID=your_chat_id")
        print()
        print("或在config.py的TELEGRAM_CONFIG中设置：")
        print("  'BOT_TOKEN': 'your_bot_token'")
        print("  'CHAT_ID': 'your_chat_id'")
        return
    
    print(f"✅ Telegram通知器初始化成功")
    print(f"📱 Bot Token: {notifier.bot_token[:10]}...")
    print(f"💬 Chat ID: {notifier.chat_id}")
    print()
    
    # 测试1: 连接测试
    print("📡 测试1: 连接测试")
    success = notifier.test_connection()
    time.sleep(2)
    
    if not success:
        print("❌ 连接测试失败，请检查配置")
        return
    
    # 测试2: 信号通知
    print("\n📊 测试2: 交易信号通知")
    
    # 多头信号
    notify_signal(
        signal=1,
        price=4250.50,
        score=0.732,
        reason="RSI从超卖反弹，MACD金叉确认"
    )
    print("✅ 多头信号通知已发送")
    time.sleep(2)
    
    # 空头信号
    notify_signal(
        signal=-1,
        price=4230.75,
        score=-0.658,
        reason="价格跌破支撑位，成交量放大"
    )
    print("✅ 空头信号通知已发送")
    time.sleep(2)
    
    # 观望信号
    notify_signal(
        signal=0,
        price=4240.25,
        score=-0.043,
        reason="趋势不明确，等待进一步确认"
    )
    print("✅ 观望信号通知已发送")
    time.sleep(2)
    
    # 测试3: 交易通知
    print("\n💰 测试3: 交易执行通知")
    
    # 开仓通知
    notify_trade(
        action='open',
        side='long',
        price=4245.50,
        quantity=0.5
    )
    print("✅ 开仓通知已发送")
    time.sleep(2)
    
    # 平仓通知
    notify_trade(
        action='close',
        side='long',
        price=4280.75,
        quantity=0.5,
        pnl=17.63
    )
    print("✅ 平仓通知已发送")
    time.sleep(2)
    
    # 测试4: 状态通知
    print("\n📋 测试4: 状态通知")
    
    # 系统启动
    notify_status(
        status_type='start',
        title='交易系统启动',
        content='ETHUSDT交易系统已成功启动\n正在监控市场信号...'
    )
    print("✅ 启动通知已发送")
    time.sleep(2)
    
    # 警告通知
    notify_status(
        status_type='warning',
        title='网络延迟警告',
        content='检测到API响应时间较长\n当前延迟: 2.5秒'
    )
    print("✅ 警告通知已发送")
    time.sleep(2)
    
    # 测试5: 错误通知
    print("\n❌ 测试5: 错误通知")
    
    notify_error(
        error_msg="API连接失败",
        context="尝试获取市场数据时发生错误"
    )
    print("✅ 错误通知已发送")
    time.sleep(2)
    
    # 测试完成
    notify_status(
        status_type='success',
        title='通知测试完成',
        content='所有Telegram通知功能测试完成\n系统运行正常'
    )
    print("✅ 完成通知已发送")
    
    print("\n🎉 所有测试完成！")
    print("请检查您的Telegram聊天，确认收到了所有通知消息。")

if __name__ == "__main__":
    main()