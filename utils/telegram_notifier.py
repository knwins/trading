# -*- coding: utf-8 -*-
"""
Telegram通知模块

功能：
1. 发送交易信号通知
2. 发送交易执行结果通知
3. 发送系统状态通知
4. 发送错误警告通知
"""

import asyncio
import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import requests
import json
from config import TELEGRAM_CONFIG

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Telegram通知器"""
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        """初始化Telegram通知器"""
        self.bot_token = bot_token or TELEGRAM_CONFIG.get('BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or TELEGRAM_CONFIG.get('CHAT_ID') or os.getenv('TELEGRAM_CHAT_ID')
        
        self.enabled = bool(self.bot_token and self.chat_id)
        
        if not self.enabled:
            logger.warning("Telegram通知未配置：缺少BOT_TOKEN或CHAT_ID")
        else:
            logger.info("✅ Telegram通知器初始化成功")
    
    def _format_signal_message(self, signal_data: Dict[str, Any]) -> str:
        """格式化信号消息"""
        signal_type = signal_data.get('signal', 0)
        price = signal_data.get('price', 0)
        score = signal_data.get('score', 0)
        reason = signal_data.get('reason', '')
        
        # 信号图标
        if signal_type == 1:
            signal_icon = "🟢"
            signal_text = "多头信号"
        elif signal_type == -1:
            signal_icon = "🔴"
            signal_text = "空头信号"
        else:
            signal_icon = "⚪"
            signal_text = "观望信号"
        
        # 构建消息
        message = f"""
🚨 <b>ETHUSDT交易信号</b>

{signal_icon} <b>{signal_text}</b>
💰 当前价格: <code>${price:,.2f}</code>
📊 综合评分: <code>{score:.3f}</code>
🔍 信号原因: {reason}

🕐 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📊 时间框架: 1h
        """.strip()
        
        return message
    
    def _format_trade_message(self, trade_data: Dict[str, Any]) -> str:
        """格式化交易消息"""
        action = trade_data.get('action')  # 'open', 'close'
        side = trade_data.get('side')      # 'long', 'short'
        price = trade_data.get('price', 0)
        quantity = trade_data.get('quantity', 0)
        pnl = trade_data.get('pnl', 0)
        
        if action == 'open':
            action_icon = "📈" if side == 'long' else "📉"
            action_text = f"开仓 - {'做多' if side == 'long' else '做空'}"
        else:
            action_icon = "💰" if pnl > 0 else "💸"
            action_text = "平仓"
        
        message = f"""
{action_icon} <b>ETHUSDT交易执行</b>

🎯 操作: <b>{action_text}</b>
💰 价格: <code>${price:,.2f}</code>
📊 数量: <code>{quantity:.4f} ETH</code>
"""
        
        if action == 'close' and pnl is not None:
            pnl_icon = "📈" if pnl > 0 else "📉"
            message += f"{pnl_icon} 盈亏: <code>${pnl:,.2f}</code>\n"
        
        message += f"\n🕐 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return message.strip()
    
    def _format_status_message(self, status_data: Dict[str, Any]) -> str:
        """格式化状态消息"""
        status_type = status_data.get('type', 'info')
        title = status_data.get('title', '系统状态')
        content = status_data.get('content', '')
        
        # 状态图标
        status_icons = {
            'info': "ℹ️",
            'success': "✅", 
            'warning': "⚠️",
            'error': "❌",
            'start': "🚀",
            'stop': "⏹️"
        }
        
        icon = status_icons.get(status_type, "ℹ️")
        
        message = f"""
{icon} <b>{title}</b>

{content}

🕐 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """.strip()
        
        return message
    
    def send_message(self, message: str, parse_mode: str = 'HTML') -> bool:
        """发送消息到Telegram"""
        if not self.enabled:
            logger.debug("Telegram通知未启用")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Telegram消息发送成功")
                return True
            else:
                logger.error(f"❌ Telegram消息发送失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Telegram消息发送异常: {e}")
            return False
    
    def send_signal_notification(self, signal_data: Dict[str, Any]) -> bool:
        """发送交易信号通知"""
        if not self.enabled:
            return False
        
        message = self._format_signal_message(signal_data)
        return self.send_message(message)
    
    def send_trade_notification(self, trade_data: Dict[str, Any]) -> bool:
        """发送交易执行通知"""
        if not self.enabled:
            return False
        
        message = self._format_trade_message(trade_data)
        return self.send_message(message)
    
    def send_status_notification(self, status_data: Dict[str, Any]) -> bool:
        """发送状态通知"""
        if not self.enabled:
            return False
        
        message = self._format_status_message(status_data)
        return self.send_message(message)
    
    def send_error_notification(self, error_msg: str, context: str = "") -> bool:
        """发送错误通知"""
        if not self.enabled:
            return False
        
        status_data = {
            'type': 'error',
            'title': '系统错误',
            'content': f"错误信息: {error_msg}\n上下文: {context}" if context else error_msg
        }
        
        return self.send_status_notification(status_data)
    
    def test_connection(self) -> bool:
        """测试Telegram连接"""
        if not self.enabled:
            print("❌ Telegram通知未配置")
            return False
        
        test_message = """
🔧 <b>Telegram通知测试</b>

✅ 连接测试成功！
🚀 交易系统已准备就绪

🕐 测试时间: {time}
        """.format(time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')).strip()
        
        success = self.send_message(test_message)
        
        if success:
            print("✅ Telegram通知测试成功")
        else:
            print("❌ Telegram通知测试失败")
        
        return success

# 全局通知器实例
telegram_notifier = TelegramNotifier()

def notify_signal(signal: int, price: float, score: float, reason: str = "") -> bool:
    """快速发送信号通知"""
    # 观望信号不发送通知
    if signal == 0:
        return True
    
    signal_data = {
        'signal': signal,
        'price': price, 
        'score': score,
        'reason': reason
    }
    return telegram_notifier.send_signal_notification(signal_data)

def notify_trade(action: str, side: str, price: float, quantity: float, pnl: float = None) -> bool:
    """快速发送交易通知"""
    trade_data = {
        'action': action,
        'side': side,
        'price': price,
        'quantity': quantity,
        'pnl': pnl
    }
    return telegram_notifier.send_trade_notification(trade_data)

def notify_status(status_type: str, title: str, content: str) -> bool:
    """快速发送状态通知"""
    status_data = {
        'type': status_type,
        'title': title,
        'content': content
    }
    return telegram_notifier.send_status_notification(status_data)

def notify_error(error_msg: str, context: str = "") -> bool:
    """快速发送错误通知"""
    return telegram_notifier.send_error_notification(error_msg, context)

if __name__ == "__main__":
    # 测试Telegram通知
    notifier = TelegramNotifier()
    notifier.test_connection()