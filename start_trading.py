#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实盘交易系统启动脚本
一键启动交易系统
"""

import os
import sys
import time
from datetime import datetime

def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("❌ Python版本过低，需要3.8+")
        return False
    
    # 检查必需的环境变量
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        print("⚠️ 未设置Binance API密钥")
        print("请设置环境变量:")
        print("export BINANCE_API_KEY='your_api_key'")
        print("export BINANCE_API_SECRET='your_api_secret'")
        return False
    
    print("✅ 环境配置检查通过")
    return True

def install_dependencies():
    """安装依赖包"""
    print("📦 检查依赖包...")
    
    try:
        import binance
        import psutil
        import telegram
        import pandas
        import numpy
        print("✅ 依赖包已安装")
        return True
    except ImportError as e:
        print(f"❌ 缺少依赖包: {e}")
        print("正在安装依赖包...")
        
        try:
            os.system("pip install python-binance psutil python-telegram-bot pandas numpy")
            print("✅ 依赖包安装完成")
            return True
        except Exception as e:
            print(f"❌ 依赖包安装失败: {e}")
            return False

def start_system():
    """启动交易系统"""
    print("🚀 启动实盘交易系统...")
    
    try:
        # 导入并启动系统
        from realtime_trading_system import RealtimeTradingSystem
        
        # 创建交易系统
        trading_system = RealtimeTradingSystem()
        
        # 启动系统
        trading_system.run()
        
    except KeyboardInterrupt:
        print("\n🛑 用户中断，正在停止系统...")
    except Exception as e:
        print(f"❌ 系统启动失败: {e}")
        return False
    
    return True

def main():
    """主函数"""
    print("=" * 50)
    print("🚀 实盘交易系统启动器")
    print("=" * 50)
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 检查环境
    if not check_environment():
        print("\n❌ 环境检查失败，请检查配置")
        return False
    
    # 安装依赖
    if not install_dependencies():
        print("\n❌ 依赖包安装失败")
        return False
    
    print("\n✅ 所有检查通过，开始启动系统...")
    print("=" * 50)
    
    # 启动系统
    success = start_system()
    
    if success:
        print("\n✅ 系统运行完成")
    else:
        print("\n❌ 系统运行失败")
    
    return success

if __name__ == "__main__":
    main() 