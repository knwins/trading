#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实盘交易系统 (trading.py)
基于回测验证的SharpeOptimizedStrategy策略
支持CentOS7自动运行
"""

import os
import sys
import time
import json
import logging
import asyncio
import signal
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# 第三方库导入
import pandas as pd
import numpy as np
import ccxt
import yfinance as yf
from dotenv import load_dotenv
import psutil
import requests

# 本地模块导入
from data_loader import DataLoader
from feature_engineer import FeatureEngineer
from strategy import SharpeOptimizedStrategy
from config import *

# 加载环境变量
load_dotenv()

class LiveTradingSystem:
    """
    实盘交易系统
    支持自动交易、风险管理和监控
    """
    
    def __init__(self, config: Dict = None):
        """初始化实盘交易系统"""
        self.config = config or self._load_config()
        self.running = False
        self.trading_enabled = False
        
        # 初始化组件
        self.data_loader = None
        self.feature_engineer = None
        self.strategy = None
        self.exchange = None
        
        # 交易状态
        self.current_position = 0  # 当前持仓
        self.last_signal = None    # 最后信号
        self.trade_history = []    # 交易历史
        
        # 风险管理
        self.max_position_size = self.config.get('max_position_size', 0.1)  # 最大仓位
        self.stop_loss_pct = self.config.get('stop_loss_pct', 0.05)         # 止损比例
        self.take_profit_pct = self.config.get('take_profit_pct', 0.1)      # 止盈比例
        
        # 设置日志
        self._setup_logging()
        
        # 初始化组件
        self._initialize_components()
        
    def _load_config(self) -> Dict:
        """加载配置"""
        config = {
            'symbol': TRADING_CONFIG['SYMBOL'],
            'timeframe': TRADING_CONFIG['TIMEFRAME'],
            'strategy_config': OPTIMIZED_STRATEGY_CONFIG,
            'risk_config': {
                'max_position_size': 0.1,      # 最大仓位10%
                'stop_loss_pct': 0.05,         # 止损5%
                'take_profit_pct': 0.1,        # 止盈10%
                'max_daily_loss': 0.02,        # 最大日损失2%
                'max_drawdown': 0.15,          # 最大回撤15%
            },
            'exchange_config': {
                'name': 'binance',
                'api_key': os.getenv('BINANCE_API_KEY'),
                'secret': os.getenv('BINANCE_SECRET'),
                'sandbox': True,  # 默认使用测试网
            },
            'notification_config': {
                'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
                'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
                'enable_notifications': True,
            }
        }
        return config
    
    def _setup_logging(self):
        """设置日志系统"""
        # 创建logs目录
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 配置日志格式
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # 创建文件处理器
        log_filename = f'logs/live_trading_{timestamp}.log'
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(log_format))
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        
        # 配置根日志记录器
        logging.basicConfig(
            level=logging.INFO,
            handlers=[file_handler, console_handler],
            format=log_format
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("🚀 实盘交易系统初始化完成")
    
    def _initialize_components(self):
        """初始化系统组件"""
        try:
            # 初始化数据加载器
            self.data_loader = DataLoader()
            self.logger.info("✅ 数据加载器初始化完成")
            
            # 初始化特征工程
            self.feature_engineer = FeatureEngineer()
            self.logger.info("✅ 特征工程初始化完成")
            
            # 初始化策略
            self.strategy = SharpeOptimizedStrategy(
                config=self.config['strategy_config'],
                data_loader=self.data_loader
            )
            self.logger.info("✅ 交易策略初始化完成")
            
            # 初始化交易所连接
            self._initialize_exchange()
            
        except Exception as e:
            self.logger.error(f"❌ 组件初始化失败: {str(e)}")
            raise
    
    def _initialize_exchange(self):
        """初始化交易所连接"""
        try:
            exchange_config = self.config['exchange_config']
            
            if exchange_config['name'] == 'binance':
                self.exchange = ccxt.binance({
                    'apiKey': exchange_config['api_key'],
                    'secret': exchange_config['secret'],
                    'sandbox': exchange_config['sandbox'],
                    'enableRateLimit': True,
                })
            
            # 测试连接
            self.exchange.load_markets()
            self.logger.info(f"✅ 交易所连接成功: {exchange_config['name']}")
            
        except Exception as e:
            self.logger.error(f"❌ 交易所连接失败: {str(e)}")
            self.exchange = None
    
    async def get_market_data(self) -> pd.DataFrame:
        """获取市场数据"""
        try:
            symbol = self.config['symbol']
            timeframe = self.config['timeframe']
            
            # 获取历史数据
            data = self.data_loader.get_timeframe_data(
                timeframe=timeframe,
                limit=1000
            )
            
            if data is None or data.empty:
                self.logger.warning("⚠️ 无法获取市场数据")
                return pd.DataFrame()
            
            return data
            
        except Exception as e:
            self.logger.error(f"❌ 获取市场数据失败: {str(e)}")
            return pd.DataFrame()
    
    async def generate_signals(self, data: pd.DataFrame) -> Dict:
        """生成交易信号"""
        try:
            if data.empty:
                return {'signal': 0, 'strength': 0, 'confidence': 0}
            
            # 特征工程
            features = self.feature_engineer.add_features(data)
            
            # 生成信号
            signal_result = self.strategy.generate_signal(features)
            
            return signal_result
            
        except Exception as e:
            self.logger.error(f"❌ 生成信号失败: {str(e)}")
            return {'signal': 0, 'strength': 0, 'confidence': 0}
    
    def check_risk_limits(self, signal: Dict) -> bool:
        """检查风险限制"""
        try:
            risk_config = self.config['risk_config']
            
            # 检查日损失限制
            daily_pnl = self._calculate_daily_pnl()
            if daily_pnl < -risk_config['max_daily_loss']:
                self.logger.warning(f"⚠️ 达到日损失限制: {daily_pnl:.2%}")
                return False
            
            # 检查回撤限制
            current_drawdown = self._calculate_drawdown()
            if current_drawdown > risk_config['max_drawdown']:
                self.logger.warning(f"⚠️ 达到最大回撤限制: {current_drawdown:.2%}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 风险检查失败: {str(e)}")
            return False
    
    def _calculate_daily_pnl(self) -> float:
        """计算当日盈亏"""
        try:
            today = datetime.now().date()
            today_trades = [trade for trade in self.trade_history 
                          if trade['date'].date() == today]
            
            if not today_trades:
                return 0.0
            
            total_pnl = sum(trade.get('pnl', 0) for trade in today_trades)
            return total_pnl
            
        except Exception as e:
            self.logger.error(f"❌ 计算日盈亏失败: {str(e)}")
            return 0.0
    
    def _calculate_drawdown(self) -> float:
        """计算当前回撤"""
        try:
            if not self.trade_history:
                return 0.0
            
            # 计算累计收益
            cumulative_returns = []
            total_return = 0.0
            
            for trade in self.trade_history:
                total_return += trade.get('pnl', 0)
                cumulative_returns.append(total_return)
            
            if not cumulative_returns:
                return 0.0
            
            # 计算回撤
            peak = max(cumulative_returns)
            current = cumulative_returns[-1]
            drawdown = (peak - current) / peak if peak > 0 else 0.0
            
            return drawdown
            
        except Exception as e:
            self.logger.error(f"❌ 计算回撤失败: {str(e)}")
            return 0.0
    
    async def execute_trade(self, signal: Dict):
        """执行交易"""
        try:
            if not self.trading_enabled or not self.exchange:
                return
            
            signal_value = signal.get('signal', 0)
            signal_strength = signal.get('strength', 0)
            
            # 检查风险限制
            if not self.check_risk_limits(signal):
                self.logger.info("🚫 交易被风险控制阻止")
                return
            
            # 确定交易方向
            if signal_value > 0.1 and signal_strength > 0.6:  # 买入信号
                await self._place_buy_order(signal)
            elif signal_value < -0.1 and signal_strength > 0.6:  # 卖出信号
                await self._place_sell_order(signal)
            else:
                self.logger.info("⏸️ 信号强度不足，不执行交易")
                
        except Exception as e:
            self.logger.error(f"❌ 执行交易失败: {str(e)}")
    
    async def _place_buy_order(self, signal: Dict):
        """下买单"""
        try:
            symbol = self.config['symbol']
            position_size = self.config['risk_config']['max_position_size']
            
            # 获取账户余额
            balance = await self.exchange.fetch_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            
            # 计算购买数量
            ticker = await self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            quantity = (usdt_balance * position_size) / current_price
            
            if quantity <= 0:
                self.logger.warning("⚠️ 余额不足，无法买入")
                return
            
            # 下订单
            order = await self.exchange.create_market_buy_order(
                symbol=symbol,
                amount=quantity
            )
            
            # 记录交易
            trade_record = {
                'date': datetime.now(),
                'type': 'BUY',
                'symbol': symbol,
                'quantity': quantity,
                'price': current_price,
                'signal': signal,
                'order_id': order['id']
            }
            
            self.trade_history.append(trade_record)
            self.current_position += quantity
            
            self.logger.info(f"✅ 买入成功: {quantity:.4f} {symbol} @ {current_price}")
            await self._send_notification(f"买入信号: {quantity:.4f} {symbol} @ {current_price}")
            
        except Exception as e:
            self.logger.error(f"❌ 买入失败: {str(e)}")
    
    async def _place_sell_order(self, signal: Dict):
        """下卖单"""
        try:
            symbol = self.config['symbol']
            
            if self.current_position <= 0:
                self.logger.warning("⚠️ 无持仓，无法卖出")
                return
            
            # 下订单
            order = await self.exchange.create_market_sell_order(
                symbol=symbol,
                amount=self.current_position
            )
            
            # 获取成交价格
            ticker = await self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # 计算盈亏
            last_buy = None
            for trade in reversed(self.trade_history):
                if trade['type'] == 'BUY':
                    last_buy = trade
                    break
            
            pnl = 0.0
            if last_buy:
                pnl = (current_price - last_buy['price']) * self.current_position
            
            # 记录交易
            trade_record = {
                'date': datetime.now(),
                'type': 'SELL',
                'symbol': symbol,
                'quantity': self.current_position,
                'price': current_price,
                'signal': signal,
                'order_id': order['id'],
                'pnl': pnl
            }
            
            self.trade_history.append(trade_record)
            self.current_position = 0
            
            self.logger.info(f"✅ 卖出成功: {trade_record['quantity']:.4f} {symbol} @ {current_price}, PnL: {pnl:.2f}")
            await self._send_notification(f"卖出信号: {trade_record['quantity']:.4f} {symbol} @ {current_price}, PnL: {pnl:.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ 卖出失败: {str(e)}")
    
    async def _send_notification(self, message: str):
        """发送通知"""
        try:
            notification_config = self.config['notification_config']
            
            if not notification_config['enable_notifications']:
                return
            
            # Telegram通知
            if notification_config['telegram_bot_token'] and notification_config['telegram_chat_id']:
                await self._send_telegram_notification(message)
                
        except Exception as e:
            self.logger.error(f"❌ 发送通知失败: {str(e)}")
    
    async def _send_telegram_notification(self, message: str):
        """发送Telegram通知"""
        try:
            import telegram
            
            bot_token = self.config['notification_config']['telegram_bot_token']
            chat_id = self.config['notification_config']['telegram_chat_id']
            
            bot = telegram.Bot(token=bot_token)
            await bot.send_message(chat_id=chat_id, text=message)
            
        except Exception as e:
            self.logger.error(f"❌ Telegram通知失败: {str(e)}")
    
    async def trading_loop(self):
        """主交易循环"""
        self.logger.info("🔄 开始交易循环")
        
        while self.running:
            try:
                # 获取市场数据
                data = await self.get_market_data()
                
                if data.empty:
                    self.logger.warning("⚠️ 无法获取市场数据，等待下次循环")
                    await asyncio.sleep(60)
                    continue
                
                # 生成信号
                signal = await self.generate_signals(data)
                
                # 记录信号
                self.logger.info(f"📊 当前信号: {signal}")
                
                # 检查信号变化
                if self.last_signal != signal:
                    self.logger.info(f"🔄 信号变化: {self.last_signal} -> {signal}")
                    self.last_signal = signal
                    
                    # 执行交易
                    await self.execute_trade(signal)
                
                # 等待下次循环
                await asyncio.sleep(60)  # 1分钟检查一次
                
            except Exception as e:
                self.logger.error(f"❌ 交易循环异常: {str(e)}")
                await asyncio.sleep(60)
    
    def start(self):
        """启动交易系统"""
        try:
            self.running = True
            self.trading_enabled = True
            
            self.logger.info("🚀 启动实盘交易系统")
            
            # 创建事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 运行交易循环
            loop.run_until_complete(self.trading_loop())
            
        except KeyboardInterrupt:
            self.logger.info("⏹️ 收到停止信号")
        except Exception as e:
            self.logger.error(f"❌ 系统运行异常: {str(e)}")
        finally:
            self.stop()
    
    def stop(self):
        """停止交易系统"""
        self.running = False
        self.trading_enabled = False
        self.logger.info("🛑 交易系统已停止")
    
    def get_status(self) -> Dict:
        """获取系统状态"""
        return {
            'running': self.running,
            'trading_enabled': self.trading_enabled,
            'current_position': self.current_position,
            'last_signal': self.last_signal,
            'trade_count': len(self.trade_history),
            'daily_pnl': self._calculate_daily_pnl(),
            'drawdown': self._calculate_drawdown(),
            'memory_usage': psutil.Process().memory_info().rss / 1024 / 1024  # MB
        }

def main():
    """主函数"""
    print("🚀 启动实盘交易系统...")
    
    # 创建交易系统
    trading_system = LiveTradingSystem()
    
    # 设置信号处理
    def signal_handler(signum, frame):
        print("\n⏹️ 收到停止信号，正在关闭系统...")
        trading_system.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 启动系统
        trading_system.start()
    except Exception as e:
        print(f"❌ 系统启动失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 