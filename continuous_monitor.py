# -*- coding: utf-8 -*-
"""
持续监控实时信号工具
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import warnings
from data_loader import DataLoader
from feature_engineer import FeatureEngineer
from strategy import SharpeOptimizedStrategy
from config import *

warnings.filterwarnings('ignore')

class SignalMonitor:
    def __init__(self):
        self.data_loader = DataLoader()
        self.feature_engineer = FeatureEngineer()
        from config import OPTIMIZED_STRATEGY_CONFIG
        self.strategy = SharpeOptimizedStrategy(config=OPTIMIZED_STRATEGY_CONFIG, data_loader=self.data_loader)
        self.signal_history = []
        self.last_signal = None
        
    def get_current_signal(self):
        """获取当前信号"""
        try:
            # 获取最近数据
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)
            
            start_date_str = start_time.strftime("%Y-%m-%d")
            end_date_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # 获取K线数据
            data = self.data_loader.get_klines(start_date_str, end_date_str)
            
            if data is None or data.empty:
                return None, None
            
            # 特征工程
            features = self.feature_engineer.generate_features(data)
            
            if features is None or features.empty:
                return None, None
            
            # 计算信号
            signal_info = self.strategy._calculate_signal(features, verbose=False)
            
            return signal_info, features.iloc[-1]
            
        except Exception as e:
            print(f"❌ 获取信号失败: {e}")
            return None, None
    
    def display_signal(self, signal_info, current_data, iteration):
        """显示信号信息"""
        if not signal_info:
            return
        
        current_time = datetime.now()
        current_price = current_data.get('close', 0)
        signal = signal_info.get('signal', 0)
        
        # 信号类型
        signal_type = "🟢 多头" if signal == 1 else "🔴 空头" if signal == -1 else "⚪ 观望"
        
        # 检查信号变化
        signal_change = ""
        if self.last_signal is not None and self.last_signal != signal:
            signal_change = f" 🔄 信号变化!"
        
        # 显示基本信息
        print(f"\n[{current_time.strftime('%H:%M:%S')}] 第{iteration}次检查 {signal_change}")
        print(f"💰 价格: {current_price:.2f} | 🎯 信号: {signal_type}")
        print(f"📊 评分: {signal_info.get('signal_score', 0):.3f} | 基础: {signal_info.get('base_score', 0):.3f} | 趋势: {signal_info.get('trend_score', 0):.3f}")
        
        # 显示过滤器状态
        filters = signal_info.get('filters', {})
        if filters:
            signal_filter = filters.get('signal_filter', {})
            if not signal_filter.get('passed', True):
                print(f"🔍 过滤: {signal_filter.get('reason', 'N/A')}")
        
        # 记录信号历史
        self.signal_history.append({
            'timestamp': current_time,
            'signal': signal,
            'price': current_price,
            'signal_score': signal_info.get('signal_score', 0),
            'reason': signal_info.get('reason', 'N/A')
        })
        
        # 保持最近50条记录
        if len(self.signal_history) > 50:
            self.signal_history = self.signal_history[-50:]
        
        self.last_signal = signal
    
    def print_summary(self):
        """打印摘要"""
        if not self.signal_history:
            return
        
        print("\n" + "="*60)
        print("📊 监控摘要")
        print("="*60)
        
        # 信号分布
        signals = [record['signal'] for record in self.signal_history]
        long_count = signals.count(1)
        short_count = signals.count(-1)
        neutral_count = signals.count(0)
        total = len(signals)
        
        print(f"📈 信号分布: 多头{long_count} | 空头{short_count} | 观望{neutral_count} | 总计{total}")
        
        # 价格变化
        if len(self.signal_history) > 1:
            first_price = self.signal_history[0]['price']
            last_price = self.signal_history[-1]['price']
            change = (last_price - first_price) / first_price * 100
            print(f"💰 价格变化: {change:+.2f}% ({first_price:.2f} → {last_price:.2f})")
        
        # 最新信号
        latest = self.signal_history[-1]
        print(f"🕐 最新信号: {latest['timestamp'].strftime('%H:%M:%S')} | {latest['signal']} | {latest['signal_score']:.3f}")
        
        print("="*60)

def main():
    """主函数"""
    print("🚀 持续信号监控工具")
    print(f"📊 交易对: {TRADING_CONFIG['SYMBOL']}")
    print(f"🕐 时间级别: {TRADING_CONFIG['TIMEFRAME']}")
    print("="*60)
    
    monitor = SignalMonitor()
    
    try:
        interval = 60  # 60秒间隔
        iteration = 0
        
        while True:
            iteration += 1
            
            # 获取信号
            signal_info, current_data = monitor.get_current_signal()
            
            if signal_info:
                monitor.display_signal(signal_info, current_data, iteration)
            else:
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 第{iteration}次检查 - ❌ 无法获取信号")
            
            # 每10次检查显示一次摘要
            if iteration % 10 == 0:
                monitor.print_summary()
            
            # 等待下次检查
            print(f"⏳ 等待 {interval} 秒...")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断监控")
        monitor.print_summary()
    except Exception as e:
        print(f"\n❌ 监控异常: {e}")
        monitor.print_summary()

if __name__ == "__main__":
    main() 