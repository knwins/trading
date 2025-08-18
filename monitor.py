#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交易系统监控模块
实时监控系统状态、性能和健康度
"""

import os
import sys
import time
import json
import logging
import asyncio
import psutil
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.running = False
        self.metrics = {}
        self.alerts = []
        
        # 监控配置
        self.monitor_interval = self.config.get('monitor_interval', 30)  # 监控间隔(秒)
        self.alert_thresholds = self.config.get('alert_thresholds', {
            'cpu_usage': 80.0,      # CPU使用率阈值
            'memory_usage': 85.0,   # 内存使用率阈值
            'disk_usage': 90.0,     # 磁盘使用率阈值
            'network_latency': 1000, # 网络延迟阈值(ms)
            'api_error_rate': 0.1,   # API错误率阈值
        })
        
        # 设置日志
        self._setup_logging()
        
        # 初始化监控数据
        self._initialize_metrics()
    
    def _setup_logging(self):
        """设置日志"""
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/monitor.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _initialize_metrics(self):
        """初始化监控指标"""
        self.metrics = {
            'system': {
                'cpu_usage': 0.0,
                'memory_usage': 0.0,
                'disk_usage': 0.0,
                'network_io': {'bytes_sent': 0, 'bytes_recv': 0},
                'load_average': [0.0, 0.0, 0.0],
            },
            'trading': {
                'signal_count': 0,
                'trade_count': 0,
                'error_count': 0,
                'last_signal_time': None,
                'last_trade_time': None,
            },
            'network': {
                'api_latency': 0.0,
                'api_error_rate': 0.0,
                'connection_status': 'unknown',
            },
            'performance': {
                'response_time': 0.0,
                'throughput': 0.0,
                'memory_leak': False,
            }
        }
    
    def get_system_metrics(self) -> Dict:
        """获取系统指标"""
        try:
            # CPU使用率
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            
            # 网络IO
            network_io = psutil.net_io_counters()
            
            # 负载平均值
            load_avg = psutil.getloadavg()
            
            return {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'disk_usage': disk_usage,
                'network_io': {
                    'bytes_sent': network_io.bytes_sent,
                    'bytes_recv': network_io.bytes_recv
                },
                'load_average': list(load_avg),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取系统指标失败: {str(e)}")
            return {}
    
    def get_trading_metrics(self) -> Dict:
        """获取交易指标"""
        try:
            # 从日志文件读取交易信息
            trading_metrics = {
                'signal_count': 0,
                'trade_count': 0,
                'error_count': 0,
                'last_signal_time': None,
                'last_trade_time': None,
            }
            
            # 读取最新的交易日志
            log_files = [f for f in os.listdir('logs') if f.startswith('live_trading_')]
            if log_files:
                latest_log = max(log_files, key=lambda x: os.path.getctime(os.path.join('logs', x)))
                log_path = os.path.join('logs', latest_log)
                
                with open(log_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines:
                        if '信号' in line:
                            trading_metrics['signal_count'] += 1
                            trading_metrics['last_signal_time'] = datetime.now().isoformat()
                        elif '买入成功' in line or '卖出成功' in line:
                            trading_metrics['trade_count'] += 1
                            trading_metrics['last_trade_time'] = datetime.now().isoformat()
                        elif 'ERROR' in line or '❌' in line:
                            trading_metrics['error_count'] += 1
            
            return trading_metrics
            
        except Exception as e:
            self.logger.error(f"❌ 获取交易指标失败: {str(e)}")
            return {}
    
    async def get_network_metrics(self) -> Dict:
        """获取网络指标"""
        try:
            # 测试API连接
            start_time = time.time()
            
            # 测试Binance API连接
            try:
                response = requests.get('https://api.binance.com/api/v3/ping', timeout=5)
                latency = (time.time() - start_time) * 1000  # 转换为毫秒
                connection_status = 'connected' if response.status_code == 200 else 'error'
            except Exception as e:
                latency = float('inf')
                connection_status = 'disconnected'
            
            return {
                'api_latency': latency,
                'api_error_rate': 0.0,  # 需要更复杂的统计
                'connection_status': connection_status,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取网络指标失败: {str(e)}")
            return {}
    
    def check_alerts(self, metrics: Dict) -> List[Dict]:
        """检查告警"""
        alerts = []
        
        try:
            # 系统告警
            if metrics.get('system', {}).get('cpu_usage', 0) > self.alert_thresholds['cpu_usage']:
                alerts.append({
                    'level': 'warning',
                    'type': 'system',
                    'message': f"CPU使用率过高: {metrics['system']['cpu_usage']:.1f}%",
                    'timestamp': datetime.now().isoformat()
                })
            
            if metrics.get('system', {}).get('memory_usage', 0) > self.alert_thresholds['memory_usage']:
                alerts.append({
                    'level': 'warning',
                    'type': 'system',
                    'message': f"内存使用率过高: {metrics['system']['memory_usage']:.1f}%",
                    'timestamp': datetime.now().isoformat()
                })
            
            if metrics.get('system', {}).get('disk_usage', 0) > self.alert_thresholds['disk_usage']:
                alerts.append({
                    'level': 'critical',
                    'type': 'system',
                    'message': f"磁盘使用率过高: {metrics['system']['disk_usage']:.1f}%",
                    'timestamp': datetime.now().isoformat()
                })
            
            # 网络告警
            if metrics.get('network', {}).get('api_latency', 0) > self.alert_thresholds['network_latency']:
                alerts.append({
                    'level': 'warning',
                    'type': 'network',
                    'message': f"API延迟过高: {metrics['network']['api_latency']:.1f}ms",
                    'timestamp': datetime.now().isoformat()
                })
            
            if metrics.get('network', {}).get('connection_status') == 'disconnected':
                alerts.append({
                    'level': 'critical',
                    'type': 'network',
                    'message': "API连接断开",
                    'timestamp': datetime.now().isoformat()
                })
            
            # 交易告警
            trading_metrics = metrics.get('trading', {})
            if trading_metrics.get('error_count', 0) > 10:
                alerts.append({
                    'level': 'warning',
                    'type': 'trading',
                    'message': f"交易错误过多: {trading_metrics['error_count']}",
                    'timestamp': datetime.now().isoformat()
                })
            
            # 检查长时间无信号
            last_signal_time = trading_metrics.get('last_signal_time')
            if last_signal_time:
                last_signal = datetime.fromisoformat(last_signal_time)
                if datetime.now() - last_signal > timedelta(hours=1):
                    alerts.append({
                        'level': 'info',
                        'type': 'trading',
                        'message': "长时间无交易信号",
                        'timestamp': datetime.now().isoformat()
                    })
            
        except Exception as e:
            self.logger.error(f"❌ 检查告警失败: {str(e)}")
        
        return alerts
    
    async def monitor_loop(self):
        """监控循环"""
        self.logger.info("🔄 开始系统监控")
        
        while self.running:
            try:
                # 获取各项指标
                system_metrics = self.get_system_metrics()
                trading_metrics = self.get_trading_metrics()
                network_metrics = await self.get_network_metrics()
                
                # 更新指标
                self.metrics['system'] = system_metrics
                self.metrics['trading'] = trading_metrics
                self.metrics['network'] = network_metrics
                
                # 检查告警
                alerts = self.check_alerts(self.metrics)
                if alerts:
                    self.alerts.extend(alerts)
                    for alert in alerts:
                        self.logger.warning(f"🚨 {alert['message']}")
                
                # 记录监控数据
                self._save_metrics()
                
                # 等待下次监控
                await asyncio.sleep(self.monitor_interval)
                
            except Exception as e:
                self.logger.error(f"❌ 监控循环异常: {str(e)}")
                await asyncio.sleep(self.monitor_interval)
    
    def _save_metrics(self):
        """保存监控指标"""
        try:
            metrics_file = 'logs/metrics.json'
            with open(metrics_file, 'w', encoding='utf-8') as f:
                json.dump(self.metrics, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"❌ 保存监控指标失败: {str(e)}")
    
    def get_health_status(self) -> Dict:
        """获取系统健康状态"""
        try:
            # 计算健康度分数
            health_score = 100.0
            
            # 系统健康度
            system_metrics = self.metrics.get('system', {})
            if system_metrics.get('cpu_usage', 0) > 80:
                health_score -= 20
            if system_metrics.get('memory_usage', 0) > 85:
                health_score -= 20
            if system_metrics.get('disk_usage', 0) > 90:
                health_score -= 30
            
            # 网络健康度
            network_metrics = self.metrics.get('network', {})
            if network_metrics.get('connection_status') == 'disconnected':
                health_score -= 40
            elif network_metrics.get('api_latency', 0) > 1000:
                health_score -= 10
            
            # 交易健康度
            trading_metrics = self.metrics.get('trading', {})
            if trading_metrics.get('error_count', 0) > 10:
                health_score -= 15
            
            # 确定健康状态
            if health_score >= 80:
                status = 'healthy'
            elif health_score >= 60:
                status = 'warning'
            else:
                status = 'critical'
            
            return {
                'health_score': max(0, health_score),
                'status': status,
                'timestamp': datetime.now().isoformat(),
                'metrics': self.metrics,
                'alerts': self.alerts[-10:]  # 最近10个告警
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取健康状态失败: {str(e)}")
            return {
                'health_score': 0,
                'status': 'unknown',
                'timestamp': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def start(self):
        """启动监控"""
        self.running = True
        self.logger.info("🚀 启动系统监控")
        
        # 创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 运行监控循环
            loop.run_until_complete(self.monitor_loop())
        except KeyboardInterrupt:
            self.logger.info("⏹️ 收到停止信号")
        finally:
            self.stop()
    
    def stop(self):
        """停止监控"""
        self.running = False
        self.logger.info("🛑 系统监控已停止")

class HealthChecker:
    """健康检查器"""
    
    def __init__(self):
        self.monitor = SystemMonitor()
    
    def run_health_check(self) -> Dict:
        """运行健康检查"""
        try:
            # 获取健康状态
            health_status = self.monitor.get_health_status()
            
            # 输出健康报告
            print("=" * 50)
            print("🏥 系统健康检查报告")
            print("=" * 50)
            print(f"健康度分数: {health_status['health_score']:.1f}/100")
            print(f"状态: {health_status['status']}")
            print(f"检查时间: {health_status['timestamp']}")
            print()
            
            # 系统指标
            metrics = health_status.get('metrics', {})
            system = metrics.get('system', {})
            print("📊 系统指标:")
            print(f"  CPU使用率: {system.get('cpu_usage', 0):.1f}%")
            print(f"  内存使用率: {system.get('memory_usage', 0):.1f}%")
            print(f"  磁盘使用率: {system.get('disk_usage', 0):.1f}%")
            print()
            
            # 网络指标
            network = metrics.get('network', {})
            print("🌐 网络指标:")
            print(f"  API延迟: {network.get('api_latency', 0):.1f}ms")
            print(f"  连接状态: {network.get('connection_status', 'unknown')}")
            print()
            
            # 交易指标
            trading = metrics.get('trading', {})
            print("💰 交易指标:")
            print(f"  信号数量: {trading.get('signal_count', 0)}")
            print(f"  交易数量: {trading.get('trade_count', 0)}")
            print(f"  错误数量: {trading.get('error_count', 0)}")
            print()
            
            # 告警信息
            alerts = health_status.get('alerts', [])
            if alerts:
                print("🚨 告警信息:")
                for alert in alerts:
                    print(f"  [{alert['level'].upper()}] {alert['message']}")
                print()
            
            print("=" * 50)
            
            return health_status
            
        except Exception as e:
            print(f"❌ 健康检查失败: {str(e)}")
            return {'error': str(e)}

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='交易系统监控')
    parser.add_argument('action', choices=['monitor', 'health-check'],
                       help='监控操作')
    parser.add_argument('--interval', type=int, default=30,
                       help='监控间隔(秒)')
    
    args = parser.parse_args()
    
    if args.action == 'monitor':
        # 启动监控
        monitor = SystemMonitor({'monitor_interval': args.interval})
        monitor.start()
    
    elif args.action == 'health-check':
        # 运行健康检查
        checker = HealthChecker()
        checker.run_health_check()

if __name__ == "__main__":
    main() 