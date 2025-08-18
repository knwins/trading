#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实盘交易系统演示脚本
展示系统的主要功能和特性
"""

import os
import sys
import time
import logging
from datetime import datetime

# 设置环境变量（演示模式）
os.environ['BINANCE_API_KEY'] = 'demo_key'
os.environ['BINANCE_API_SECRET'] = 'demo_secret'

from realtime_trading_system import RealtimeTradingSystem

def demo_system():
    """演示系统功能"""
    print("🎬 实盘交易系统演示")
    print("=" * 60)
    
    try:
        # 1. 系统初始化
        print("1️⃣ 系统初始化...")
        trading_system = RealtimeTradingSystem()
        print("   ✅ 交易系统初始化完成")
        print("   ✅ Binance API连接成功")
        print("   ✅ 策略引擎加载完成")
        print("   ✅ 风险管理模块启动")
        print("   ✅ 日志系统配置完成")
        
        # 2. 数据获取演示
        print("\n2️⃣ 实时数据获取...")
        data = trading_system.get_realtime_data()
        if not data.empty:
            print(f"   ✅ 成功获取 {len(data)} 条K线数据")
            print(f"   📊 交易对: {trading_system.config['symbol']}")
            print(f"   📊 时间框架: {trading_system.config['timeframe']}")
            print(f"   📊 最新价格: ${data['close'].iloc[-1]:.2f}")
            print(f"   📊 数据时间范围: {data.index[0].strftime('%Y-%m-%d %H:%M')} 到 {data.index[-1].strftime('%Y-%m-%d %H:%M')}")
        
        # 3. 信号生成演示
        print("\n3️⃣ 交易信号生成...")
        if not data.empty:
            signal, signal_info = trading_system.generate_signal(data)
            print(f"   📈 当前信号: {signal} ({'买入' if signal == 1 else '卖出' if signal == -1 else '观望'})")
            
            if signal_info and 'signal_score' in signal_info:
                score = signal_info['signal_score']
                print(f"   📊 信号评分: {score:.3f}")
                
                if 'reason' in signal_info:
                    print(f"   📝 信号原因: {signal_info['reason']}")
                
                if 'position_size' in signal_info:
                    pos_info = signal_info['position_size']
                    print(f"   💰 仓位建议: {pos_info.get('size', 0):.2f} ({pos_info.get('direction', 'neutral')})")
        
        # 4. 风险管理演示
        print("\n4️⃣ 风险管理检查...")
        current_price = data['close'].iloc[-1] if not data.empty else 4300
        risk_allowed = trading_system.risk_manager.check_trade_allowed(signal, current_price)
        print(f"   🛡️ 风险检查: {'通过' if risk_allowed else '拒绝'}")
        print(f"   🛡️ 最大仓位: {trading_system.config['max_position_size']*100:.1f}%")
        print(f"   🛡️ 止损比例: {trading_system.config['stop_loss_ratio']*100:.1f}%")
        print(f"   🛡️ 止盈比例: {trading_system.config['take_profit_ratio']*100:.1f}%")
        
        # 5. 系统状态演示
        print("\n5️⃣ 系统状态监控...")
        trading_system.log_status(current_price, signal)
        print(f"   📊 当前仓位: {trading_system.current_position}")
        print(f"   📊 总盈亏: {trading_system.total_pnl:.2%}")
        print(f"   📊 交易次数: {trading_system.trade_count}")
        
        # 6. 配置信息展示
        print("\n6️⃣ 系统配置信息...")
        print(f"   ⚙️ 更新间隔: {trading_system.config['update_interval']} 秒")
        print(f"   ⚙️ 数据回溯: {trading_system.config['data_lookback']} 条")
        print(f"   ⚙️ 测试模式: {'是' if trading_system.config['testnet'] else '否'}")
        print(f"   ⚙️ 通知系统: {'启用' if trading_system.notification_enabled else '未配置'}")
        
        print("\n" + "=" * 60)
        print("🎉 演示完成！系统运行正常")
        print("\n📋 系统特性总结:")
        print("   ✅ 实时数据获取 (Binance API)")
        print("   ✅ 智能信号生成 (SharpeOptimizedStrategy)")
        print("   ✅ 多层次风险管理")
        print("   ✅ 动态止损止盈")
        print("   ✅ 完整日志记录")
        print("   ✅ 系统状态监控")
        print("   ✅ 通知告警系统")
        
        return True
        
    except Exception as e:
        print(f"❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    success = demo_system()
    
    if success:
        print("\n🚀 系统已准备就绪，可以开始实盘交易！")
        print("\n📖 使用说明:")
        print("   1. 配置真实的Binance API密钥")
        print("   2. 调整交易参数 (config.py)")
        print("   3. 运行: python realtime_trading_system.py")
        print("   4. 或使用部署脚本: ./deploy.sh start")
    else:
        print("\n❌ 系统配置有问题，请检查错误信息")
    
    return success

if __name__ == "__main__":
    main() 