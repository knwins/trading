#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统监控和健康检查模块
监控实盘交易系统的运行状态

功能：
1. 系统健康检查
2. 性能监控
3. 异常告警
4. 资源使用监控
5. 交易状态监控
"""

import os
import sys
import time
import json
import psutil
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_usage: float
    network_io: Dict[str, float]
    process_count: int
    uptime: float

@dataclass
class TradingMetrics:
    """交易指标"""
    timestamp: datetime
    current_price: float
    position: int
    entry_price: float
    position_size: float
    total_pnl: float
    trade_count: int
    last_signal: int
    signal_quality: float

@dataclass
class HealthStatus:
    """健康状态"""
    timestamp: datetime
    overall_status: str  # 'healthy', 'warning', 'critical'
    system_status: str
    trading_status: str
    alerts: List[str]

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self, config: Dict = None):
        """初始化监控器"""
        self.config = config or self._default_config()
        self.setup_logging()
        
        # 监控状态
        self.is_monitoring = False
        self.metrics_history = []
        self.health_history = []
        
        # 阈值配置
        self.thresholds = {
            'cpu_warning': 70.0,
            'cpu_critical': 90.0,
            'memory_warning': 80.0,
            'memory_critical': 95.0,
            'disk_warning': 85.0,
            'disk_critical': 95.0,
            'max_pnl_loss': -0.1,  # 最大亏损10%
            'max_daily_loss': -0.05,  # 最大日亏损5%
        }
        
        # 监控线程
        self.monitor_thread = None
        
    def _default_config(self) -> Dict:
        """默认配置"""
        return {
            'monitor_interval': 30,  # 监控间隔(秒)
            'metrics_retention': 1000,  # 指标保留数量
            'alert_enabled': True,
            'log_metrics': True,
        }
    
    def setup_logging(self):
        """设置日志"""
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = f'{log_dir}/system_monitor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"📊 系统监控器初始化完成: {log_file}")
    
    def collect_system_metrics(self) -> SystemMetrics:
        """收集系统指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            # 网络IO
            network = psutil.net_io_counters()
            network_io = {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            }
            
            # 进程数量
            process_count = len(psutil.pids())
            
            # 系统运行时间
            uptime = time.time() - psutil.boot_time()
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                disk_usage=disk_usage,
                network_io=network_io,
                process_count=process_count,
                uptime=uptime
            )
            
        except Exception as e:
            self.logger.error(f"❌ 收集系统指标失败: {e}")
            return None
    
    def collect_trading_metrics(self, trading_system) -> TradingMetrics:
        """收集交易指标"""
        try:
            if not trading_system:
                return None
            
            # 获取交易系统状态
            current_price = getattr(trading_system, 'kline_data', pd.DataFrame()).get('close', pd.Series()).iloc[-1] if hasattr(trading_system, 'kline_data') and not trading_system.kline_data.empty else 0.0
            
            return TradingMetrics(
                timestamp=datetime.now(),
                current_price=current_price,
                position=getattr(trading_system, 'current_position', 0),
                entry_price=getattr(trading_system, 'entry_price', 0.0),
                position_size=getattr(trading_system, 'position_size', 0.0),
                total_pnl=getattr(trading_system, 'total_pnl', 0.0),
                trade_count=getattr(trading_system, 'trade_count', 0),
                last_signal=getattr(trading_system, 'last_signal', 0),
                signal_quality=0.0  # 需要从策略中获取
            )
            
        except Exception as e:
            self.logger.error(f"❌ 收集交易指标失败: {e}")
            return None
    
    def check_system_health(self, system_metrics: SystemMetrics, trading_metrics: TradingMetrics) -> HealthStatus:
        """检查系统健康状态"""
        alerts = []
        system_status = 'healthy'
        trading_status = 'healthy'
        
        # 检查系统指标
        if system_metrics:
            # CPU检查
            if system_metrics.cpu_percent >= self.thresholds['cpu_critical']:
                alerts.append(f"CPU使用率过高: {system_metrics.cpu_percent:.1f}%")
                system_status = 'critical'
            elif system_metrics.cpu_percent >= self.thresholds['cpu_warning']:
                alerts.append(f"CPU使用率较高: {system_metrics.cpu_percent:.1f}%")
                if system_status == 'healthy':
                    system_status = 'warning'
            
            # 内存检查
            if system_metrics.memory_percent >= self.thresholds['memory_critical']:
                alerts.append(f"内存使用率过高: {system_metrics.memory_percent:.1f}%")
                system_status = 'critical'
            elif system_metrics.memory_percent >= self.thresholds['memory_warning']:
                alerts.append(f"内存使用率较高: {system_metrics.memory_percent:.1f}%")
                if system_status == 'healthy':
                    system_status = 'warning'
            
            # 磁盘检查
            if system_metrics.disk_usage >= self.thresholds['disk_critical']:
                alerts.append(f"磁盘使用率过高: {system_metrics.disk_usage:.1f}%")
                system_status = 'critical'
            elif system_metrics.disk_usage >= self.thresholds['disk_warning']:
                alerts.append(f"磁盘使用率较高: {system_metrics.disk_usage:.1f}%")
                if system_status == 'healthy':
                    system_status = 'warning'
        
        # 检查交易指标
        if trading_metrics:
            # 盈亏检查
            if trading_metrics.total_pnl <= self.thresholds['max_pnl_loss']:
                alerts.append(f"总亏损过大: {trading_metrics.total_pnl:.2%}")
                trading_status = 'critical'
            
            # 检查是否有异常持仓
            if trading_metrics.position != 0 and trading_metrics.entry_price == 0:
                alerts.append("检测到异常持仓状态")
                trading_status = 'warning'
        
        # 确定整体状态
        if system_status == 'critical' or trading_status == 'critical':
            overall_status = 'critical'
        elif system_status == 'warning' or trading_status == 'warning':
            overall_status = 'warning'
        else:
            overall_status = 'healthy'
        
        return HealthStatus(
            timestamp=datetime.now(),
            overall_status=overall_status,
            system_status=system_status,
            trading_status=trading_status,
            alerts=alerts
        )
    
    def start_monitoring(self, trading_system=None):
        """开始监控"""
        self.is_monitoring = True
        self.trading_system = trading_system
        
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info("📊 系统监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_monitoring = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("🛑 系统监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.is_monitoring:
            try:
                # 收集指标
                system_metrics = self.collect_system_metrics()
                trading_metrics = self.collect_trading_metrics(self.trading_system)
                
                # 检查健康状态
                health_status = self.check_system_health(system_metrics, trading_metrics)
                
                # 记录指标
                if system_metrics:
                    self.metrics_history.append(asdict(system_metrics))
                
                if trading_metrics:
                    self.metrics_history.append(asdict(trading_metrics))
                
                self.health_history.append(asdict(health_status))
                
                # 限制历史记录数量
                if len(self.metrics_history) > self.config['metrics_retention']:
                    self.metrics_history = self.metrics_history[-self.config['metrics_retention']:]
                
                if len(self.health_history) > self.config['metrics_retention']:
                    self.health_history = self.health_history[-self.config['metrics_retention']:]
                
                # 记录日志
                if self.config['log_metrics']:
                    self._log_metrics(system_metrics, trading_metrics, health_status)
                
                # 发送告警
                if health_status.alerts and self.config['alert_enabled']:
                    self._send_alerts(health_status)
                
                # 等待下次监控
                time.sleep(self.config['monitor_interval'])
                
            except Exception as e:
                self.logger.error(f"❌ 监控循环异常: {e}")
                time.sleep(self.config['monitor_interval'])
    
    def _log_metrics(self, system_metrics: SystemMetrics, trading_metrics: TradingMetrics, health_status: HealthStatus):
        """记录指标日志"""
        log_msg = f"📊 监控指标 - 系统状态: {health_status.overall_status}"
        
        if system_metrics:
            log_msg += f", CPU: {system_metrics.cpu_percent:.1f}%, 内存: {system_metrics.memory_percent:.1f}%"
        
        if trading_metrics:
            log_msg += f", 仓位: {trading_metrics.position}, 盈亏: {trading_metrics.total_pnl:.2%}"
        
        if health_status.alerts:
            log_msg += f", 告警: {len(health_status.alerts)}个"
        
        self.logger.info(log_msg)
    
    def _send_alerts(self, health_status: HealthStatus):
        """发送告警"""
        for alert in health_status.alerts:
            self.logger.warning(f"⚠️ 系统告警: {alert}")
            
            # 这里可以集成Telegram、邮件等通知方式
            # self.send_telegram_alert(alert)
            # self.send_email_alert(alert)
    
    def get_system_summary(self) -> Dict:
        """获取系统摘要"""
        if not self.health_history:
            return {}
        
        recent_health = self.health_history[-10:]  # 最近10次检查
        
        summary = {
            'current_status': recent_health[-1]['overall_status'] if recent_health else 'unknown',
            'system_uptime': self._get_uptime(),
            'alert_count': sum(1 for h in recent_health if h['alerts']),
            'health_trend': self._calculate_health_trend(recent_health),
            'last_check': recent_health[-1]['timestamp'] if recent_health else None
        }
        
        return summary
    
    def _get_uptime(self) -> str:
        """获取系统运行时间"""
        try:
            uptime_seconds = time.time() - psutil.boot_time()
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            if days > 0:
                return f"{days}天{hours}小时{minutes}分钟"
            elif hours > 0:
                return f"{hours}小时{minutes}分钟"
            else:
                return f"{minutes}分钟"
        except:
            return "未知"
    
    def _calculate_health_trend(self, health_history: List[Dict]) -> str:
        """计算健康趋势"""
        if len(health_history) < 2:
            return "stable"
        
        recent_status = health_history[-1]['overall_status']
        previous_status = health_history[-2]['overall_status']
        
        if recent_status == 'critical' and previous_status != 'critical':
            return "deteriorating"
        elif recent_status == 'healthy' and previous_status != 'healthy':
            return "improving"
        else:
            return "stable"
    
    def export_metrics(self, filepath: str = None):
        """导出监控指标"""
        if not filepath:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f'metrics_export_{timestamp}.json'
        
        export_data = {
            'export_time': datetime.now().isoformat(),
            'metrics_history': self.metrics_history,
            'health_history': self.health_history,
            'system_summary': self.get_system_summary()
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2, default=str)
            
            self.logger.info(f"📁 监控指标已导出到: {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"❌ 导出监控指标失败: {e}")
            return None


def main():
    """测试监控器"""
    monitor = SystemMonitor()
    
    try:
        monitor.start_monitoring()
        
        # 运行一段时间
        time.sleep(60)
        
        # 导出指标
        monitor.export_metrics()
        
    finally:
        monitor.stop_monitoring()


if __name__ == "__main__":
    main() 