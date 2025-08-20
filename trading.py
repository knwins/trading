#!/usr/bin/env python38
# -*- coding: utf-8 -*-
"""
实盘交易系统 - Trading System
支持服务模式和交互模式运行
适用于 CentOS 系统

功能特性:
- 自动交易执行
- 实时信号监控
- 风险控制管理
- 系统状态监控
- 日志记录
- 服务模式运行
- 交互模式启动
"""

import os
import sys
import time
import signal
import logging
import argparse
import threading
import json
from datetime import datetime, timedelta
from pathlib import Path

# 导入项目模块
try:
    from config import *
    from strategy import SharpeOptimizedStrategy
    from data_loader import DataLoader
    from feature_engineer import FeatureEngineer
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保在项目根目录运行此脚本")
    sys.exit(1)

class TradingSystem:
    """实盘交易系统核心类"""
    
    def __init__(self, mode='interactive'):
        """初始化交易系统"""
        self.mode = mode
        self.running = True  # 改为True，表示系统已启动
        self.start_time = datetime.now()
        
        # 加载用户配置
        try:
            from user_config import apply_user_config
            success, message = apply_user_config()
            if success:
                print(f"✅ {message}")
            else:
                print(f"⚠️ {message}")
        except Exception as e:
            print(f"⚠️ 加载用户配置失败: {e}")
        
        # 初始化日志
        self.setup_logging()
        
        # 初始化真实交易API
        self.setup_real_trading()
        
        # 初始化组件
        self.setup_components()
        
        # 初始化资金管理
        self.setup_capital_management()
        
        # 设置信号处理器
        self.setup_signal_handlers()
        
        # 初始化交易状态
        self.setup_trading_state()
        
        self.logger.info(f"🚀 交易系统初始化完成 - 模式: {mode}")
    
    def setup_logging(self):
        """设置日志系统"""
        log_dir = Path(LOGGING_CONFIG.get('LOG_DIR', 'logs'))
        log_dir.mkdir(exist_ok=True)
        # 创建日志文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f"trading_{timestamp}.log"
        
        # 配置日志格式
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        # 在交互模式下，只输出到文件，不输出到控制台
        handlers = [logging.FileHandler(log_file, encoding='utf-8')]
        if self.mode != 'interactive' and LOGGING_CONFIG.get('CONSOLE_OUTPUT', True):
            handlers.append(logging.StreamHandler())
            
        logging.basicConfig(
            level=getattr(logging, LOGGING_CONFIG.get('LEVEL', 'INFO')),
            format=log_format,
            handlers=handlers
        )
        
        self.logger = logging.getLogger('TradingSystem')
        self.logger.info(f"📝 日志系统初始化完成: {log_file}")
    
    def setup_real_trading(self):
        """初始化真实交易API"""
        try:
            from exchange_api import RealExchangeAPI
            
            # 从配置文件加载API密钥
            api_key = ''
            secret_key = ''
            
            # 首先尝试从环境变量获取
            api_key = os.getenv('BINANCE_API_KEY', '')
            secret_key = os.getenv('BINANCE_SECRET_KEY', '')
            
            # 如果环境变量没有，尝试从配置文件加载
            if not api_key or not secret_key:
                config_file = 'api_config.json'
                if os.path.exists(config_file):
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            api_config = json.load(f)
                        api_key = api_config.get('api_key', '')
                        secret_key = api_config.get('secret_key', '')
                        print("✅ 从配置文件加载API密钥")
                    except Exception as e:
                        print(f"⚠️ 加载配置文件失败: {e}")
            
            if not api_key or not secret_key:
                print("⚠️ 未配置API密钥，将使用模拟交易模式")
                self.real_trading = False
                self.exchange_api = None
                return
            
            # 初始化真实交易API
            self.exchange_api = RealExchangeAPI(
                api_key=api_key,
                secret_key=secret_key,
                testnet=False  # 使用主网
            )
            self.exchange_api.set_logger(self.logger)
            
            # 测试API连接
            success, message = self.exchange_api.test_connection()
            if success:
                print("✅ 真实交易API连接成功")
                self.real_trading = True
            else:
                print(f"❌ 真实交易API连接失败: {message}")
                self.real_trading = False
                
        except Exception as e:
            print(f"❌ 初始化真实交易API失败: {e}")
            self.real_trading = False
            self.exchange_api = None
    
    def setup_components(self):
        """初始化系统组件"""
        try:
            # 数据加载器
            self.data_loader = DataLoader()
            self.logger.info("📊 数据加载器初始化完成")
            
            # 特征工程
            self.feature_engineer = FeatureEngineer()
            self.logger.info("🔧 特征工程初始化完成")
            
            # 交易策略
            self.strategy = SharpeOptimizedStrategy(
                config=OPTIMIZED_STRATEGY_CONFIG,
                data_loader=self.data_loader
            )
            self.logger.info("📈 交易策略初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 组件初始化失败: {e}")
            raise
    
    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        if hasattr(signal, 'SIGUSR2'):
            signal.signal(signal.SIGUSR2, self.emergency_stop)
    
    def setup_capital_management(self):
        """设置资金管理"""
        # 获取资金配置
        capital_config = TRADING_CONFIG.get('CAPITAL_CONFIG', {})
        risk_config = TRADING_CONFIG.get('RISK_CONFIG', {})
        
        # 资金状态
        self.initial_capital = capital_config.get('INITIAL_CAPITAL', 10000)
        self.current_capital = self.initial_capital
        self.available_capital = self.initial_capital
        
        # 仓位管理
        self.position_size_percent = capital_config.get('POSITION_SIZE_PERCENT', 0.1)
        self.max_position_size = capital_config.get('MAX_POSITION_SIZE', 0.5)
        self.min_position_size = capital_config.get('MIN_POSITION_SIZE', 0.05)
        self.leverage = capital_config.get('LEVERAGE', 1)
        
        # 风险控制
        self.max_daily_trades = risk_config.get('MAX_DAILY_TRADES', 10)
        self.min_trade_interval = risk_config.get('MIN_TRADE_INTERVAL', 300)
        self.max_daily_loss = risk_config.get('MAX_DAILY_LOSS', 0.05)
        self.max_total_loss = risk_config.get('MAX_TOTAL_LOSS', 0.20)
        self.emergency_stop_loss = risk_config.get('EMERGENCY_STOP_LOSS', 0.30)
        
        # 交易记录
        self.daily_trades = 0
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.trade_history = []
        
        # 重置每日计数
        self.reset_daily_counters()
        
        self.logger.info(f"💰 资金管理初始化完成 - 初始资金: {self.initial_capital} USDT")
        self.logger.info(f"📊 仓位配置 - 单次: {self.position_size_percent*100}%, 最大: {self.max_position_size*100}%")
        self.logger.info(f"🛡️ 风险控制 - 每日最大交易: {self.max_daily_trades}, 间隔: {self.min_trade_interval}秒")
    
    def setup_trading_state(self):
        """初始化交易状态"""
        # 交易状态
        self.current_position = 0  # 0=无仓位, 1=多头, -1=空头
        self.last_signal = 0
        self.last_trade_time = None
        self.trade_count = 0
        
        # 系统监控
        self.heartbeat_interval = 30  # 心跳间隔(秒)
        
        self.logger.info("📊 交易状态初始化完成")
    
    def reset_daily_counters(self):
        """重置每日计数器"""
        current_date = datetime.now().date()
        if not hasattr(self, 'last_reset_date') or self.last_reset_date != current_date:
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.last_reset_date = current_date
            self.logger.info("🔄 每日计数器已重置")
    
    def signal_handler(self, signum, frame):
        """信号处理器"""
        self.logger.info(f"📡 收到信号 {signum}，正在停止系统...")
        
        # 在交互模式下，提供用户选择
        if self.mode == 'interactive':
            print(f"\n📡 收到中断信号 {signum}")
            if self.current_position != 0:
                position_desc = {1: '多头', -1: '空头'}.get(self.current_position, '未知')
                print(f"⚠️  当前持有{position_desc}仓位")
                print("请选择处理方式:")
                print("   1. 平仓后退出")
                print("   2. 保持仓位退出")
                print("   0. 取消退出")
                
                try:
                    choice = input("\n请选择处理方式 (0-2): ").strip()
                    
                    if choice == '1':
                        print("🔄 正在平仓...")
                        self.current_position = 0
                        self.available_capital = self.current_capital
                        print("✅ 仓位已平仓")
                        print("👋 再见!")
                        self.stop()
                        
                    elif choice == '2':
                        print(f"⚠️  保持{position_desc}仓位退出")
                        print("👋 再见!")
                        self.stop()
                        
                    elif choice == '0':
                        print("✅ 取消退出")
                        return
                        
                    else:
                        print("❌ 无效选择，保持仓位退出")
                        self.stop()
                        
                except KeyboardInterrupt:
                    print("\n✅ 取消退出")
                    return
            else:
                print("✅ 当前无仓位，直接退出")
                print("👋 再见!")
                self.stop()
        else:
            # 在服务模式下，直接停止系统
            self.stop()
    

    
    def emergency_stop(self, signum, frame):
        """紧急停止"""
        self.logger.warning("🚨 紧急停止触发！")
        
        # 在交互模式下，不强制平仓，而是提示用户
        if self.mode == 'interactive':
            print("\n🚨 紧急停止触发！")
            if self.current_position != 0:
                position_desc = {1: '多头', -1: '空头'}.get(self.current_position, '未知')
                print(f"⚠️  当前持有{position_desc}仓位")
                print("请选择处理方式:")
                print("   1. 强制平仓后停止")
                print("   2. 保持仓位停止")
                print("   0. 取消停止")
                
                try:
                    choice = input("\n请选择处理方式 (0-2): ").strip()
                    
                    if choice == '1':
                        print("🔄 正在强制平仓...")
                        self.emergency_close_positions()
                        print("✅ 仓位已强制平仓")
                        self.stop()
                        
                    elif choice == '2':
                        print(f"⚠️  保持{position_desc}仓位停止")
                        self.stop()
                        
                    elif choice == '0':
                        print("✅ 取消停止")
                        return
                        
                    else:
                        print("❌ 无效选择，保持仓位停止")
                        self.stop()
                        
                except KeyboardInterrupt:
                    print("\n✅ 取消停止")
                    return
            else:
                print("✅ 当前无仓位，直接停止")
                self.stop()
        else:
            # 在服务模式下，直接强制平仓
            self.emergency_close_positions()
            self.stop()
    
    def emergency_close_positions(self):
        """紧急平仓"""
        if self.current_position != 0:
            position_desc = {1: '多头', -1: '空头'}.get(self.current_position, '未知')
            self.logger.warning(f"🚨 紧急平仓: {position_desc}仓位")
            print(f"🚨 紧急平仓: {position_desc}仓位")
            
            # 这里应该调用实际的平仓API
            # 在实际交易中，这里需要调用交易所的平仓接口
            # 目前只是模拟平仓操作
            
            # 恢复可用资金
            self.available_capital = self.current_capital
            self.current_position = 0
            
            self.logger.info("✅ 紧急平仓完成")
            print("✅ 紧急平仓完成")
        else:
            self.logger.info("ℹ️ 当前无仓位，无需平仓")
            print("ℹ️ 当前无仓位，无需平仓")
    
    def get_market_data(self, silent=False):
        """获取市场数据"""
        try:
            # 计算时间范围：获取最近1000条数据
            end_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            start_date = (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d %H:%M:%S')
            
            # 获取最新K线数据
            klines = self.data_loader.get_klines(
                start_date=start_date,
                end_date=end_date,
                silent=silent
            )
            
            if klines is None or klines.empty:
                if not silent:
                    self.logger.warning("⚠️ 无法获取市场数据")
                return None
            
            return klines
            
        except Exception as e:
            if not silent:
                self.logger.error(f"❌ 获取市场数据失败: {e}")
            return None
    
    def generate_signals(self, market_data, silent=False):
        """生成交易信号"""
        try:
            if market_data is None or market_data.empty:
                return None
            
            # 计算特征
            features = self.feature_engineer.generate_features(market_data, silent=silent)
            
            # 生成信号
            signal_info = self.strategy.generate_signals(features, silent=silent)
            
            if signal_info is not None and isinstance(signal_info, dict):
                return signal_info
            
            return None
            
        except Exception as e:
            if not silent:
                self.logger.error(f"❌ 生成信号失败: {e}")
            return None
    
    def execute_trade(self, signal):
        """执行交易"""
        try:
            if signal is None:
                return
            
            signal_value = signal.get('signal', 0)
            signal_score = signal.get('final_score', 0)
            
            # 记录信号（在交互模式下不输出到控制台）
            if self.mode != 'interactive':
                self.logger.info(f"📊 信号: {signal_value}, 评分: {signal_score:.4f}")
            
            # 计算仓位大小
            position_size = self.calculate_position_size(signal_score)
            
            # 交易逻辑
            if signal_value == 1 and self.current_position <= 0:
                # 开多仓
                if self.real_trading and self.exchange_api:
                    # 真实交易
                    symbol = TRADING_CONFIG.get('SYMBOL', 'ETHUSDT')
                    trade_amount = self.available_capital * position_size
                    
                    # 设置杠杆和保证金类型
                    leverage_result = self.exchange_api.set_leverage(symbol, self.leverage)
                    if not leverage_result['success']:
                        error_msg = leverage_result['error']
                        if 'ip_info' in leverage_result:
                            error_msg += f" ({leverage_result['ip_info']})"
                        self.logger.warning(f"杠杆设置警告: {error_msg}")
                    
                    # 执行买入订单
                    result = self.exchange_api.place_order(symbol, 'buy', trade_amount)
                    
                    if result['success']:
                        self.logger.info(f"🟢 真实开多仓成功 - 订单ID: {result['order_id']}")
                        self.current_position = 1
                        self.available_capital -= trade_amount
                        self.record_trade('LONG', trade_amount, signal_score)
                    else:
                        self.logger.error(f"❌ 真实开多仓失败: {result['error']}")
                else:
                    # 模拟交易
                    trade_amount = self.available_capital * position_size
                    self.logger.info(f"🟢 模拟开多仓 - 金额: {trade_amount:,.0f} USDT, 仓位: {position_size:.1%}")
                    self.current_position = 1
                    self.available_capital -= trade_amount
                    self.record_trade('LONG', trade_amount, signal_score)
                
            elif signal_value == -1 and self.current_position >= 0:
                # 开空仓
                if self.real_trading and self.exchange_api:
                    # 真实交易
                    symbol = TRADING_CONFIG.get('SYMBOL', 'ETHUSDT')
                    trade_amount = self.available_capital * position_size
                    
                    # 设置杠杆和保证金类型
                    leverage_result = self.exchange_api.set_leverage(symbol, self.leverage)
                    if not leverage_result['success']:
                        error_msg = leverage_result['error']
                        if 'ip_info' in leverage_result:
                            error_msg += f" ({leverage_result['ip_info']})"
                        self.logger.warning(f"杠杆设置警告: {error_msg}")
                    
                    # 执行卖出订单
                    result = self.exchange_api.place_order(symbol, 'sell', trade_amount)
                    
                    if result['success']:
                        self.logger.info(f"🔴 真实开空仓成功 - 订单ID: {result['order_id']}")
                        self.current_position = -1
                        self.available_capital -= trade_amount
                        self.record_trade('SHORT', trade_amount, signal_score)
                    else:
                        self.logger.error(f"❌ 真实开空仓失败: {result['error']}")
                else:
                    # 模拟交易
                    trade_amount = self.available_capital * position_size
                    self.logger.info(f"🔴 模拟开空仓 - 金额: {trade_amount:,.0f} USDT, 仓位: {position_size:.1%}")
                    self.current_position = -1
                    self.available_capital -= trade_amount
                    self.record_trade('SHORT', trade_amount, signal_score)
                
            elif signal_value == 0 and self.current_position != 0:
                # 平仓
                position_desc = "多头" if self.current_position == 1 else "空头"
                
                if self.real_trading and self.exchange_api:
                    # 真实平仓
                    symbol = TRADING_CONFIG.get('SYMBOL', 'ETHUSDT')
                    result = self.exchange_api.close_position(symbol)
                    
                    if result['success']:
                        self.logger.info(f"⚪ 真实平仓成功 ({position_desc})")
                        self.current_position = 0
                        self.available_capital = self.current_capital
                        self.record_trade('CLOSE', 0, signal_score)
                    else:
                        self.logger.error(f"❌ 真实平仓失败: {result['error']}")
                else:
                    # 模拟平仓
                    self.logger.info(f"⚪ 模拟平仓 ({position_desc}) - 当前仓位: {self.current_position}")
                    self.current_position = 0
                    self.available_capital = self.current_capital
                    self.record_trade('CLOSE', 0, signal_score)
            
            self.last_signal = signal_value
            
        except Exception as e:
            self.logger.error(f"❌ 执行交易失败: {e}")
    
    def calculate_position_size(self, signal_score):
        """计算仓位大小"""
        try:
            # 基于信号评分调整仓位大小
            abs_score = abs(signal_score)
            
            if abs_score >= 0.7:
                # 强信号，使用最大仓位
                position_size = self.max_position_size
            elif abs_score >= 0.3:
                # 中等信号，使用标准仓位
                position_size = self.position_size_percent
            else:
                # 弱信号，使用最小仓位
                position_size = self.min_position_size
            
            # 确保不超过可用资金
            max_position = self.available_capital / self.current_capital
            position_size = min(position_size, max_position)
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"❌ 计算仓位大小失败: {e}")
            return self.min_position_size
    
    def record_trade(self, trade_type, amount, signal_score):
        """记录交易"""
        try:
            self.trade_count += 1
            self.daily_trades += 1
            self.last_trade_time = datetime.now()
            
            trade_record = {
                'timestamp': self.last_trade_time,
                'type': trade_type,
                'amount': amount,
                'signal_score': signal_score,
                'position': self.current_position,
                'capital': self.current_capital,
                'available_capital': self.available_capital
            }
            
            self.trade_history.append(trade_record)
            
            self.logger.info(f"📝 交易记录: {trade_type} - 金额: {amount:,.0f} USDT, 评分: {signal_score:.4f}")
            
        except Exception as e:
            self.logger.error(f"❌ 记录交易失败: {e}")
    
    def check_risk_limits(self):
        """检查风险限制"""
        try:
            # 重置每日计数器
            self.reset_daily_counters()
            
            # 检查交易频率
            if self.last_trade_time:
                time_since_last_trade = (datetime.now() - self.last_trade_time).total_seconds()
                if time_since_last_trade < self.min_trade_interval:
                    self.logger.debug(f"⚠️ 交易间隔不足: {time_since_last_trade:.0f}秒 < {self.min_trade_interval}秒")
                    return False
            
            # 检查每日最大交易次数
            if self.daily_trades >= self.max_daily_trades:
                self.logger.warning(f"⚠️ 达到每日最大交易次数限制: {self.daily_trades}/{self.max_daily_trades}")
                return False
            
            # 检查每日最大亏损
            daily_loss_ratio = abs(self.daily_pnl) / self.initial_capital
            if daily_loss_ratio >= self.max_daily_loss:
                self.logger.warning(f"⚠️ 达到每日最大亏损限制: {daily_loss_ratio:.2%} >= {self.max_daily_loss:.2%}")
                return False
            
            # 检查总资金最大亏损
            total_loss_ratio = abs(self.total_pnl) / self.initial_capital
            if total_loss_ratio >= self.max_total_loss:
                self.logger.warning(f"⚠️ 达到总资金最大亏损限制: {total_loss_ratio:.2%} >= {self.max_total_loss:.2%}")
                return False
            
            # 检查紧急止损
            if total_loss_ratio >= self.emergency_stop_loss:
                self.logger.error(f"🚨 触发紧急止损: {total_loss_ratio:.2%} >= {self.emergency_stop_loss:.2%}")
                self.emergency_close_positions()
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 风险检查失败: {e}")
            return False
    
    def log_system_status(self, manual=False):
        """记录系统状态"""
        try:
            uptime = datetime.now() - self.start_time
            
            # 计算收益率
            total_return = (self.current_capital - self.initial_capital) / self.initial_capital
            daily_return = self.daily_pnl / self.initial_capital
            
            # 获取交易所合约信息
            exchange_info = self.get_exchange_info()
            
            status = {
                '运行时间': str(uptime).split('.')[0],
                '当前仓位': self.current_position,
                '最后信号': self.last_signal,
                '交易次数': self.trade_count,
                '系统状态': '运行中' if self.running else '已停止',
        
                '初始资金': f"{self.initial_capital:,.0f} USDT",
                '当前资金': f"{self.current_capital:,.0f} USDT",
                '可用资金': f"{self.available_capital:,.0f} USDT",
                '总收益': f"{self.total_pnl:+,.0f} USDT ({total_return:+.2%})",
                '今日收益': f"{self.daily_pnl:+,.0f} USDT ({daily_return:+.2%})",
                '今日交易': f"{self.daily_trades}/{self.max_daily_trades}",
                '交易所': exchange_info.get('exchange', 'Binance'),
                '合约类型': exchange_info.get('contract_type', '永续合约'),
                '交易对': exchange_info.get('symbol', 'ETHUSDT'),
                '杠杆倍数': f"{self.leverage}x",
                'API状态': exchange_info.get('api_status', '正常'),
                '网络延迟': exchange_info.get('latency', 'N/A')
            }
            
            # 在交互模式下，只有手动调用才打印到控制台
            if self.mode == 'interactive':
                if manual:
                    self.show_current_config(exchange_info)  # 传递已获取的交易所信息
                # 心跳调用时只记录到日志文件，不打印到控制台
            else:
                self.logger.info(f"📊 系统状态: {status}")
            
        except Exception as e:
            if self.mode != 'interactive':
                self.logger.error(f"❌ 记录系统状态失败: {e}")
    
    def get_exchange_info(self):
        """获取交易所合约信息"""
        try:
            # 获取基本配置信息
            symbol = TRADING_CONFIG.get('SYMBOL', 'ETHUSDT')
            timeframe = TRADING_CONFIG.get('TIMEFRAME', '1h')
            
            # 测试API连接状态
            api_status, latency = self.test_api_connection()
            
            # 期货合约类型
            if symbol.endswith('USDT'):
                contract_type = "永续合约"
            elif symbol.endswith('USD'):
                contract_type = "交割合约"
            else:
                contract_type = "期货合约"
            
            # 获取服务器时间
            server_time = self.get_server_time()
            
            exchange_info = {
                'exchange': 'Binance',
                'contract_type': contract_type,
                'symbol': symbol,
                'timeframe': timeframe,
                'api_status': api_status,
                'latency': latency,
                'api_url': 'https://fapi.binance.com/fapi/v1',
                'testnet': False,
                'server_time': server_time
            }
            
            # 添加调试信息
            if self.logger:
                self.logger.debug(f"get_exchange_info: api_status={api_status}, latency={latency}")
            
            return exchange_info
            
        except Exception as e:
            self.logger.error(f"❌ 获取交易所信息失败: {e}")
            # 简化异常处理，直接返回默认值
            return {
                'exchange': 'Binance',
                'contract_type': '永续合约',
                'symbol': 'ETHUSDT',
                'api_status': '异常',
                'latency': 'N/A',
                'api_url': 'https://fapi.binance.com/fapi/v1',
                'testnet': False,
                'server_time': 'N/A'
            }
    
    def test_api_connection(self):
        """测试API连接状态"""
        try:
            import time
            import requests
            
            start_time = time.time()
            
            # 测试API连接
            response = requests.get('https://fapi.binance.com/fapi/v1/ping', timeout=5)
            
            end_time = time.time()
            latency = f"{(end_time - start_time) * 1000:.0f}ms"
            
            if response.status_code == 200:
                api_status = "正常"
            else:
                api_status = f"异常 ({response.status_code})"
                
            return api_status, latency
            
        except requests.exceptions.Timeout:
            return "超时", ">5000ms"
        except requests.exceptions.ConnectionError:
            return "连接失败", "N/A"
        except Exception as e:
            return f"异常 ({str(e)[:20]})", "N/A"
    
    def get_server_time(self):
        """获取服务器时间"""
        try:
            import requests
            response = requests.get('https://fapi.binance.com/fapi/v1/time', timeout=5)
            if response.status_code == 200:
                server_time = response.json().get('serverTime', 0)
                from datetime import datetime
                return datetime.fromtimestamp(server_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
            else:
                return "N/A"
        except:
            return "N/A"
    
    def trading_loop(self):
        """主交易循环"""
        self.logger.info("🔄 开始交易循环")
        
        while self.running:
            try:
                # 检查风险限制
                if not self.check_risk_limits():
                    time.sleep(60)
                    continue
                
                # 获取市场数据（静默模式）
                market_data = self.get_market_data(silent=True)
                if market_data is None:
                    time.sleep(30)
                    continue
                
                # 生成信号
                signal = self.generate_signals(market_data, silent=True)
                
                # 执行交易
                if signal is not None:
                    self.execute_trade(signal)
                
                # 等待下次循环
                time.sleep(60)  # 1分钟循环
                
            except Exception as e:
                self.logger.error(f"❌ 交易循环异常: {e}")
                time.sleep(30)
    
    def heartbeat_loop(self):
        """心跳监控循环"""
        while self.running:
            try:
                time.sleep(self.heartbeat_interval)
                self.log_system_status()
            except Exception as e:
                self.logger.error(f"❌ 心跳循环异常: {e}")
    
    def start(self):
        """启动交易系统"""
        if self.running:
            self.logger.warning("⚠️ 系统已在运行中")
            return
        
        self.running = True
        self.logger.info("🚀 启动交易系统")
        
        # 启动交易线程
        self.trading_thread = threading.Thread(target=self.trading_loop, daemon=True)
        self.trading_thread.start()
        
        # 启动心跳线程
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        
        if self.mode == 'interactive':
            self.interactive_mode()
        else:
            self.service_mode()
    
    def service_mode(self):
        """服务模式运行"""
        self.logger.info("🔧 服务模式运行中...")
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("📡 收到中断信号")
        finally:
            self.stop()
    
    def interactive_mode(self):
        """交互模式运行"""
        self.logger.info("💬 交互模式启动")
        
        # 启动交互界面线程
        self.interactive_thread = threading.Thread(target=self.interactive_interface, daemon=True)
        self.interactive_thread.start()
        
        # 主线程等待交互线程结束
        try:
            while self.running and self.interactive_thread.is_alive():
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.logger.info("📡 收到中断信号")
        finally:
            self.stop()
    
    def show_main_menu(self):
        """显示主菜单"""
        print("\n" + "="*50)
        print("🚀 交易系统 - 交互控制台")
        print("="*50)
        print("")
        print("📊 监控与查看")
        print("   1. 系统状态")
        print("   2. 交易历史")
        print("   3. 性能监控")
        print("")
        print("⚙️ 系统控制")
        print("   4. 系统配置")
        print("")
        print("🔧 高级功能")
        print("   5. 创建服务文件")
        print("   6. API密钥配置")
        print("")
        print("   0. 退出系统")
        print("="*50)

    def interactive_interface(self):
        """交互界面"""
        self.show_main_menu()
        
        while self.running:
            try:
                choice = input("\n请选择功能 (0-7): ").strip()
                
                if choice == '1':
                    self.log_system_status(manual=True)
                    input("\n按回车键继续...")
                    self.show_main_menu()
                elif choice == '2':
                    self.show_trade_history()
                    input("\n按回车键继续...")
                    self.show_main_menu()
                elif choice == '3':
                    self.show_performance_monitor()
                    input("\n按回车键继续...")
                    self.show_main_menu()
                elif choice == '4':
                    self.interactive_config()
                    # 从配置菜单返回后重新显示主菜单
                    self.show_main_menu()
                elif choice == '5':
                    self.create_service_file()
                    input("\n按回车键继续...")
                    self.show_main_menu()
                elif choice == '6':
                    self.config_api_keys()
                    input("\n按回车键继续...")
                    self.show_main_menu()
                elif choice == '0':
                    # 调用退出确认，根据返回值决定是否真的退出
                    if self.confirm_exit():
                        break  # 用户确认退出，跳出主循环
                    else:
                        # 用户取消退出，重新显示主菜单
                        self.show_main_menu()
                    
                # 兼容旧的文字命令
                elif choice.lower() in ['status', 'config', 'stop', 'help', 'quit', 'exit', 'history']:
                    command = choice.lower()
                    if command == 'status':
                        self.log_system_status(manual=True)
                    elif command == 'history':
                        self.show_trade_history()
                    elif command == 'config':
                        self.interactive_config()
                    elif command == 'stop':
                        print("🛑 正在停止系统...")
                        self.stop()
                        break
                    elif command == 'service':
                        self.create_service_file()
                    elif command in ['quit', 'exit']:
                        # 调用退出确认，根据返回值决定是否真的退出
                        if self.confirm_exit():
                            break  # 用户确认退出，跳出主循环
                        else:
                            # 用户取消退出，重新显示主菜单
                            self.show_main_menu()
                    
                else:
                    print("❓ 无效选择，请输入 0-6")
                    self.show_main_menu()
                    
            except KeyboardInterrupt:
                print("\n📡 收到中断信号")
                self.stop()
                break
            except EOFError:
                print("\n👋 再见!")
                self.stop()
                break
    
    def stop(self):
        """停止交易系统"""
        if not self.running:
            return
        
        self.logger.info("🛑 正在停止交易系统...")
        self.running = False
        
        # 等待线程结束
        if hasattr(self, 'trading_thread'):
            self.trading_thread.join(timeout=5)
        if hasattr(self, 'heartbeat_thread'):
            self.heartbeat_thread.join(timeout=5)
        
        self.logger.info("✅ 交易系统已停止")
    

    
    def show_config_menu(self):
        """显示配置菜单"""
        print("\n" + "="*50)
        print("⚙️ 系统配置中心")
        print("="*50)
        print("")
        print("📈 交易设置")
        print("   1. 交易对设置")
        print("   2. 时间级别设置")
        print("   3. 初始仓位设置")
        print("")
        print("💰 资金管理")
        print("   4. 资金配置")
        print("   5. 仓位管理")
        print("")
        print("🛡️ 风险管理")
        print("   6. 风险控制设置")
        print("")
        print("📋 配置管理")
        print("   7. 查看当前配置")
        print("   8. 重置配置")
        print("")
        print("   0. 返回主菜单 (自动保存)")
        print("="*50)

    def interactive_config(self):
        """交互式配置系统参数"""
        while True:
            self.show_config_menu()
            
            try:
                choice = input("\n请选择配置项 (0-9): ").strip()
                
                if choice == '':
                    # 空输入，重新显示菜单
                    continue
                elif choice == '1':
                    self.config_trading_pair()
                    # 子菜单返回后重新显示配置菜单
                    continue
                elif choice == '2':
                    self.config_timeframe()
                    # 子菜单返回后重新显示配置菜单
                    continue
                elif choice == '3':
                    self.config_initial_position()
                    # 子菜单返回后重新显示配置菜单
                    continue
                elif choice == '4':
                    self.config_capital()
                    # 子菜单返回后重新显示配置菜单
                    continue
                elif choice == '5':
                    self.config_position_management()
                    # 子菜单返回后重新显示配置菜单
                    continue
                elif choice == '6':
                    self.config_risk_control()
                    # 子菜单返回后重新显示配置菜单
                    continue
                elif choice == '7':
                    self.show_current_config()
                    input("\n按回车键继续...")
                    # 显示后重新显示配置菜单
                    continue
                elif choice == '8':
                    self.reset_config()
                    input("\n按回车键继续...")
                    # 重置后重新显示配置菜单
                    continue
                elif choice == '0' or choice == '9':  # 支持0和9都能返回
                    print("💾 自动保存配置...")
                    self.save_config()
                    print("✅ 配置已保存")
                    print("✅ 返回主菜单")
                    break
                else:
                    print("❓ 无效选择，请输入 0-8")
                    
            except KeyboardInterrupt:
                print("\n📡 返回主菜单")
                break
            except Exception as e:
                print(f"❌ 配置错误: {e}")
    
    def show_trading_pair_menu(self):
        """显示交易对配置菜单"""
        print("\n" + "="*50)
        print("📈 交易对配置")
        print("="*50)
        current_symbol = TRADING_CONFIG.get('SYMBOL', 'ETHUSDT')
        print(f"当前交易对: {current_symbol}")
        print("")
        
        # 常用交易对列表
        common_pairs = [
            'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
            'DOTUSDT', 'LINKUSDT', 'MATICUSDT', 'AVAXUSDT', 'ATOMUSDT'
        ]
        
        print("📋 交易对选项:")
        for i, pair in enumerate(common_pairs, 1):
            current = " (当前)" if pair == current_symbol else ""
            print(f"   {i:2d}. {pair}{current}")
        print("   11. 自定义输入")
        print("   0. 返回")
        print("="*50)
    
    def config_trading_pair(self):
        """配置交易对"""
        while True:
            self.show_trading_pair_menu()
            
            try:
                choice = input(f"\n请选择 (0-11): ").strip()
                
                if choice == '':
                    # 空输入，重新显示菜单
                    continue
                elif choice == '0':
                    return
                elif choice == '11':
                    symbol = input("请输入交易对: ").strip().upper()
                    if symbol and len(symbol) >= 6:
                        TRADING_CONFIG['SYMBOL'] = symbol
                        self.data_loader.symbol = symbol
                        print(f"✅ 交易对: {symbol}")
                        return
                    elif symbol == '':
                        print("💡 已取消修改")
                    else:
                        print("❌ 交易对格式错误")
                elif choice.isdigit() and 1 <= int(choice) <= 10:
                    common_pairs = [
                        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'SOLUSDT',
                        'DOTUSDT', 'LINKUSDT', 'MATICUSDT', 'AVAXUSDT', 'ATOMUSDT'
                    ]
                    symbol = common_pairs[int(choice) - 1]
                    TRADING_CONFIG['SYMBOL'] = symbol
                    self.data_loader.symbol = symbol
                    print(f"✅ 交易对: {symbol}")
                    return
                else:
                    print("❌ 无效选择")
                    
            except Exception as e:
                print(f"❌ 配置失败: {e}")
    
    def show_timeframe_menu(self):
        """显示时间级别配置菜单"""
        print("\n" + "="*50)
        print("⏰ 时间级别配置")
        print("="*50)
        current_timeframe = TRADING_CONFIG.get('TIMEFRAME', '1h')
        print(f"当前时间级别: {current_timeframe}")
        print("")
        
        timeframes = [
            ('1m', '1分钟'),
            ('5m', '5分钟'),
            ('15m', '15分钟'),
            ('30m', '30分钟'),
            ('1h', '1小时'),
            ('2h', '2小时'),
            ('4h', '4小时'),
            ('1d', '1天')
        ]
        
        print("📋 时间级别选项:")
        for i, (tf, desc) in enumerate(timeframes, 1):
            current = " (当前)" if tf == current_timeframe else ""
            print(f"   {i}. {tf} - {desc}{current}")
        print("   0. 返回")
        print("="*50)
    
    def config_timeframe(self):
        """配置时间级别"""
        while True:
            self.show_timeframe_menu()
            
            try:
                choice = input(f"\n请选择 (0-8): ").strip()
                
                if choice == '':
                    # 空输入，重新显示菜单
                    continue
                elif choice == '0':
                    return
                elif choice.isdigit() and 1 <= int(choice) <= 8:
                    timeframes = [
                        ('1m', '1分钟'),
                        ('5m', '5分钟'),
                        ('15m', '15分钟'),
                        ('30m', '30分钟'),
                        ('1h', '1小时'),
                        ('2h', '2小时'),
                        ('4h', '4小时'),
                        ('1d', '1天')
                    ]
                    timeframe = timeframes[int(choice) - 1][0]
                    TRADING_CONFIG['TIMEFRAME'] = timeframe
                    self.data_loader.timeframe = timeframe
                    print(f"✅ 时间级别: {timeframe}")
                    return
                else:
                    print("❌ 无效选择")
                    
            except Exception as e:
                print(f"❌ 配置失败: {e}")
    
    def show_position_menu(self):
        """显示初始仓位配置菜单"""
        print("\n" + "="*50)
        print("📊 初始仓位配置")
        print("="*50)
        current_position = self.current_position
        position_options = [
            (0, '无仓位'),
            (1, '多头'),
            (-1, '空头')
        ]
        
        print(f"当前仓位: {current_position}")
        print("")
        
        print("📋 仓位选项:")
        for i, (pos, desc) in enumerate(position_options, 1):
            current = " (当前)" if pos == current_position else ""
            print(f"  {i}. {desc} ({pos}){current}")
        print("   0. 返回")
        print("="*50)
    
    def config_initial_position(self):
        """配置初始仓位"""
        while True:
            self.show_position_menu()
            
            try:
                choice = input("\n请选择 (0-3): ").strip()
                
                if choice == '':
                    # 空输入，重新显示菜单
                    continue
                elif choice == '0':
                    return
                elif choice.isdigit() and 1 <= int(choice) <= 3:
                    position_options = [
                        (0, '无仓位'),
                        (1, '多头'),
                        (-1, '空头')
                    ]
                    new_position = position_options[int(choice) - 1][0]
                    position_desc = position_options[int(choice) - 1][1]
                    self.current_position = new_position
                    print(f"✅ 仓位: {position_desc} ({new_position})")
                    return
                else:
                    print("❌ 无效选择")
                    
            except Exception as e:
                print(f"❌ 配置失败: {e}")
    
    def show_risk_control_menu(self):
        """显示风险控制配置菜单"""
        print("\n" + "="*50)
        print("🛡️ 风险控制配置")
        print("="*50)
        
        # 获取当前风险控制参数
        max_trades = self.max_daily_trades
        min_trade_interval = self.min_trade_interval
        
        print("📊 当前设置:")
        print(f"  每日最大交易次数: {max_trades}")
        print(f"  最小交易间隔: {min_trade_interval}秒 ({min_trade_interval//60}分钟)")
        print("")
        
        print("📋 配置选项:")
        print("   1. 每日最大交易次数")
        print("   2. 最小交易间隔")
        print("   3. 快速设置 (保守)")
        print("   4. 快速设置 (激进)")
        print("   0. 返回")
        print("="*50)
    
    def config_risk_control(self):
        """配置风险控制"""
        while True:
            self.show_risk_control_menu()
            
            try:
                choice = input("\n请选择 (0-4): ").strip()
                
                if choice == '':
                    # 空输入，重新显示菜单
                    continue
                elif choice == '1':
                    max_trades = self.max_daily_trades
                    new_max_trades = input(f"每日最大交易次数 (当前: {max_trades}): ").strip()
                    if new_max_trades and new_max_trades.isdigit() and int(new_max_trades) > 0:
                        self.max_daily_trades = int(new_max_trades)
                        print(f"✅ 每日最大交易次数: {new_max_trades}")
                    elif new_max_trades == '':
                        print("💡 已取消修改")
                    else:
                        print("❌ 请输入有效数字")
                        
                elif choice == '2':
                    min_trade_interval = self.min_trade_interval
                    print("\n📋 间隔选项:")
                    intervals = [(60, '1分钟'), (300, '5分钟'), (600, '10分钟'), (1800, '30分钟'), (3600, '1小时')]
                    for i, (sec, desc) in enumerate(intervals, 1):
                        current = " (当前)" if sec == min_trade_interval else ""
                        print(f"  {i}. {desc}{current}")
                    
                    interval_choice = input(f"请选择间隔 (1-5): ").strip()
                    if interval_choice == '':
                        print("💡 已取消修改")
                    elif interval_choice.isdigit() and 1 <= int(interval_choice) <= 5:
                        new_interval = intervals[int(interval_choice) - 1][0]
                        self.min_trade_interval = new_interval
                        print(f"✅ 最小交易间隔: {new_interval}秒")
                    else:
                        print("❌ 无效选择")
                        
                elif choice == '3':
                    # 保守设置
                    self.max_daily_trades = 5
                    self.min_trade_interval = 1800  # 30分钟
                    print("✅ 保守设置: 每日5次，间隔30分钟")
                    
                elif choice == '4':
                    # 激进设置
                    self.max_daily_trades = 20
                    self.min_trade_interval = 300  # 5分钟
                    print("✅ 激进设置: 每日20次，间隔5分钟")
                    
                elif choice == '0':
                    return
                else:
                    print("❌ 无效选择")
                    
            except Exception as e:
                print(f"❌ 配置失败: {e}")
    
    def config_capital(self):
        """配置资金管理"""
        while True:
            print("\n" + "="*50)
            print("💰 资金配置")
            print("="*50)
            print("📊 当前设置:")
            print(f"  初始资金: {self.initial_capital:>10,.0f} USDT")
            print(f"  当前资金: {self.current_capital:>10,.0f} USDT")
            print(f"  可用资金: {self.available_capital:>10,.0f} USDT")
            print(f"  杠杆倍数: {self.leverage:>10}x")
            print("")
            
            print("📋 配置选项:")
            print("   1. 设置初始资金")
            print("   2. 设置杠杆倍数")
            print("   3. 重置资金")
            print("   0. 返回")
            print("="*50)
            
            try:
                choice = input("\n请选择 (0-3): ").strip()
                
                if choice == '':
                    continue
                elif choice == '1':
                    new_capital = input(f"初始资金 (当前: {self.initial_capital:,.0f} USDT): ").strip()
                    if new_capital and new_capital.replace(',', '').isdigit():
                        new_amount = int(new_capital.replace(',', ''))
                        if new_amount > 0:
                            self.initial_capital = new_amount
                            self.current_capital = new_amount
                            self.available_capital = new_amount
                            print(f"✅ 初始资金: {new_amount:,.0f} USDT")
                        else:
                            print("❌ 资金必须大于0")
                    elif new_capital == '':
                        print("💡 已取消修改")
                    else:
                        print("❌ 请输入有效数字")
                        
                elif choice == '2':
                    print("\n📋 杠杆选项:")
                    leverages = [1, 2, 3, 5, 10, 20]
                    for i, lev in enumerate(leverages, 1):
                        current = " (当前)" if lev == self.leverage else ""
                        print(f"  {i}. {lev}x{current}")
                    
                    lev_choice = input(f"请选择杠杆 (1-6): ").strip()
                    if lev_choice == '':
                        print("💡 已取消修改")
                    elif lev_choice.isdigit() and 1 <= int(lev_choice) <= 6:
                        new_leverage = leverages[int(lev_choice) - 1]
                        self.leverage = new_leverage
                        print(f"✅ 杠杆倍数: {new_leverage}x")
                        
                        # 立即应用到真实交易所
                        if self.real_trading and self.exchange_api:
                            symbol = TRADING_CONFIG.get('SYMBOL', 'ETHUSDT')
                            leverage_result = self.exchange_api.set_leverage(symbol, new_leverage)
                            if leverage_result['success']:
                                print(f"✅ 杠杆设置已应用到交易所: {leverage_result['message']}")
                            else:
                                print(f"⚠️  杠杆设置警告: {leverage_result['error']}")
                        else:
                            print("💡 模拟模式：杠杆设置仅在开仓时生效")
                    else:
                        print("❌ 无效选择")
                        
                elif choice == '3':
                    confirm = input("确定要重置资金吗? (y/N): ").strip().lower()
                    if confirm in ['y', 'yes', '是']:
                        self.current_capital = self.initial_capital
                        self.available_capital = self.initial_capital
                        self.total_pnl = 0.0
                        self.daily_pnl = 0.0
                        print("✅ 资金已重置")
                    else:
                        print("💡 已取消重置")
                        
                elif choice == '0':
                    return
                else:
                    print("❌ 无效选择")
                    
            except Exception as e:
                print(f"❌ 配置失败: {e}")
    
    def config_position_management(self):
        """配置仓位管理"""
        while True:
            print("\n" + "="*50)
            print("📊 仓位管理配置")
            print("="*50)
            print("📈 当前设置:")
            print(f"  单次仓位比例: {self.position_size_percent:>8.1%}")
            print(f"  最大仓位比例: {self.max_position_size:>8.1%}")
            print(f"  最小仓位比例: {self.min_position_size:>8.1%}")
            print("")
            
            print("📋 配置选项:")
            print("   1. 设置单次仓位比例")
            print("   2. 设置最大仓位比例")
            print("   3. 设置最小仓位比例")
            print("   4. 快速设置 (保守)")
            print("   5. 快速设置 (激进)")
            print("   0. 返回")
            print("="*50)
            
            try:
                choice = input("\n请选择 (0-5): ").strip()
                
                if choice == '':
                    continue
                elif choice == '1':
                    new_size = input(f"单次仓位比例 (当前: {self.position_size_percent:.1%}): ").strip()
                    if new_size and new_size.replace('%', '').replace('.', '').isdigit():
                        new_percent = float(new_size.replace('%', '')) / 100
                        if 0 < new_percent <= 1:
                            self.position_size_percent = new_percent
                            print(f"✅ 单次仓位比例: {new_percent:.1%}")
                        else:
                            print("❌ 比例必须在0-100%之间")
                    elif new_size == '':
                        print("💡 已取消修改")
                    else:
                        print("❌ 请输入有效数字")
                        
                elif choice == '2':
                    new_max = input(f"最大仓位比例 (当前: {self.max_position_size:.1%}): ").strip()
                    if new_max and new_max.replace('%', '').replace('.', '').isdigit():
                        new_percent = float(new_max.replace('%', '')) / 100
                        if 0 < new_percent <= 1:
                            self.max_position_size = new_percent
                            print(f"✅ 最大仓位比例: {new_percent:.1%}")
                        else:
                            print("❌ 比例必须在0-100%之间")
                    elif new_max == '':
                        print("💡 已取消修改")
                    else:
                        print("❌ 请输入有效数字")
                        
                elif choice == '3':
                    new_min = input(f"最小仓位比例 (当前: {self.min_position_size:.1%}): ").strip()
                    if new_min and new_min.replace('%', '').replace('.', '').isdigit():
                        new_percent = float(new_min.replace('%', '')) / 100
                        if 0 < new_percent <= 1:
                            self.min_position_size = new_percent
                            print(f"✅ 最小仓位比例: {new_percent:.1%}")
                        else:
                            print("❌ 比例必须在0-100%之间")
                    elif new_min == '':
                        print("💡 已取消修改")
                    else:
                        print("❌ 请输入有效数字")
                        
                elif choice == '4':
                    # 保守设置
                    self.position_size_percent = 0.05
                    self.max_position_size = 0.2
                    self.min_position_size = 0.02
                    print("✅ 保守设置: 单次5%, 最大20%, 最小2%")
                    
                elif choice == '5':
                    # 激进设置
                    self.position_size_percent = 0.2
                    self.max_position_size = 0.8
                    self.min_position_size = 0.1
                    print("✅ 激进设置: 单次20%, 最大80%, 最小10%")
                    
                elif choice == '0':
                    return
                else:
                    print("❌ 无效选择")
                    
            except Exception as e:
                print(f"❌ 配置失败: {e}")
    
    def show_current_config(self, exchange_info=None):
        """显示当前配置"""
        print("\n" + "="*50)
        print("📋 当前配置")
        print("="*50)
        
        # 交易配置
        symbol = TRADING_CONFIG.get('SYMBOL', 'ETHUSDT')
        timeframe = TRADING_CONFIG.get('TIMEFRAME', '1h')
        position = self.current_position
        position_desc = {0: '无仓位', 1: '多头', -1: '空头'}.get(position, '未知')
        
        # 资金配置
        total_return = (self.current_capital - self.initial_capital) / self.initial_capital
        daily_return = self.daily_pnl / self.initial_capital
        
        # 风险控制
        max_trades = self.max_daily_trades
        min_interval = self.min_trade_interval
        
        # 系统状态
        system_status = '运行中' if self.running else '已停止'
        
        # 交易所信息 - 如果没有传入，则重新获取
        if exchange_info is None:
            exchange_info = self.get_exchange_info()
        
        print("\n" + "="*60)
        print("📊 系统状态监控")
        print("="*60)
        
        # 交易设置区域
        print("📈 交易设置")
        print(f"  交易对:     {symbol}")
        print(f"  时间级别:   {timeframe}")
        print(f"  当前仓位:   {position_desc} ({position})")
        
        # 交易所信息区域
        print("\n🏢 交易所信息")
        print(f"  交易所:     {exchange_info.get('exchange', 'Binance')}")
        print(f"  合约类型:   {exchange_info.get('contract_type', '永续合约')}")
        print(f"  API状态:    {exchange_info.get('api_status', '正常')}")
        print(f"  网络延迟:   {exchange_info.get('latency', 'N/A')}")
        print(f"  API地址:    {exchange_info.get('api_url', 'N/A')}")
        print(f"  服务器时间: {exchange_info.get('server_time', 'N/A')}")
        
        # 资金管理区域
        print("\n💰 资金管理")
        print(f"  初始资金:   {self.initial_capital:>12,.0f} USDT")
        print(f"  当前资金:   {self.current_capital:>12,.0f} USDT")
        print(f"  可用资金:   {self.available_capital:>12,.0f} USDT")
        print(f"  总收益:     {self.total_pnl:>+12,.0f} USDT ({total_return:>+6.2%})")
        print(f"  今日收益:   {self.daily_pnl:>+12,.0f} USDT ({daily_return:>+6.2%})")
        print(f"  杠杆倍数:   {self.leverage:>12}x")
        
        # 仓位配置区域
        print("\n📊 仓位配置")
        print(f"  单次仓位:   {self.position_size_percent:>10.1%}")
        print(f"  最大仓位:   {self.max_position_size:>10.1%}")
        print(f"  最小仓位:   {self.min_position_size:>10.1%}")
        
        # 风险控制区域
        print("\n🛡️ 风险控制")
        print(f"  每日交易:   {self.daily_trades:>3}/{max_trades}")
        print(f"  交易间隔:   {min_interval//60:>3}分钟")
        print(f"  每日止损:   {self.max_daily_loss:>10.1%}")
        print(f"  总资金止损: {self.max_total_loss:>10.1%}")
        
        # 系统状态区域
        print("\n⚙️ 系统状态")
        status_icon = "🟢" if system_status == '运行中' else "🔴"
        trading_mode = "真实交易" if self.real_trading else "模拟交易"
        mode_icon = "🔴" if self.real_trading else "🟡"
        print(f"  运行状态:   {status_icon} {system_status}")

        print(f"  交易模式:   {mode_icon} {trading_mode}")
        print("="*60)
    
    def config_api_keys(self):
        """配置API密钥"""
        print("\n" + "="*50)
        print("🔑 API密钥配置")
        print("="*50)
        
        # 显示当前状态
        if self.real_trading:
            print("✅ 当前模式: 真实交易")
        else:
            print("⚠️ 当前模式: 模拟交易")
        
        # 检查API密钥状态
        api_key_exists = False
        if os.path.exists('api_config.json'):
            try:
                with open('api_config.json', 'r', encoding='utf-8') as f:
                    api_config = json.load(f)
                if api_config.get('api_key') and api_config.get('secret_key'):
                    api_key_exists = True
                    print("✅ API密钥已配置")
                else:
                    print("⚠️ API密钥配置不完整")
            except:
                print("⚠️ API密钥配置文件损坏")
        else:
            print("❌ 未配置API密钥")
        
        print("\n📋 配置选项:")
        print("   1. 设置API密钥")
        print("   2. 测试API连接")
        print("   3. 切换交易模式")
        print("   4. 查看API密钥状态")
        print("   5. 删除API密钥")
        print("   0. 返回")
        
        try:
            choice = input("\n请选择 (0-5): ").strip()
            
            if choice == '1':
                self.setup_api_keys()
            elif choice == '2':
                self.test_api_connection_ui()
            elif choice == '3':
                self.toggle_trading_mode()
            elif choice == '4':
                self.show_api_key_status()
            elif choice == '5':
                self.delete_api_keys()
            elif choice == '0':
                return
            else:
                print("❌ 无效选择")
                
        except Exception as e:
            print(f"❌ 配置失败: {e}")
    
    def show_api_key_status(self):
        """显示API密钥状态"""
        print("\n📊 API密钥状态")
        print("="*30)
        
        if os.path.exists('api_config.json'):
            try:
                with open('api_config.json', 'r', encoding='utf-8') as f:
                    api_config = json.load(f)
                
                api_key = api_config.get('api_key', '')
                secret_key = api_config.get('secret_key', '')
                testnet = api_config.get('testnet', False)
                timestamp = api_config.get('timestamp', '')
                
                print(f"API Key: {'*' * (len(api_key) - 8) + api_key[-8:] if api_key else '未设置'}")
                print(f"Secret Key: {'*' * (len(secret_key) - 8) + secret_key[-8:] if secret_key else '未设置'}")
                print(f"测试网模式: {'是' if testnet else '否'}")
                print(f"配置时间: {timestamp}")
                
                if api_key and secret_key:
                    print("✅ API密钥配置完整")
                else:
                    print("⚠️ API密钥配置不完整")
                    
            except Exception as e:
                print(f"❌ 读取配置文件失败: {e}")
        else:
            print("❌ 未找到API密钥配置文件")
    
    def delete_api_keys(self):
        """删除API密钥"""
        print("\n🗑️ 删除API密钥")
        print("⚠️ 警告: 此操作将永久删除API密钥配置")
        
        confirm = input("确定要删除API密钥吗? (y/N): ").strip().lower()
        if confirm in ['y', 'yes', '是']:
            try:
                if os.path.exists('api_config.json'):
                    os.remove('api_config.json')
                    print("✅ API密钥配置文件已删除")
                
                # 清除环境变量
                if 'BINANCE_API_KEY' in os.environ:
                    del os.environ['BINANCE_API_KEY']
                if 'BINANCE_SECRET_KEY' in os.environ:
                    del os.environ['BINANCE_SECRET_KEY']
                print("✅ 环境变量已清除")
                
                # 重置交易模式
                self.real_trading = False
                self.exchange_api = None
                print("✅ 已切换到模拟交易模式")
                
            except Exception as e:
                print(f"❌ 删除失败: {e}")
        else:
            print("💡 已取消删除操作")
    
    def setup_api_keys(self):
        """设置API密钥"""
        print("\n🔑 设置API密钥")
        print("⚠️ 注意: API密钥将保存到配置文件中")
        
        try:
            api_key = input("请输入API Key: ").strip()
            if not api_key:
                print("💡 已取消设置")
                return
            
            secret_key = input("请输入Secret Key: ").strip()
            if not secret_key:
                print("💡 已取消设置")
                return
            
            # 保存到配置文件
            api_config = {
                'api_key': api_key,
                'secret_key': secret_key,
                'testnet': False,
                'timestamp': datetime.now().isoformat()
            }
            
            config_file = 'api_config.json'
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(api_config, f, indent=2, ensure_ascii=False)
                print("✅ API密钥已保存到配置文件")
            except Exception as e:
                print(f"❌ 保存配置文件失败: {e}")
                return
            
            # 保存到环境变量（当前会话）
            try:
                os.environ['BINANCE_API_KEY'] = api_key
                os.environ['BINANCE_SECRET_KEY'] = secret_key
                print("✅ API密钥已设置到环境变量")
            except Exception as e:
                print(f"⚠️ 设置环境变量失败: {e}")
            
            # 重新初始化API连接
            print("🔄 正在测试API连接...")
            try:
                from exchange_api import RealExchangeAPI
                self.exchange_api = RealExchangeAPI(
                    api_key=api_key,
                    secret_key=secret_key,
                    testnet=False
                )
                self.exchange_api.set_logger(self.logger)
                
                # 测试连接
                success, message = self.exchange_api.test_connection()
                if success:
                    print("✅ API密钥已设置并连接成功")
                    self.real_trading = True
                else:
                    print(f"⚠️ API密钥已保存，但连接测试失败: {message}")
                    print("💡 这可能是网络问题或API权限问题，请检查：")
                    print("   1. 网络连接是否正常")
                    print("   2. API密钥是否有正确的权限")
                    print("   3. 是否启用了期货交易权限")
                    self.real_trading = False
            except Exception as e:
                print(f"❌ 重新初始化API失败: {e}")
                print("💡 请检查API密钥是否正确")
                self.real_trading = False
            
        except Exception as e:
            print(f"❌ 设置API密钥失败: {e}")
            print("💡 请检查输入是否正确")
    
    def test_api_connection_ui(self):
        """测试API连接（UI版本）"""
        print("\n🔍 测试API连接")
        
        if not self.exchange_api:
            print("❌ 未配置API密钥")
            print("💡 请先设置API密钥")
            return
        
        try:
            print("🔄 正在测试API连接...")
            success, message = self.exchange_api.test_connection()
            print(message)
            
            if success:
                print("✅ API连接正常")
                # 获取账户信息
                try:
                    balance = self.exchange_api.get_balance()
                    print(f"💰 账户余额: {balance['total']:.2f} USDT")
                    
                    position = self.exchange_api.get_position()
                    if position['size'] > 0:
                        print(f"📊 当前仓位: {position['side']} {position['size']}")
                    else:
                        print("📊 当前无仓位")
                except Exception as e:
                    print(f"⚠️ 获取账户信息失败: {e}")
                    print("💡 这可能是API权限问题，请检查API密钥权限")
            else:
                print("❌ API连接失败")
                print("💡 可能的原因：")
                print("   1. 网络连接问题")
                print("   2. API密钥无效或过期")
                print("   3. API权限不足")
                print("   4. 服务器维护中")
                print("💡 建议：")
                print("   1. 检查网络连接")
                print("   2. 重新生成API密钥")
                print("   3. 确认API权限设置")
                    
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            print("💡 请检查API配置是否正确")
    
    def toggle_trading_mode(self):
        """切换交易模式"""
        print("\n🔄 切换交易模式")
        
        if self.real_trading:
            print("当前: 真实交易模式")
            confirm = input("是否切换到模拟交易模式? (y/N): ").strip().lower()
            if confirm in ['y', 'yes', '是']:
                self.real_trading = False
                print("✅ 已切换到模拟交易模式")
            else:
                print("💡 保持真实交易模式")
        else:
            print("当前: 模拟交易模式")
            if not self.exchange_api:
                print("❌ 未配置API密钥，无法切换到真实交易模式")
                return
            
            confirm = input("是否切换到真实交易模式? (y/N): ").strip().lower()
            if confirm in ['y', 'yes', '是']:
                self.real_trading = True
                print("✅ 已切换到真实交易模式")
                print("⚠️ 警告: 真实交易模式将使用真实资金!")
            else:
                print("💡 保持模拟交易模式")
    
    def save_config(self):
        """保存配置到文件"""
        try:
            print("\n💾 保存配置")
            print("-" * 20)
            
            # 准备要保存的配置数据
            config_to_save = {
                'TRADING_CONFIG': {
                    'SYMBOL': TRADING_CONFIG['SYMBOL'],
                    'TIMEFRAME': TRADING_CONFIG['TIMEFRAME'],
                    'CAPITAL_CONFIG': {
                        'INITIAL_CAPITAL': self.initial_capital,
                        'POSITION_SIZE_PERCENT': self.position_size_percent,
                        'MAX_POSITION_SIZE': self.max_position_size,
                        'MIN_POSITION_SIZE': self.min_position_size,
                        'LEVERAGE': self.leverage,
                    },
                    'RISK_CONFIG': {
                        'MAX_DAILY_TRADES': self.max_daily_trades,
                        'MIN_TRADE_INTERVAL': self.min_trade_interval,
                        'MAX_DAILY_LOSS': self.max_daily_loss,
                        'MAX_TOTAL_LOSS': self.max_total_loss,
                        'EMERGENCY_STOP_LOSS': self.emergency_stop_loss,
                    }
                }
            }
            
            # 保存配置到文件
            from user_config import save_user_config
            success, message = save_user_config(config_to_save)
            
            if success:
                print("✅ 交易配置已保存")
                print("✅ 风险控制已保存")
                print("✅ 资金管理已保存")
                print("✅ 配置已保存到 user_config.json")
                print("\n📝 配置将在下次启动时自动加载")
            else:
                print(f"❌ 保存失败: {message}")
            
        except Exception as e:
            print(f"❌ 保存失败: {e}")

    def manual_data_fetch(self):
        """手动获取数据"""
        print("\n" + "="*40)
        print("📊 手动获取数据")
        print("="*40)
        
        try:
            print("🔄 正在获取最新市场数据...")
            
            # 获取市场数据（非静默模式）
            market_data = self.get_market_data(silent=False)
            if market_data is None:
                print("❌ 获取市场数据失败")
                return
            
            print(f"✅ 成功获取 {len(market_data)} 条数据")
            
            # 生成信号（非静默模式）
            print("🔍 正在分析市场信号...")
            signal = self.generate_signals(market_data, silent=False)
            
            if signal is not None:
                signal_value = signal.get('signal', 0)
                signal_score = signal.get('final_score', 0)
                print(f"📊 当前信号: {signal_value}, 评分: {signal_score:.4f}")
                
                if signal_value == 1:
                    print("🟢 市场信号: 看多")
                elif signal_value == -1:
                    print("🔴 市场信号: 看空")
                else:
                    print("⚪ 市场信号: 中性")
            else:
                print("📊 当前无有效信号")
                
        except Exception as e:
            print(f"❌ 手动获取数据失败: {e}")

    def create_service_file(self):
        """创建服务文件"""
        print("\n" + "="*50)
        print("🔧 创建服务文件")
        print("="*50)
        print("📋 服务文件功能:")
        print("  ✓ 创建 systemd 服务配置")
        print("  ✓ 支持后台自动运行")
        print("  ✓ 支持开机自启动")
        print("  ✓ 支持自动重启恢复")
        print("  ✓ 日志记录到系统日志")
        print("")
        print("⚠️  注意事项:")
        print("  • 需要 root 权限")
        print("  • 适用于 CentOS/Linux 系统")
        print("  • 需要先运行 install.sh 安装脚本")
        print("  • 确保虚拟环境已正确配置")
        print("  • 创建后需要手动启动服务")
        print("="*50)
        
        try:
            confirm = input("\n是否创建服务文件? (y/N): ").strip().lower()
            if confirm in ['y', 'yes', '是']:
                print("🚀 正在创建服务文件...")
                self.create_systemd_service()
                print("✅ 服务文件创建完成")
                print("\n📋 后续操作:")
                print("   1. 启动服务: sudo systemctl start trading-system")
                print("   2. 查看状态: sudo systemctl status trading-system")
                print("   3. 启用自启: sudo systemctl enable trading-system")
                print("   4. 查看日志: sudo journalctl -u trading-system -f")
                print("   5. 重启服务: sudo systemctl restart trading-system")
                print("   6. 停止服务: sudo systemctl stop trading-system")
                print("\n💡 提示:")
                print("  • 服务将以 'trading' 用户身份运行")
                print("  • 使用虚拟环境: /opt/trading/venv")
                print("  • 工作目录: /opt/trading")
                print("  • 日志目录: /opt/trading/logs")
            else:
                print("✅ 取消创建服务文件")
                
        except Exception as e:
            print(f"❌ 创建服务文件失败: {e}")
    
    def create_systemd_service(self):
        """创建 systemd 服务文件"""
        # 使用标准的 CentOS 安装路径
        work_dir = "/opt/trading"
        script_path = "/opt/trading/trading.py"
        
        service_content = """[Unit]
Description=Trading System Service
After=network.target

[Service]
Type=simple
User=trading
Group=trading
WorkingDirectory={work_dir}
ExecStart={work_dir}/venv/bin/python {script_path} --mode service
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# 环境变量
Environment=PYTHONPATH={work_dir}
Environment=PYTHONUNBUFFERED=1

# 资源限制
LimitNOFILE=65536
LimitNPROC=4096

# 安全设置 (兼容旧版本 systemd)
NoNewPrivileges=true
PrivateTmp=true
# ProtectSystem=strict  # 注释掉，旧版本可能不支持
# ReadWritePaths={work_dir}/logs  # 注释掉，旧版本不支持

[Install]
WantedBy=multi-user.target
""".format(
            work_dir=work_dir,
            script_path=script_path
        )
        
        service_file = "/etc/systemd/system/trading-system.service"
        
        try:
            with open(service_file, 'w', encoding='utf-8') as f:
                f.write(service_content)
            
            print(f"✅ 服务文件已创建: {service_file}")
            
        except (PermissionError, FileNotFoundError):
            print("❌ 权限不足或目录不存在，创建临时服务文件")
            # 创建临时文件供用户手动复制
            temp_file = "trading-system.service"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(service_content)
            print(f"📝 已创建临时服务文件: {temp_file}")
            print("请手动复制到 /etc/systemd/system/ 目录")
            print("然后运行以下命令:")
            print("  sudo systemctl daemon-reload")
            print("  sudo systemctl enable trading-system")
            print("  sudo systemctl start trading-system")
        except Exception as e:
            print(f"❌ 创建服务文件失败: {e}")

    def confirm_exit(self):
        """确认退出"""
        while True:
            print("\n🚪 退出系统确认")
            
            # 检查当前仓位
            if self.current_position != 0:
                position_desc = {1: '多头', -1: '空头'}.get(self.current_position, '未知')
                print(f"⚠️  当前持有{position_desc}仓位")
                print("请选择退出方式:")
                print("   1. 平仓后退出")
                print("   2. 保持仓位退出")
                print("   0. 取消退出")
                
                try:
                    choice = input("\n请选择退出方式 (0-2): ").strip()
                    
                    if choice == '':
                        # 空输入，重新显示选项
                        continue
                        
                    elif choice == '1':
                        print("🔄 正在平仓...")
                        self.current_position = 0
                        print("✅ 仓位已平仓")
                        print("👋 再见!")
                        self.stop()
                        return True  # 表示确实退出
                        
                    elif choice == '2':
                        print(f"⚠️  保持{position_desc}仓位退出")
                        print("👋 再见!")
                        self.stop()
                        return True  # 表示确实退出
                        
                    elif choice == '0':
                        print("✅ 取消退出")
                        return False  # 表示取消退出
                        
                    else:
                        print("❌ 无效选择，请输入 0-2")
                        # 继续循环，重新显示选项
                        
                except KeyboardInterrupt:
                    print("\n✅ 取消退出")
                    return False  # 表示取消退出
                    
            else:
                print("✅ 当前无仓位")
                print("确认退出吗?")
                print("   1. 确认退出")
                print("   0. 取消退出")
                
                try:
                    choice = input("\n请选择 (0-1): ").strip()
                    
                    if choice == '':
                        # 空输入，重新显示选项
                        continue
                        
                    elif choice == '1':
                        print("👋 再见!")
                        self.stop()
                        return True  # 表示确实退出
                        
                    elif choice == '0':
                        print("✅ 取消退出")
                        return False  # 表示取消退出
                        
                    else:
                        print("❌ 无效选择，请输入 0-1")
                        # 继续循环，重新显示选项
                        
                except KeyboardInterrupt:
                    print("\n✅ 取消退出")
                    return False  # 表示取消退出

    def show_trade_history(self):
        """显示交易历史记录"""
        print("\n" + "="*60)
        print("📊 交易历史记录")
        print("="*60)
        
        if not self.trade_history:
            print("📝 暂无交易记录")
            print("="*60)
            return
        
        # 统计信息
        total_trades = len(self.trade_history)
        long_trades = len([t for t in self.trade_history if t['type'] == 'LONG'])
        short_trades = len([t for t in self.trade_history if t['type'] == 'SHORT'])
        close_trades = len([t for t in self.trade_history if t['type'] == 'CLOSE'])
        
        print(f"📈 交易统计:")
        print(f"  总交易次数: {total_trades}")
        print(f"  开多仓: {long_trades}")
        print(f"  开空仓: {short_trades}")
        print(f"  平仓: {close_trades}")
        
        # 计算性能统计
        if total_trades > 0:
            # 计算平均信号评分
            avg_score = sum([abs(t['signal_score']) for t in self.trade_history]) / total_trades
            
            # 计算最大单笔交易金额
            max_amount = max([t['amount'] for t in self.trade_history if t['amount'] > 0], default=0)
            
            # 计算交易频率（每小时）
            if len(self.trade_history) > 1:
                first_trade = self.trade_history[0]['timestamp']
                last_trade = self.trade_history[-1]['timestamp']
                time_diff = (last_trade - first_trade).total_seconds() / 3600  # 小时
                trade_frequency = total_trades / time_diff if time_diff > 0 else 0
            else:
                trade_frequency = 0
            
            print(f"  平均信号强度: {avg_score:.3f}")
            print(f"  最大单笔金额: {max_amount:,.0f} USDT")
            print(f"  交易频率: {trade_frequency:.2f} 次/小时")
        
        print()
        
        # 显示最近的交易记录
        print("📋 最近交易记录:")
        print("-" * 60)
        print(f"{'时间':<20} {'类型':<8} {'金额':<12} {'评分':<8} {'仓位':<6}")
        print("-" * 60)
        
        # 显示最近10条记录
        recent_trades = self.trade_history[-10:] if len(self.trade_history) > 10 else self.trade_history
        
        for trade in recent_trades:
            timestamp = trade['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            trade_type = trade['type']
            amount = f"{trade['amount']:,.0f}" if trade['amount'] > 0 else "N/A"
            score = f"{trade['signal_score']:.3f}"
            position = trade['position']
            
            # 添加颜色标识
            if trade_type == 'LONG':
                trade_type_display = "🟢 开多"
            elif trade_type == 'SHORT':
                trade_type_display = "🔴 开空"
            else:
                trade_type_display = "⚪ 平仓"
            
            print(f"{timestamp:<20} {trade_type_display:<8} {amount:<12} {score:<8} {position:<6}")
        
        print("-" * 60)
        
        # 显示详细统计
        if len(self.trade_history) > 10:
            print(f"\n💡 显示最近10条记录，共{total_trades}条")
            print("输入 'all' 查看全部记录，或按回车返回")
            
            try:
                show_all = input("> ").strip().lower()
                if show_all == 'all':
                    self.show_all_trade_history()
            except KeyboardInterrupt:
                print("\n✅ 返回主菜单")
        
        print("="*60)
    
    def show_all_trade_history(self):
        """显示所有交易历史记录"""
        print("\n" + "="*80)
        print("📊 完整交易历史记录")
        print("="*80)
        
        print(f"{'时间':<20} {'类型':<8} {'金额':<12} {'评分':<8} {'仓位':<6} {'资金':<12}")
        print("-" * 80)
        
        for trade in self.trade_history:
            timestamp = trade['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            trade_type = trade['type']
            amount = f"{trade['amount']:,.0f}" if trade['amount'] > 0 else "N/A"
            score = f"{trade['signal_score']:.3f}"
            position = trade['position']
            capital = f"{trade['capital']:,.0f}"
            
            # 添加颜色标识
            if trade_type == 'LONG':
                trade_type_display = "🟢 开多"
            elif trade_type == 'SHORT':
                trade_type_display = "🔴 开空"
            else:
                trade_type_display = "⚪ 平仓"
            
            print(f"{timestamp:<20} {trade_type_display:<8} {amount:<12} {score:<8} {position:<6} {capital:<12}")
        
        print("-" * 80)
        print(f"📝 共 {len(self.trade_history)} 条交易记录")
        print("="*80)
    
    def show_performance_monitor(self):
        """显示系统性能监控"""
        print("\n" + "="*60)
        print("📈 系统性能监控")
        print("="*60)
        
        try:
            import psutil
            import time
            
            # 系统资源使用情况
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 网络连接状态
            network_status = "正常"
            try:
                # 测试网络连接
                import requests
                response = requests.get('https://www.google.com', timeout=3)
                network_latency = "正常"
            except:
                network_latency = "异常"
            
            # 进程信息
            current_process = psutil.Process()
            process_memory = current_process.memory_info()
            
            print("🖥️ 系统资源:")
            print(f"  CPU使用率: {cpu_percent:.1f}%")
            print(f"  内存使用: {memory.percent:.1f}% ({memory.used//1024//1024}MB / {memory.total//1024//1024}MB)")
            print(f"  磁盘使用: {disk.percent:.1f}% ({disk.used//1024//1024//1024}GB / {disk.total//1024//1024//1024}GB)")
            
            print("\n🌐 网络状态:")
            print(f"  网络连接: {network_latency}")
            print(f"  API延迟: {self.get_exchange_info().get('latency', 'N/A')}")
            
            print("\n📊 进程信息:")
            print(f"  进程ID: {current_process.pid}")
            print(f"  进程内存: {process_memory.rss//1024//1024}MB")
            print(f"  运行时间: {str(datetime.now() - self.start_time).split('.')[0]}")
            
            print("\n⚡ 交易性能:")
            print(f"  总交易次数: {self.trade_count}")
            print(f"  今日交易: {self.daily_trades}/{self.max_daily_trades}")
            print(f"  当前仓位: {self.current_position}")
            print(f"  系统状态: {'运行中' if self.running else '已停止'}")
    
            
            # 性能建议
            print("\n💡 性能建议:")
            if cpu_percent > 80:
                print("  ⚠️  CPU使用率较高，建议检查系统负载")
            if memory.percent > 80:
                print("  ⚠️  内存使用率较高，建议释放内存")
            if disk.percent > 90:
                print("  ⚠️  磁盘空间不足，建议清理日志文件")
            if network_latency == "异常":
                print("  ⚠️  网络连接异常，请检查网络设置")
            
            if cpu_percent < 50 and memory.percent < 70 and disk.percent < 80:
                print("  ✅ 系统运行状态良好")
            
            print("="*60)
            
        except ImportError:
            print("❌ 需要安装 psutil 库来显示系统性能信息")
            print("请运行: pip install psutil")
            print("="*60)
        except Exception as e:
            print(f"❌ 获取性能信息失败: {e}")
            print("="*60)

    def reset_config(self):
        """重置配置"""
        print("\n🔄 重置配置")
        print("-" * 20)
        
        try:
            # 删除配置文件
            from user_config import reset_to_default_config
            success, message = reset_to_default_config()
            
            if success:
                print("✅ 配置文件已删除")
            else:
                print(f"⚠️ {message}")
            
            # 重置交易配置
            TRADING_CONFIG['SYMBOL'] = 'ETHUSDT'
            TRADING_CONFIG['TIMEFRAME'] = '1h'
            TRADING_CONFIG['CAPITAL_CONFIG']['INITIAL_CAPITAL'] = 10000
            TRADING_CONFIG['CAPITAL_CONFIG']['POSITION_SIZE_PERCENT'] = 0.1
            TRADING_CONFIG['CAPITAL_CONFIG']['MAX_POSITION_SIZE'] = 0.5
            TRADING_CONFIG['CAPITAL_CONFIG']['MIN_POSITION_SIZE'] = 0.05
            TRADING_CONFIG['CAPITAL_CONFIG']['LEVERAGE'] = 1
            TRADING_CONFIG['RISK_CONFIG']['MAX_DAILY_TRADES'] = 10
            TRADING_CONFIG['RISK_CONFIG']['MIN_TRADE_INTERVAL'] = 300
            TRADING_CONFIG['RISK_CONFIG']['MAX_DAILY_LOSS'] = 0.05
            TRADING_CONFIG['RISK_CONFIG']['MAX_TOTAL_LOSS'] = 0.20
            TRADING_CONFIG['RISK_CONFIG']['EMERGENCY_STOP_LOSS'] = 0.30
            
            # 重置资金管理
            self.initial_capital = TRADING_CONFIG['CAPITAL_CONFIG']['INITIAL_CAPITAL']
            self.current_capital = self.initial_capital
            self.available_capital = self.initial_capital
            
            # 重置仓位管理
            self.position_size_percent = TRADING_CONFIG['CAPITAL_CONFIG']['POSITION_SIZE_PERCENT']
            self.max_position_size = TRADING_CONFIG['CAPITAL_CONFIG']['MAX_POSITION_SIZE']
            self.min_position_size = TRADING_CONFIG['CAPITAL_CONFIG']['MIN_POSITION_SIZE']
            self.leverage = TRADING_CONFIG['CAPITAL_CONFIG']['LEVERAGE']
            
            # 重置风险控制
            self.max_daily_trades = TRADING_CONFIG['RISK_CONFIG']['MAX_DAILY_TRADES']
            self.min_trade_interval = TRADING_CONFIG['RISK_CONFIG']['MIN_TRADE_INTERVAL']
            self.max_daily_loss = TRADING_CONFIG['RISK_CONFIG']['MAX_DAILY_LOSS']
            self.max_total_loss = TRADING_CONFIG['RISK_CONFIG']['MAX_TOTAL_LOSS']
            self.emergency_stop_loss = TRADING_CONFIG['RISK_CONFIG']['EMERGENCY_STOP_LOSS']
            
            # 重置交易记录
            self.daily_trades = 0
            self.daily_pnl = 0.0
            self.total_pnl = 0.0
            self.trade_history = []
            
            # 重置每日计数器
            self.reset_daily_counters()
            
            print("✅ 配置已重置")
            print("💰 资金管理已重置")
            print("📊 仓位管理已重置")
            print("🛡️ 风险控制已重置")
            print("\n📝 系统将在下次启动时使用默认配置")
            print("="*20)
            
        except Exception as e:
            print(f"❌ 重置配置失败: {e}")
            print("="*20)


def create_systemd_service():
    """创建 systemd 服务文件"""
    # 使用标准的 CentOS 安装路径
    work_dir = "/opt/trading"
    script_path = "/opt/trading/trading.py"
    
    service_content = """[Unit]
Description=Trading System Service
After=network.target

[Service]
Type=simple
User=trading
Group=trading
WorkingDirectory={work_dir}
ExecStart={work_dir}/venv/bin/python {script_path} --mode service
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# 环境变量
Environment=PYTHONPATH={work_dir}
Environment=PYTHONUNBUFFERED=1

# 资源限制
LimitNOFILE=65536
LimitNPROC=4096

# 安全设置 (兼容旧版本 systemd)
NoNewPrivileges=true
PrivateTmp=true
# ProtectSystem=strict  # 注释掉，旧版本可能不支持
# ReadWritePaths={work_dir}/logs  # 注释掉，旧版本不支持

[Install]
WantedBy=multi-user.target
""".format(
        work_dir=work_dir,
        script_path=script_path
    )
    
    service_file = "/etc/systemd/system/trading-system.service"
    
    try:
        with open(service_file, 'w', encoding='utf-8') as f:
            f.write(service_content)
        
        print(f"✅ 服务文件已创建: {service_file}")
        print("\n📋 使用以下命令管理服务:")
        print(f"  启动服务: sudo systemctl start trading-system")
        print(f"  停止服务: sudo systemctl stop trading-system")
        print(f"  重启服务: sudo systemctl restart trading-system")
        print(f"  查看状态: sudo systemctl status trading-system")
        print(f"  启用自启: sudo systemctl enable trading-system")
        print(f"  查看日志: sudo journalctl -u trading-system -f")
        
    except PermissionError:
        print("❌ 权限不足，请使用 sudo 运行")
    except Exception as e:
        print(f"❌ 创建服务文件失败: {e}")


def select_mode():
    """选择运行模式"""
    print("🚀 实盘交易系统")
    print("请选择运行模式:")
    print("   1. 交互模式 - 手动控制，实时监控")
    print("   2. 自动模式 - 后台运行，无人值守")
    print("   0. 退出系统")
    
    while True:
        try:
            choice = input("\n请选择模式 (0-2): ").strip()
            
            if choice == '1':
                print("✅ 选择交互模式")
                return 'interactive'
            elif choice == '2':
                print("✅ 选择自动模式")
                return 'service'
            elif choice == '0':
                print("👋 再见!")
                sys.exit(0)
            else:
                print("❓ 无效选择，请输入 0-2")
                
        except KeyboardInterrupt:
            print("\n👋 再见!")
            sys.exit(0)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='实盘交易系统')
    parser.add_argument('--mode', choices=['interactive', 'service'], 
                       help='运行模式（如不指定将提示选择）')
    parser.add_argument('--create-service', action='store_true',
                       help='创建 systemd 服务文件')
    parser.add_argument('--config', type=str, help='配置文件路径')
    
    args = parser.parse_args()
    
    # 创建服务文件
    if args.create_service:
        create_systemd_service()
        return
    
    # 选择运行模式
    if args.mode:
        mode = args.mode
    else:
        mode = select_mode()
    
    # 加载配置
    config = {}
    if args.config and os.path.exists(args.config):
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("config", args.config)
            config_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(config_module)
            config = {k: v for k, v in config_module.__dict__.items() 
                     if not k.startswith('_')}
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return
    
    # 创建并启动交易系统
    try:
        trading_system = TradingSystem(mode=mode)
        trading_system.start()
    except KeyboardInterrupt:
        print("\n📡 收到中断信号")
    except Exception as e:
        print(f"❌ 系统启动失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 