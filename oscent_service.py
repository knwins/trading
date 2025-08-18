#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSCent服务配置
实盘交易系统服务化部署

使用方法：
1. 将此文件放在OSCent服务目录中
2. 配置环境变量
3. 启动服务: python oscent_service.py
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from realtime_trading_system import RealtimeTradingSystem

class OSCentService:
    """OSCent服务类"""
    
    def __init__(self):
        """初始化服务"""
        self.trading_system = None
        self.is_running = False
        self.setup_logging()
        self.setup_signal_handlers()
        
    def setup_logging(self):
        """设置日志"""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f'oscent_service_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"🚀 OSCent服务启动，日志文件: {log_file}")
    
    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """信号处理"""
        self.logger.info(f"📡 收到信号 {signum}，正在停止服务...")
        self.stop()
    
    def check_environment(self):
        """检查环境配置"""
        required_vars = [
            'BINANCE_API_KEY',
            'BINANCE_API_SECRET'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.logger.error(f"❌ 缺少必需的环境变量: {missing_vars}")
            return False
        
        self.logger.info("✅ 环境配置检查通过")
        return True
    
    def start(self):
        """启动服务"""
        if not self.check_environment():
            self.logger.error("❌ 环境配置检查失败，服务启动终止")
            return False
        
        try:
            self.logger.info("🚀 正在启动实盘交易系统...")
            
            # 创建交易系统
            self.trading_system = RealtimeTradingSystem()
            
            # 启动交易系统
            self.is_running = True
            self.trading_system.run()
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 服务启动失败: {e}")
            return False
    
    def stop(self):
        """停止服务"""
        self.is_running = False
        
        if self.trading_system:
            self.trading_system.stop()
        
        self.logger.info("🛑 OSCent服务已停止")
    
    def run(self):
        """运行服务"""
        if self.start():
            self.logger.info("✅ 服务启动成功")
            
            # 保持服务运行
            try:
                while self.is_running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("🛑 收到键盘中断信号")
            finally:
                self.stop()
        else:
            self.logger.error("❌ 服务启动失败")
            sys.exit(1)


def main():
    """主函数"""
    service = OSCentService()
    service.run()


if __name__ == "__main__":
    main() 