# -*- coding: utf-8 -*-
"""
量化交易回测器
============

本模块提供完整的量化交易策略回测功能，包括：
1. 多策略回测支持
2. 实时资金曲线跟踪
3. 详细的交易记录
4. 风险控制机制
5. 性能指标计算

主要功能：
- 支持多种策略的回测
- 实时计算资金曲线
- 详细的交易日志记录
- 风险控制和止损止盈
- 性能指标统计
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import logging

warnings.filterwarnings('ignore')

# 获取日志记录器
logger = logging.getLogger(__name__)


class Backtester:
    """
    量化交易回测器
    
    功能：
    - 执行策略回测
    - 管理仓位和资金
    - 计算性能指标
    - 记录交易日志
    """
    
    def __init__(self):
        """
        初始化回测器
        
        配置：
        - 初始资金：1000 USDT
        - 交易手续费：0.1%
        - 固定止损：5%（兜底机制）
        - 仓位倍数：1.0
        """
        # ===== 基础配置 =====
        self.initial_cash = 1000.0
        self.cash = 1000.0
        self.trading_fee = 0.001  # 0.1% 交易手续费
        
        # ===== 仓位管理 =====
        self.position = 0  # 当前仓位 (0=无仓位, 1=多仓, -1=空仓)
        self.entry_price = 0  # 开仓价格
        self.position_value = 0  # 仓位价值
        # 仓位管理已移至策略内部
        
        # ===== 交易统计 =====
        self.total_trades = 0  # 总交易次数
        self.profitable_trades = 0  # 盈利交易次数
        self.loss_trades = 0  # 亏损交易次数
        
        # ===== 资金曲线跟踪 =====
        self.total_assets = []  # 总资产历史
        self.asset_timestamps = []  # 资产时间戳
        self.trade_log = []  # 交易日志
        
        # ===== 止损和风险控制 =====
        self.high_point = 0  # 持仓期间最高点
        self.low_point = float('inf')  # 持仓期间最低点
     
    
    def calculate_position_value(self, current_price=None):
        """
        计算当前仓位价值
        
        Args:
            current_price: 当前价格，如果为None则返回原始仓位价值
            
        Returns:
            float: 当前仓位价值
        """
        if self.position == 0:
            return 0
        
        if current_price is None:
            return self.position_value
        
        # 根据当前价格计算实时仓位价值
        if self.position == 1:  # 多仓
            current_value = self.position_value * (current_price / self.entry_price)
        else:  # 空仓
            current_value = self.position_value * (self.entry_price / current_price)
        
        return current_value
    
    # 仓位管理已移至策略内部，不再需要此方法
    
    def open_position(self, signal, price, current_time=None, timeframe="1h", signal_info=None):
        """
        开仓
        
        Args:
            signal: 交易信号 (1=开多, -1=开空)
            price: 开仓价格
            current_time: 当前时间
            timeframe: 时间级别
            signal_info: 信号信息
        """
        if self.position != 0:
            return  # 已有仓位，不开新仓
        
        # 使用策略提供的仓位大小
        position_value = 0
        if signal_info and 'position_size' in signal_info:
            position_size = signal_info['position_size']
            # 处理position_size，它可能是一个字典
            if isinstance(position_size, dict):
                position_size = position_size.get('size', 0.0)
            # 将仓位比例转换为实际金额
            position_value = self.cash * position_size
        else:
            # 默认使用全部资金
            position_value = self.cash
        
        # 确保不超过可用资金
        if position_value > self.cash:
            position_value = self.cash
        
        # 扣除手续费和买入资金
        fee = position_value * self.trading_fee
        self.cash -= (position_value + fee)
        
        # 记录开仓信息
        self.position = signal
        self.entry_price = price
        self.position_value = position_value
        
        # 同步更新策略的持仓信息
        if hasattr(self.strategy, 'update_position_info'):
            # 获取信号评分
            entry_signal_score = 0.0
            if signal_info and 'signal_score' in signal_info:
                entry_signal_score = signal_info['signal_score']
            
            self.strategy.update_position_info(signal, price, price, current_time, entry_signal_score)
        

        
        # 初始化高点跟踪
        if signal == 1:  # 多仓
            self.high_point = price
            self.low_point = float('inf')
        else:  # 空仓
            self.high_point = 0
            self.low_point = price
        
        # 格式化时间显示
        time_str = current_time.strftime("%Y-%m-%d %H:%M") if current_time else "N/A"
        
        # 记录开仓日志 - 包含信号原因
        action = "开多" if signal == 1 else "开空"
        data_time = current_time.strftime('%Y-%m-%d %H:%M:%S') if current_time else "N/A"
        
        # 获取信号原因和详细信息
        signal_reason = "信号开仓"
        signal_details = ""
        
        if signal_info:
            # 优先使用原始信号信息中的原因
            if 'original_signal' in signal_info and 'reason' in signal_info['original_signal']:
                signal_reason = signal_info['original_signal']['reason']
            elif 'reason' in signal_info:
                signal_reason = signal_info['reason']
            
            # 构建详细的信号信息
            details_parts = []
            
            # 检查是否有评分信息
            if 'signal_score' in signal_info:
                details_parts.append(f"综合评分{signal_info['signal_score']:.2f}")
            if 'base_score' in signal_info:
                details_parts.append(f"基础评分{signal_info['base_score']:.2f}")
            if 'trend_score' in signal_info:
                details_parts.append(f"趋势评分{signal_info['trend_score']:.2f}")
            
            
            # 添加技术指标信息
            if 'debug' in signal_info:
                debug_info = signal_info['debug']
                tech_parts = []
                
                if 'rsi' in debug_info:
                    tech_parts.append(f"RSI:{debug_info['rsi']:.1f}")
                
                if 'macd' in debug_info and 'macd_signal' in debug_info:
                    macd_diff = debug_info['macd'] - debug_info['macd_signal']
                    tech_parts.append(f"MACD:{macd_diff:+.3f}")
                
                if 'adx' in debug_info:
                    tech_parts.append(f"ADX:{debug_info['adx']:.1f}")
                
                if 'market_scenario' in debug_info:
                    tech_parts.append(f"市场:{debug_info['market_scenario']}")
                
                # 添加更多技术指标
                if 'di_plus' in debug_info and 'di_minus' in debug_info:
                    tech_parts.append(f"DI+:{debug_info['di_plus']:.1f} DI-:{debug_info['di_minus']:.1f}")
                
                if 'volume_ratio' in debug_info:
                    tech_parts.append(f"成交量:{debug_info['volume_ratio']:.2f}x")
                
                if 'greed_score' in debug_info:
                    tech_parts.append(f"贪婪指数:{debug_info['greed_score']:.0f}")
                
                if 'sentiment_score' in debug_info:
                    tech_parts.append(f"情绪:{debug_info['sentiment_score']:.0f}")
                
                if tech_parts:
                    details_parts.append(f"技术指标: {' '.join(tech_parts)}")
            
            if details_parts:
                signal_details = f" | 信号: {' '.join(details_parts)}"
        
        # 只保留一个日志输出，避免重复
        logger.info(f"[{data_time}] {action} | 价格: {price:.2f} | 仓位: {position_value:.0f} | 现金: {self.cash:.0f} | 原因: {signal_reason}{signal_details}")
        
        # 记录交易
        trade_record = {
            "date": current_time,
            "action": action,
            "price": price,
            "position_value": position_value,
            "cash": self.cash,
            "timeframe": timeframe,
            "pnl": 0,
            "reason": signal_reason,
            "trade_type": "open"
        }
        
        # 添加信号评分信息
        if signal_info:
            trade_record.update({
                "signal_score": signal_info.get('signal_score', 0),
                "base_score": signal_info.get('base_score', 0),
                "trend_score": signal_info.get('trend_score', 0),
                "risk_score": signal_info.get('risk_score', 0),
                "drawdown_score": signal_info.get('drawdown_score', 0),
                "position_size": signal_info.get('position_size', {}).get('size', 0) if isinstance(signal_info.get('position_size'), dict) else signal_info.get('position_size', 0)
            })
            
            # 添加过滤器信息
            if 'filters' in signal_info:
                trade_record['filters'] = signal_info['filters']
            else:
                trade_record['filters'] = {'signal_filter': {'passed': True, 'reason': '无过滤器信息'}}
        
        self.trade_log.append(trade_record)
        
        self.total_trades += 1
    
    def close_position(self, price, reason="信号平仓", current_time=None, timeframe="1h"):
        """
        平仓
        
        Args:
            price: 平仓价格
            reason: 平仓原因
            current_time: 当前时间
            timeframe: 时间级别
        """
        if self.position == 0:
            return
        
        # 计算盈亏
        if self.position == 1:  # 多仓
            pnl = self.position_value * (price / self.entry_price - 1)
        else:  # 空仓
            pnl = self.position_value * (self.entry_price / price - 1)
        
        # 计算平仓后的现金
        closing_amount = self.position_value + pnl  # 平仓获得的总金额
        fee = closing_amount * self.trading_fee if closing_amount > 0 else 0  # 手续费
        self.cash += closing_amount - fee
        
        # 确保现金不为负数
        if self.cash < 0:
            self.cash = 0
        
        # 更新统计
        if pnl > 0:
            self.profitable_trades += 1
        else:
            self.loss_trades += 1
        

        
        # 更新冷却处理状态 - 统一使用策略的冷却系统
        if hasattr(self.strategy, 'update_cooldown_treatment_status'):
            trade_result = {
                'pnl': pnl,
                'timestamp': current_time,
                'reason': reason
            }
            self.strategy.update_cooldown_treatment_status(trade_result)
            
            # 记录冷却处理状态 - 简化版
            if hasattr(self.strategy, 'get_cooldown_treatment_status'):
                status = self.strategy.get_cooldown_treatment_status()
                if status.get('cooldown_treatment_active', False):
                    level = status.get('cooldown_treatment_level', 0)
                    skipped = status.get('skipped_trades_count', 0)
                    max_skip = status.get('max_skip_trades', 0)
                    print(f"冷却中 L{level} | 跳过: {skipped}/{max_skip}")
                    logger.debug(f"冷却中 L{level} | 跳过: {skipped}/{max_skip}")
        
        # 仓位管理已移至策略内部
        
        # 格式化时间显示
        time_str = current_time.strftime("%Y-%m-%d %H:%M") if current_time else "N/A"
        
        # 记录平仓日志 - 整合止盈信息
        action = "平多" if self.position == 1 else "平空"
        profit_status = "盈利" if pnl > 0 else "亏损"
        data_time = current_time.strftime('%Y-%m-%d %H:%M:%S') if current_time else "N/A"
        
        # 检查是否为止盈操作
        is_take_profit = any(keyword in reason for keyword in ['止盈', '技术止盈', '固定止盈', '回调止盈'])
        
        if is_take_profit:
            # 止盈操作：记录整合的日志
            log_message = f"[{data_time}] 触发止盈 - 状态: {profit_status}, 盈亏: {pnl/self.position_value*100:.2f}%, 原因: {reason}"
            logger.info(log_message)
            print(f"🟢 {log_message}")
        else:
            # 其他平仓操作：记录标准日志
            reason_text = f" | 原因: {reason}" if reason and reason != "信号平仓" else ""
            log_message = f"[{data_time}] {profit_status} {action}{reason_text} | 价格: {price:.2f} | 盈亏: {pnl:.0f} ({pnl/self.position_value*100:.1f}%) | 现金: {self.cash:.0f}"
            print(log_message)
            logger.info(log_message)
        
        # 记录交易
        trade_record = {
            "date": current_time,
            "action": action,
            "price": price,
            "position_value": self.position_value,
            "cash": self.cash,
            "timeframe": timeframe,
            "pnl": pnl,
            "reason": reason,
            "trade_type": "close"
        }
        
        # 添加评分信息 - 从开仓记录中获取
        if len(self.trade_log) > 0:
            # 找到对应的开仓记录
            for trade in reversed(self.trade_log):
                if trade.get('trade_type') == 'open':
                    # 复制开仓时的评分信息到平仓记录
                    trade_record.update({
                        "signal_score": trade.get('signal_score', 0),
                        "base_score": trade.get('base_score', 0),
                        "trend_score": trade.get('trend_score', 0),
                        "risk_score": trade.get('risk_score', 0),
                        "drawdown_score": trade.get('drawdown_score', 0),
                        "position_size": trade.get('position_size', 0)
                    })
                    
                    # 复制过滤器信息
                    if 'filters' in trade:
                        trade_record['filters'] = trade['filters']
                    break
        
        self.trade_log.append(trade_record)
        
        # 重置仓位信息
        self.position = 0
        self.entry_price = 0
        self.position_value = 0
        
        # 重置高点跟踪
        self.high_point = 0
        self.low_point = float('inf')
        
        # 同步更新策略的持仓信息
        if hasattr(self.strategy, 'update_position_info'):
            self.strategy.update_position_info(0, 0, price, current_time)
    
    def run_backtest(self, features, timeframe="1h"):
        """
        运行回测
        
        Args:
            features: 包含技术指标的数据框
            timeframe: 时间级别
            
        Returns:
            dict: 回测结果
        """
        print(f"开始回测 ({len(features)} 条数据)")
        
        # ===== 重置回测器状态 =====
        self.cash = self.initial_cash
        self.position = 0
        self.entry_price = 0
        self.position_value = 0
        # 仓位管理已移至策略内部
        self.trade_log = []
        self.total_assets = []
        self.asset_timestamps = []
        self.total_trades = 0
        self.profitable_trades = 0
        self.loss_trades = 0
        

        
        # 重置策略的风险管理状态
        if hasattr(self.strategy, 'reset_risk_management'):
            self.strategy.reset_risk_management()
        
        # ===== 遍历每个时间点 =====
        # 交易逻辑：持仓状态下根据盈亏状态分别触发止盈或止损，无持仓状态下才考虑开仓
        for i, (timestamp, row) in enumerate(features.iterrows()):
            current_price = row['close']
            current_time = timestamp
            
            # 创建增强的行数据 - 简化版以提高性能
            enhanced_row = {'row_data': row.to_dict(), 'multi_timeframe_data': None}
            
            # 标记是否在当前时间点执行了平仓
            position_closed_this_time = False
            
            # ===== 持仓状态下的风险管理检查（根据盈亏状态分别处理） =====
            if self.position != 0 and hasattr(self.strategy, 'check_risk_management'):
                # 更新策略的持仓信息
                self.strategy.update_position_info(self.position, self.entry_price, current_price)
                
                # 获取当前持仓状态信息
                position_status = self.strategy.get_position_status(current_price)
                profit_ratio = position_status['profit_ratio']
                profit_status = position_status['status']
                
                try:
                    # 检查风险管理 - 根据盈亏状态分别触发止盈或止损逻辑
                    # 信号评分已经在特征工程中计算并保存到enhanced_row中
                    risk_action, risk_reason = self.strategy.check_risk_management(
                        current_price, enhanced_row, current_time
                    )
                    
                    if risk_action == 'stop_loss':
                        logger.info(f"触发止损 - 状态: {profit_status}, 盈亏: {profit_ratio*100:.2f}%, 原因: {risk_reason}")
                        self.close_position(current_price, reason=risk_reason, current_time=current_time, timeframe=timeframe)
                        position_closed_this_time = True
                    elif risk_action == 'take_profit':
                        # 不在这里记录日志，让close_position方法统一处理
                        self.close_position(current_price, reason=risk_reason, current_time=current_time, timeframe=timeframe)
                        position_closed_this_time = True
                except Exception as e:
                    print(f"风险管理检查异常: {e}")
                    logger.error(f"风险管理检查异常: {e}")
                    # 风险管理检查失败时，记录错误但不进行兜底处理
                    # 兜底止损逻辑已移至策略内部统一管理
            
            # ===== 获取交易信号 =====
            try:
                signal_info = self.strategy.generate_signals(features.iloc[:i+1], verbose=False)
                signal = signal_info.get('signal', 0)  # 从字典中提取信号值
                
                # 检查回测模式冷却处理 - 风险控制：是否应该跳过交易
                # 注意：这个检查应该在每次信号生成时都执行，而不仅仅是有交易信号时
                if hasattr(self.strategy, 'should_skip_trade') and self.strategy.should_skip_trade():
                    logger.info(f"跳过交易 - 冷却处理中")
                    # 记录冷却处理状态信息
                    if hasattr(self.strategy, 'get_cooldown_treatment_status'):
                        status = self.strategy.get_cooldown_treatment_status()
                        logger.info(f"冷却处理状态 - 级别: {status.get('cooldown_treatment_level', 0)}, "
                                  f"已跳过: {status.get('skipped_trades_count', 0)}/{status.get('max_skip_trades', 0)}")
                    continue
                
                # 处理开仓信号 - 只在无持仓状态下进行开仓（持仓状态下只执行止盈止损）
                if signal != 0 and self.position == 0 and not position_closed_this_time:
                    # 添加调试信息
                    logger.debug(f"[{current_time}] 检查开仓条件 - signal: {signal}, position: {self.position}, position_closed_this_time: {position_closed_this_time}")
                    # 使用策略的开仓检查方法
                    if hasattr(self.strategy, 'should_open_position'):
                        should_open = self.strategy.should_open_position(signal, enhanced_row, current_time)
                        if not should_open:
                            continue

                    
                    # 记录交易信号到日志 - 简化版
                    signal_type = "多头" if signal == 1 else "空头"
                    # logger.debug(f"信号: {signal_type} | 价格: {current_price:.0f}")  # 注释掉调试日志以提高性能
                    
                    # 开仓
                    self.open_position(signal, current_price, current_time, timeframe, signal_info)
                    

                    
                    # 更新策略的持仓信息
                    if hasattr(self.strategy, 'update_position_info'):
                        self.strategy.update_position_info(self.position, self.entry_price, current_price)
                    
            except Exception as e:
                print(f"获取信号异常: {e}")
                logger.error(f"获取信号异常: {e}")
            
            # ===== 记录资金曲线 =====
            # 优化：只在需要时计算仓位价值
            if self.position != 0:
                current_position_value = self.calculate_position_value(current_price)
            else:
                current_position_value = 0
            total_asset = self.cash + current_position_value
            self.total_assets.append(total_asset)
            self.asset_timestamps.append(current_time)
            
            # 显示进度 - 进一步减少频率以提高性能
            if (i + 1) % 1000 == 0:
                print(f"进度: {i+1}/{len(features)} | 资产: {total_asset:.0f}")
        
        # ===== 回测结束处理 =====
        # 如果还有仓位则强制平仓
        if self.position != 0:
            last_price = features['close'].iloc[-1]
            last_time = features.index[-1]
            self.close_position(last_price, reason="回测结束平仓", current_time=last_time, timeframe=timeframe)
        
        # ===== 输出统计信息 =====
        self._print_backtest_summary(features)
        
        # ===== 返回回测结果 =====
        final_cash = self.cash
        return_ratio = (final_cash - self.initial_cash) / self.initial_cash * 100
        
        return {
            'final_cash': final_cash,
            'return_ratio': return_ratio,
            'total_trades': self.total_trades,
            'total_assets': self.total_assets,
            'asset_timestamps': self.asset_timestamps,
            'trade_log': pd.DataFrame(self.trade_log)
        }
    
    def _print_backtest_summary(self, features):
        """
        打印回测摘要 - 简化版
        
        Args:
            features: 特征数据
        """
        # 统计交易记录
        trade_df = pd.DataFrame(self.trade_log)
        
        print(f"\n回测结果")
        print(f"总交易: {self.total_trades} | 盈利: {self.profitable_trades} | 亏损: {self.loss_trades}")
        
        if self.total_trades > 0:
            win_rate = self.profitable_trades / self.total_trades * 100
            print(f"胜率: {win_rate:.1f}%")
        
        if len(trade_df) > 0 and 'pnl' in trade_df.columns:
            close_trades = trade_df[trade_df['trade_type'] == 'close']
            if len(close_trades) > 0:
                profitable_trades = close_trades[close_trades['pnl'] > 0]
                loss_trades = close_trades[close_trades['pnl'] < 0]
                
                avg_profit = profitable_trades['pnl'].mean() if len(profitable_trades) > 0 else 0
                avg_loss = loss_trades['pnl'].mean() if len(loss_trades) > 0 else 0
                profit_loss_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else 0
                
                print(f"平均盈亏: {avg_profit:.0f} / {avg_loss:.0f} | 盈亏比: {profit_loss_ratio:.1f}")
        
        final_cash = self.cash
        return_ratio = (final_cash - self.initial_cash) / self.initial_cash * 100
        print(f"最终资金: {final_cash:.0f} | 收益率: {return_ratio:.1f}%")
    
    
