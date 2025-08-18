#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实盘交易系统 - OSCent服务
基于回测验证的SharpeOptimizedStrategy策略

功能模块：
1. 实时数据获取 (Binance API)
2. 信号生成 (SharpeOptimizedStrategy)
3. 风险管理 (动态止损止盈)
4. 交易执行 (Binance API)
5. 监控告警 (Telegram/邮件)
6. 日志记录 (结构化日志)
"""

import os
import sys
import time
import json
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException
import telegram

# 导入策略模块
from strategy import SharpeOptimizedStrategy
from feature_engineer import FeatureEngineer
from data_loader import DataLoader
from config import *

class RealtimeTradingSystem:
    """实盘交易系统主类"""
    
    def __init__(self, config: Dict = None):
        """初始化交易系统"""
        self.config = config or self._load_config()
        self.setup_logging()
        self.setup_exchange()
        self.setup_strategy()
        self.setup_risk_management()
        self.setup_notifications()
        
        # 状态变量
        self.is_running = False
        self.current_position = 0  # 0=无仓位, 1=多头, -1=空头
        self.entry_price = 0.0
        self.entry_time = None
        self.position_size = 0.0
        self.total_pnl = 0.0
        self.trade_count = 0
        
        # 数据缓存
        self.kline_data = pd.DataFrame()
        self.last_signal = 0
        self.last_signal_time = None
        
        self.logger.info("🚀 实盘交易系统初始化完成")
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        config = {
            # 交易配置
            'symbol': TRADING_CONFIG['SYMBOL'],
            'timeframe': TRADING_CONFIG['TIMEFRAME'],
            'base_quantity': 0.01,  # 基础交易量
            
            # API配置
            'api_key': os.getenv('BINANCE_API_KEY', ''),
            'api_secret': os.getenv('BINANCE_API_SECRET', ''),
            'testnet': True,  # 使用测试网
            
            # 策略配置
            'strategy_config': OPTIMIZED_STRATEGY_CONFIG,
            
            # 风险管理配置
            'max_position_size': 0.1,  # 最大仓位比例
            'stop_loss_ratio': 0.02,   # 止损比例
            'take_profit_ratio': 0.04, # 止盈比例
            'max_daily_loss': 0.05,    # 最大日亏损
            
            # 通知配置
            'telegram_token': os.getenv('TELEGRAM_TOKEN', ''),
            'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),
            
            # 系统配置
            'update_interval': 60,     # 更新间隔(秒)
            'data_lookback': 1000,     # 历史数据长度
        }
        return config
    
    def setup_logging(self):
        """设置日志系统"""
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        
        # 创建日志文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f'{log_dir}/realtime_trading_{timestamp}.log'
        
        # 配置日志格式
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"📝 日志系统初始化完成: {log_file}")
    
    def setup_exchange(self):
        """设置交易所连接"""
        try:
            self.client = Client(
                self.config['api_key'],
                self.config['api_secret'],
                testnet=self.config['testnet']
            )
            
            # 测试连接
            server_time = self.client.get_server_time()
            self.logger.info(f"✅ Binance连接成功，服务器时间: {datetime.fromtimestamp(server_time['serverTime']/1000)}")
            
        except Exception as e:
            self.logger.error(f"❌ Binance连接失败: {e}")
            raise
    
    def setup_strategy(self):
        """设置策略"""
        try:
            # 初始化特征工程
            self.feature_engineer = FeatureEngineer()
            
            # 初始化策略
            self.strategy = SharpeOptimizedStrategy(
                config=self.config['strategy_config'],
                data_loader=None
            )
            
            self.logger.info("✅ 策略初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 策略初始化失败: {e}")
            raise
    
    def setup_risk_management(self):
        """设置风险管理"""
        self.risk_manager = RiskManager(
            max_position_size=self.config['max_position_size'],
            stop_loss_ratio=self.config['stop_loss_ratio'],
            take_profit_ratio=self.config['take_profit_ratio'],
            max_daily_loss=self.config['max_daily_loss']
        )
        self.logger.info("✅ 风险管理初始化完成")
    
    def setup_notifications(self):
        """设置通知系统"""
        if self.config['telegram_token'] and self.config['telegram_chat_id']:
            try:
                self.bot = telegram.Bot(token=self.config['telegram_token'])
                self.notification_enabled = True
                self.logger.info("✅ Telegram通知初始化完成")
            except Exception as e:
                self.logger.warning(f"⚠️ Telegram通知初始化失败: {e}")
                self.notification_enabled = False
        else:
            self.notification_enabled = False
            self.logger.info("ℹ️ 通知系统未配置")
    
    def get_realtime_data(self) -> pd.DataFrame:
        """获取实时K线数据"""
        try:
            # 获取K线数据
            klines = self.client.get_klines(
                symbol=self.config['symbol'],
                interval=self.config['timeframe'],
                limit=self.config['data_lookback']
            )
            
            # 转换为DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 数据类型转换
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 时间戳转换
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ 获取实时数据失败: {e}")
            return pd.DataFrame()
    
    def generate_signal(self, data: pd.DataFrame) -> Tuple[int, Dict]:
        """生成交易信号"""
        try:
            if len(data) < 100:
                return 0, {}
            
            # 特征工程
            features = self.feature_engineer.add_features(data.copy())
            
            # 生成信号
            signal_info = self.strategy.generate_signal(features)
            
            return signal_info.get('signal', 0), signal_info
            
        except Exception as e:
            self.logger.error(f"❌ 信号生成失败: {e}")
            return 0, {}
    
    def execute_trade(self, signal: int, current_price: float) -> bool:
        """执行交易"""
        try:
            if signal == 0:
                return True
            
            # 检查风险管理
            if not self.risk_manager.check_trade_allowed(signal, current_price):
                self.logger.warning("⚠️ 交易被风险管理阻止")
                return False
            
            # 计算交易量
            quantity = self.calculate_position_size(signal, current_price)
            
            # 执行订单
            if signal == 1:  # 买入
                order = self.client.create_order(
                    symbol=self.config['symbol'],
                    side=Client.SIDE_BUY,
                    type=Client.ORDER_TYPE_MARKET,
                    quantity=quantity
                )
                self.current_position = 1
                self.entry_price = current_price
                self.entry_time = datetime.now()
                self.position_size = quantity
                
            elif signal == -1:  # 卖出
                order = self.client.create_order(
                    symbol=self.config['symbol'],
                    side=Client.SIDE_SELL,
                    type=Client.ORDER_TYPE_MARKET,
                    quantity=quantity
                )
                self.current_position = -1
                self.entry_price = current_price
                self.entry_time = datetime.now()
                self.position_size = quantity
            
            # 记录交易
            self.record_trade(signal, current_price, quantity, order)
            
            # 发送通知
            self.send_notification(f"🔄 执行交易: {'买入' if signal == 1 else '卖出'} {quantity} {self.config['symbol']} @ {current_price}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 交易执行失败: {e}")
            return False
    
    def calculate_position_size(self, signal: int, current_price: float) -> float:
        """计算仓位大小"""
        try:
            # 获取账户余额
            account = self.client.get_account()
            balance = float([asset for asset in account['balances'] 
                           if asset['asset'] == 'USDT'][0]['free'])
            
            # 计算可用资金
            available_balance = balance * self.config['max_position_size']
            
            # 计算数量
            quantity = available_balance / current_price
            
            # 四舍五入到合适的小数位
            quantity = round(quantity, 4)
            
            return quantity
            
        except Exception as e:
            self.logger.error(f"❌ 计算仓位大小失败: {e}")
            return self.config['base_quantity']
    
    def check_exit_conditions(self, current_price: float) -> bool:
        """检查退出条件"""
        if self.current_position == 0:
            return False
        
        # 计算盈亏比例
        if self.current_position == 1:  # 多头
            pnl_ratio = (current_price - self.entry_price) / self.entry_price
        else:  # 空头
            pnl_ratio = (self.entry_price - current_price) / self.entry_price
        
        # 检查止损止盈
        if pnl_ratio <= -self.config['stop_loss_ratio']:
            self.logger.info(f"🛑 触发止损: {pnl_ratio:.2%}")
            return self.close_position(current_price, "止损")
        
        elif pnl_ratio >= self.config['take_profit_ratio']:
            self.logger.info(f"🎯 触发止盈: {pnl_ratio:.2%}")
            return self.close_position(current_price, "止盈")
        
        return False
    
    def close_position(self, current_price: float, reason: str) -> bool:
        """平仓"""
        try:
            if self.current_position == 0:
                return True
            
            # 计算盈亏
            if self.current_position == 1:  # 多头
                pnl_ratio = (current_price - self.entry_price) / self.entry_price
                side = Client.SIDE_SELL
            else:  # 空头
                pnl_ratio = (self.entry_price - current_price) / self.entry_price
                side = Client.SIDE_BUY
            
            # 执行平仓
            order = self.client.create_order(
                symbol=self.config['symbol'],
                side=side,
                type=Client.ORDER_TYPE_MARKET,
                quantity=self.position_size
            )
            
            # 更新状态
            self.total_pnl += pnl_ratio
            self.trade_count += 1
            self.current_position = 0
            self.entry_price = 0.0
            self.entry_time = None
            self.position_size = 0.0
            
            # 记录交易
            self.record_trade(0, current_price, self.position_size, order, reason)
            
            # 发送通知
            self.send_notification(f"💰 平仓({reason}): 盈亏 {pnl_ratio:.2%}, 总盈亏 {self.total_pnl:.2%}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 平仓失败: {e}")
            return False
    
    def record_trade(self, signal: int, price: float, quantity: float, order: Dict, reason: str = ""):
        """记录交易"""
        trade_record = {
            'timestamp': datetime.now(),
            'signal': signal,
            'price': price,
            'quantity': quantity,
            'order_id': order.get('orderId', ''),
            'reason': reason,
            'position': self.current_position,
            'total_pnl': self.total_pnl
        }
        
        # 保存到文件
        with open('trade_history.json', 'a', encoding='utf-8') as f:
            f.write(json.dumps(trade_record, default=str, ensure_ascii=False) + '\n')
    
    def send_notification(self, message: str):
        """发送通知"""
        if not self.notification_enabled:
            return
        
        try:
            self.bot.send_message(
                chat_id=self.config['telegram_chat_id'],
                text=f"[实盘交易系统] {message}"
            )
        except Exception as e:
            self.logger.error(f"❌ 发送通知失败: {e}")
    
    def run(self):
        """运行交易系统"""
        self.is_running = True
        self.logger.info("🚀 开始运行实盘交易系统")
        
        try:
            while self.is_running:
                try:
                    # 获取实时数据
                    data = self.get_realtime_data()
                    if data.empty:
                        self.logger.warning("⚠️ 获取数据为空，跳过本次循环")
                        time.sleep(self.config['update_interval'])
                        continue
                    
                    # 更新数据缓存
                    self.kline_data = data
                    current_price = float(data['close'].iloc[-1])
                    
                    # 检查退出条件
                    if self.check_exit_conditions(current_price):
                        continue
                    
                    # 生成信号
                    signal, signal_info = self.generate_signal(data)
                    
                    # 检查新信号
                    if signal != 0 and signal != self.last_signal:
                        self.logger.info(f"📊 新信号: {signal}, 价格: {current_price}")
                        
                        # 执行交易
                        if self.execute_trade(signal, current_price):
                            self.last_signal = signal
                            self.last_signal_time = datetime.now()
                    
                    # 记录状态
                    self.log_status(current_price, signal)
                    
                    # 等待下次更新
                    time.sleep(self.config['update_interval'])
                    
                except KeyboardInterrupt:
                    self.logger.info("🛑 收到中断信号，正在停止...")
                    break
                except Exception as e:
                    self.logger.error(f"❌ 运行循环异常: {e}")
                    time.sleep(self.config['update_interval'])
        
        finally:
            self.stop()
    
    def log_status(self, current_price: float, signal: int):
        """记录系统状态"""
        status = {
            'timestamp': datetime.now(),
            'price': current_price,
            'signal': signal,
            'position': self.current_position,
            'entry_price': self.entry_price,
            'position_size': self.position_size,
            'total_pnl': self.total_pnl,
            'trade_count': self.trade_count
        }
        
        self.logger.info(f"📈 状态更新: 价格={current_price:.2f}, 信号={signal}, 仓位={self.current_position}, 总盈亏={self.total_pnl:.2%}")
    
    def stop(self):
        """停止交易系统"""
        self.is_running = False
        self.logger.info("🛑 实盘交易系统已停止")


class RiskManager:
    """风险管理器"""
    
    def __init__(self, max_position_size: float, stop_loss_ratio: float, 
                 take_profit_ratio: float, max_daily_loss: float):
        self.max_position_size = max_position_size
        self.stop_loss_ratio = stop_loss_ratio
        self.take_profit_ratio = take_profit_ratio
        self.max_daily_loss = max_daily_loss
        self.daily_pnl = 0.0
        self.last_reset_date = datetime.now().date()
    
    def check_trade_allowed(self, signal: int, current_price: float) -> bool:
        """检查是否允许交易"""
        # 检查日亏损限制
        if self.daily_pnl <= -self.max_daily_loss:
            return False
        
        # 检查日期重置
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_pnl = 0.0
            self.last_reset_date = current_date
        
        return True
    
    def update_daily_pnl(self, pnl_ratio: float):
        """更新日盈亏"""
        self.daily_pnl += pnl_ratio


def main():
    """主函数"""
    # 创建交易系统
    trading_system = RealtimeTradingSystem()
    
    # 运行系统
    trading_system.run()


if __name__ == "__main__":
    main() 