#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实盘交易系统测试脚本
用于测试系统的基本功能
"""

import os
import sys
import time
import logging
from datetime import datetime

# 设置环境变量（测试模式）
os.environ['BINANCE_API_KEY'] = 'test_key'
os.environ['BINANCE_API_SECRET'] = 'test_secret'

from realtime_trading_system import RealtimeTradingSystem

def test_system():
    """测试系统基本功能"""
    print("🧪 开始测试实盘交易系统...")
    
    try:
        # 创建交易系统
        trading_system = RealtimeTradingSystem()
        print("✅ 交易系统创建成功")
        
        # 测试数据获取
        print("📊 测试数据获取...")
        data = trading_system.get_realtime_data()
        if not data.empty:
            print(f"✅ 数据获取成功，数据点数量: {len(data)}")
            print(f"   最新价格: {data['close'].iloc[-1]:.2f}")
            print(f"   数据时间范围: {data.index[0]} 到 {data.index[-1]}")
        else:
            print("⚠️ 数据获取为空")
        
        # 测试信号生成
        if not data.empty:
            print("📈 测试信号生成...")
            signal, signal_info = trading_system.generate_signal(data)
            print(f"✅ 信号生成成功，信号: {signal}")
            if signal_info:
                print(f"   信号详情: {signal_info}")
        
        # 测试系统状态
        print("📊 测试系统状态...")
        trading_system.log_status(data['close'].iloc[-1] if not data.empty else 0, 0)
        print("✅ 系统状态记录成功")
        
        print("🎉 所有测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🚀 实盘交易系统测试")
    print("=" * 50)
    
    success = test_system()
    
    print("=" * 50)
    if success:
        print("✅ 测试完成，系统运行正常")
    else:
        print("❌ 测试失败，请检查系统配置")
    
    return success

if __name__ == "__main__":
    main() 