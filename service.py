#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易系统服务管理
支持CentOS7 systemd服务管理
"""

import os
import sys
import time
import json
import logging
import signal
import subprocess
import psutil
from datetime import datetime
from pathlib import Path

class TradingServiceManager:
    """交易系统服务管理器"""
    
    def __init__(self, service_name="trading-system"):
        self.service_name = service_name
        self.service_file = f"/etc/systemd/system/{service_name}.service"
        self.working_dir = os.getcwd()
        self.python_path = sys.executable
        self.main_script = os.path.join(self.working_dir, "trading.py")
        
        # 设置日志
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/service_manager.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def create_service_file(self):
        """创建systemd服务文件"""
        try:
            service_content = f"""[Unit]
Description=Trading System Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={self.working_dir}
ExecStart={self.python_path} {self.main_script}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
Environment=PYTHONPATH={self.working_dir}
Environment=PYTHONUNBUFFERED=1

# 资源限制
LimitNOFILE=65536
LimitNPROC=4096

# 安全设置
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths={self.working_dir}

[Install]
WantedBy=multi-user.target
"""
            
            # 写入服务文件
            with open(self.service_file, 'w', encoding='utf-8') as f:
                f.write(service_content)
            
            self.logger.info(f"✅ 服务文件创建成功: {self.service_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 创建服务文件失败: {str(e)}")
            return False
    
    def install_service(self):
        """安装服务"""
        try:
            # 创建服务文件
            if not self.create_service_file():
                return False
            
            # 重新加载systemd
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            self.logger.info("✅ systemd重新加载成功")
            
            # 启用服务
            subprocess.run(['systemctl', 'enable', self.service_name], check=True)
            self.logger.info(f"✅ 服务启用成功: {self.service_name}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ 安装服务失败: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"❌ 安装服务异常: {str(e)}")
            return False
    
    def uninstall_service(self):
        """卸载服务"""
        try:
            # 停止服务
            self.stop_service()
            
            # 禁用服务
            subprocess.run(['systemctl', 'disable', self.service_name], check=True)
            self.logger.info(f"✅ 服务禁用成功: {self.service_name}")
            
            # 删除服务文件
            if os.path.exists(self.service_file):
                os.remove(self.service_file)
                self.logger.info(f"✅ 服务文件删除成功: {self.service_file}")
            
            # 重新加载systemd
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            self.logger.info("✅ systemd重新加载成功")
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ 卸载服务失败: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"❌ 卸载服务异常: {str(e)}")
            return False
    
    def start_service(self):
        """启动服务"""
        try:
            subprocess.run(['systemctl', 'start', self.service_name], check=True)
            self.logger.info(f"✅ 服务启动成功: {self.service_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ 启动服务失败: {str(e)}")
            return False
    
    def stop_service(self):
        """停止服务"""
        try:
            subprocess.run(['systemctl', 'stop', self.service_name], check=True)
            self.logger.info(f"✅ 服务停止成功: {self.service_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ 停止服务失败: {str(e)}")
            return False
    
    def restart_service(self):
        """重启服务"""
        try:
            subprocess.run(['systemctl', 'restart', self.service_name], check=True)
            self.logger.info(f"✅ 服务重启成功: {self.service_name}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ 重启服务失败: {str(e)}")
            return False
    
    def get_service_status(self):
        """获取服务状态"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', self.service_name],
                capture_output=True,
                text=True,
                check=True
            )
            status = result.stdout.strip()
            self.logger.info(f"📊 服务状态: {status}")
            return status
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ 获取服务状态失败: {str(e)}")
            return "unknown"
    
    def get_service_logs(self, lines=50):
        """获取服务日志"""
        try:
            result = subprocess.run(
                ['journalctl', '-u', self.service_name, '-n', str(lines), '--no-pager'],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"❌ 获取服务日志失败: {str(e)}")
            return ""
    
    def check_dependencies(self):
        """检查依赖"""
        try:
            # 检查Python版本
            python_version = sys.version_info
            if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
                self.logger.error("❌ Python版本过低，需要Python 3.8+")
                return False
            
            # 检查必要文件
            required_files = [
                "trading.py",
                "config.py",
                "strategy.py",
                "data_loader.py",
                "feature_engineer.py"
            ]
            
            missing_files = []
            for file in required_files:
                if not os.path.exists(file):
                    missing_files.append(file)
            
            if missing_files:
                self.logger.error(f"❌ 缺少必要文件: {missing_files}")
                return False
            
            # 检查logs目录
            if not os.path.exists('logs'):
                os.makedirs('logs')
                self.logger.info("📁 创建logs目录")
            
            self.logger.info("✅ 依赖检查通过")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 依赖检查失败: {str(e)}")
            return False

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='交易系统服务管理')
    parser.add_argument('action', choices=['install', 'uninstall', 'start', 'stop', 'restart', 'status', 'logs', 'check'],
                       help='服务操作')
    parser.add_argument('--service-name', default='trading-system', help='服务名称')
    parser.add_argument('--lines', type=int, default=50, help='日志行数')
    
    args = parser.parse_args()
    
    # 创建服务管理器
    manager = TradingServiceManager(args.service_name)
    
    # 执行操作
    if args.action == 'install':
        if manager.check_dependencies():
            manager.install_service()
        else:
            print("❌ 依赖检查失败，无法安装服务")
            sys.exit(1)
    
    elif args.action == 'uninstall':
        manager.uninstall_service()
    
    elif args.action == 'start':
        manager.start_service()
    
    elif args.action == 'stop':
        manager.stop_service()
    
    elif args.action == 'restart':
        manager.restart_service()
    
    elif args.action == 'status':
        status = manager.get_service_status()
        print(f"服务状态: {status}")
    
    elif args.action == 'logs':
        logs = manager.get_service_logs(args.lines)
        print(logs)
    
    elif args.action == 'check':
        if manager.check_dependencies():
            print("✅ 依赖检查通过")
        else:
            print("❌ 依赖检查失败")
            sys.exit(1)

if __name__ == "__main__":
    main() 