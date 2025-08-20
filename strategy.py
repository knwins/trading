import numpy as np
import pandas as pd

import logging
from datetime import datetime
import warnings

from feature_engineer import FeatureEngineer
warnings.filterwarnings('ignore')
# 设置日志
logger = logging.getLogger(__name__)
class SignalFilter:
    """
    交易信号过滤器
    
    功能：过滤低质量交易信号，提高策略稳定性
    
    核心过滤器：
    - 价格偏离过滤：防止追高追低
    - RSI过滤：避免超买超卖区域
    - 价格动量过滤：防止过度追涨杀跌
    - 成交量异常过滤：避免异常成交量
    - 相邻时间级别验证：多时间框架确认
    - 价格均线纠缠过滤：避免均线纠缠区域
    
    辅助过滤器：
    - 波动率过滤：控制风险
    - 时间过滤：避开低流动性时段
    """
    
    def __init__(self, config=None, data_loader=None):
        """初始化过滤器参数和开关"""
        # 从配置中获取过滤器参数
        if config is None:
            filter_config = {}
            print(f"🔍 使用空配置")
        else:
            # 检查配置结构，如果直接包含过滤器参数，则使用整个配置
            if 'enable_signal_filter' in config:
                filter_config = config
                print(f"🔍 使用扁平化配置，直接包含过滤器参数")
            else:
                filter_config = config.get('signal_filters', {})
                print(f"🔍 使用嵌套配置，从 signal_filters 获取")
            
            print(f"🔍 使用传入配置，config keys: {list(config.keys())}")
            print(f"🔍 filter_config keys: {list(filter_config.keys())}")
        
        print(f"🔍 filter_config 中的 enable_signal_filter: {filter_config.get('enable_signal_filter', 'NOT_FOUND')}")
        
        # ===== 核心过滤器开关 =====
        self.enable_price_deviation_filter = filter_config.get('enable_price_deviation_filter', False)
        self.enable_price_ma_entanglement = filter_config.get('enable_price_ma_entanglement', False)
        self.enable_rsi_filter = filter_config.get('enable_rsi_filter', False)
        self.enable_volatility_filter = filter_config.get('enable_volatility_filter', False)
        self.enable_signal_filter = filter_config.get('enable_signal_filter', False)
        print(f"🔍 趋势过滤器启用状态: {self.enable_signal_filter}")
        print(f"🔍 波动率过滤器启用状态: {self.enable_volatility_filter}")
        
        # ===== 核心过滤参数 =====
        self.price_deviation_threshold = filter_config.get('price_deviation_threshold', 2.0)
        self.rsi_overbought_threshold = filter_config.get('rsi_overbought_threshold', 85)
        self.rsi_oversold_threshold = filter_config.get('rsi_oversold_threshold', 25)
        
        # ===== 波动率过滤器参数 =====
        self.min_volatility = filter_config.get('min_volatility', 0.005)
        self.max_volatility = filter_config.get('max_volatility', 0.45)
        self.volatility_period = filter_config.get('volatility_period', 20)
        
        # ===== 价格均线纠缠过滤参数 =====
        self.entanglement_distance_threshold = filter_config.get('entanglement_distance_threshold', 0.2)
        
        # ===== 趋势过滤器参数 =====
        self.trend_filter_threshold_min = filter_config.get('trend_filter_threshold_min', 0.3)
        self.trend_filter_threshold_max = filter_config.get('trend_filter_threshold_max', 0.7)
        
        # 趋势过滤器具体阈值参数
        self.filter_long_base_score = filter_config.get('filter_long_base_score', 0.7)
        self.filter_short_base_score = filter_config.get('filter_short_base_score', 0.2)
        self.filter_long_trend_score = filter_config.get('filter_long_trend_score', 0.4)
        self.filter_short_trend_score = filter_config.get('filter_short_trend_score', 0.3)
        

        
        # ===== 动态阈值调整参数 =====
        
        # 数据加载器
        self.data_loader = data_loader
         
    
    def filter_signal(self, signal, features, current_index, verbose=False, trend_score=None, base_score=None, silent=False):
        """
        过滤交易信号
        
        Args:
            signal: 原始信号 (1=多头, -1=空头, 0=观望)
            features: 特征数据
            current_index: 当前索引
            verbose: 是否输出详细信息
            silent: 是否静默模式（不输出日志）
            
        Returns:
            tuple: (过滤后信号, 过滤原因)
        """
        if signal == 0:  # 观望信号不需要过滤
            return signal, "正常信号"
        
        # 获取当前数据
        current_data = features.iloc[:current_index+1]
        current_row = current_data.iloc[-1]
        
        # 获取当前数据时间用于日志
        current_time = current_row.name if hasattr(current_row, 'name') else None
        try:
            if current_time and pd.notna(current_time):
                time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                time_str = "N/A"
        except (ValueError, AttributeError):
            time_str = "N/A"
        
        # 记录开始过滤信号
        signal_type = "做多" if signal == 1 else "做空"
        #logger.info(f"[{time_str}] 开始过滤{signal_type}信号")
        
        # ===== 核心过滤器检查 =====
        
        # 1. 价格偏离过滤（核心）
        if self.enable_price_deviation_filter:
            filtered_signal, filter_reason = self._check_price_deviation(current_row, signal)
            if filtered_signal == 0:
                if verbose:
                    print(f"🔍 价格偏离过滤: {filter_reason}")
                return filtered_signal, filter_reason
        
        # 2. RSI过滤（核心）
        if self.enable_rsi_filter:
            filtered_signal, filter_reason = self._check_rsi_conditions(current_row, signal)
            if filtered_signal == 0:
                if verbose:
                    print(f"🔍 RSI过滤: {filter_reason}")
                return filtered_signal, filter_reason
        
        # 3. 波动率过滤（核心）
        if self.enable_volatility_filter:
            filtered_signal, filter_reason = self._check_volatility_filter(current_data, current_row)
            if filtered_signal == 0:
                if verbose:
                    print(f"🔍 波动率过滤: {filter_reason}")
                return filtered_signal, filter_reason
        

        

        
        # 5. 趋势过滤器（核心）
        if self.enable_signal_filter:
            if verbose:
                logger.info(f"进入趋势过滤器检查 - 原始信号: {signal}")
            filtered_signal, filter_reason = self._check_signal_filter(current_data, current_row, signal, trend_score, base_score)
            if filtered_signal == 0:
                if verbose:
                    logger.info(f"趋势过滤: {filter_reason}")
                return filtered_signal, filter_reason
            else:
                if verbose:
                    logger.info(f"趋势过滤器通过: {filter_reason}")
        
        # 6. 价格均线纠缠过滤（核心）
        if self.enable_price_ma_entanglement:
            is_entangled = self._check_price_ma_entanglement(current_row)
            if is_entangled:
                if verbose:
                    print("🔍 价格均线纠缠过滤: 价格均线纠缠")
                return 0, "价格均线纠缠"
        
        
        # 所有过滤器都通过
        return signal, "正常信号"
      
    def _check_price_deviation(self, current_row, signal):
        """价格偏离过滤：防止追高追低（动态阈值调整）"""
        
        if 'lineWMA' in current_row and not pd.isna(current_row['lineWMA']):
            # 动态调整价格偏离阈值
            dynamic_threshold = self._get_dynamic_price_deviation_threshold(current_row, signal)
            
            # 根据信号类型选择不同的价格
            if signal == 1:  # 做多信号：使用low价格
                price = current_row.get('low', current_row['close'])
                line_wma = current_row['lineWMA']
                # 避免除零错误
                if line_wma != 0:
                    price_deviation = (price - line_wma) / line_wma * 100
                    
                    # 确保price_deviation是标量值
                    if hasattr(price_deviation, '__len__') and len(price_deviation) > 1:
                        price_deviation = price_deviation.iloc[-1] if hasattr(price_deviation, 'iloc') else price_deviation[-1]
                    
                    # 做多信号：low价格过度偏离WMA向上时过滤（使用动态阈值）
                    if price_deviation >= dynamic_threshold:
                        return 0, f"价格偏离过滤(做多信号，low价格偏离WMA{price_deviation:.1f}% >= 动态阈值{dynamic_threshold:.1f}%)"
                    
            elif signal == -1:  # 空头信号：使用high价格
                price = current_row.get('high', current_row['close'])
                line_wma = current_row['lineWMA']
                # 避免除零错误
                if line_wma != 0:
                    price_deviation = (price - line_wma) / line_wma * 100
                    
                    # 确保price_deviation是标量值
                    if hasattr(price_deviation, '__len__') and len(price_deviation) > 1:
                        price_deviation = price_deviation.iloc[-1] if hasattr(price_deviation, 'iloc') else price_deviation[-1]
                    
                    # 空头信号：high价格过度偏离WMA向下时过滤（使用动态阈值）
                    if price_deviation <= -dynamic_threshold:
                        return 0, f"价格偏离过滤(空头信号，high价格偏离WMA{price_deviation:.1f}% <= -动态阈值{-dynamic_threshold:.1f}%)"
        
        return signal, "正常"
    
    def _get_dynamic_price_deviation_threshold(self, current_row, signal):
        """动态计算价格偏离阈值"""
        base_threshold = self.price_deviation_threshold  # 基础阈值2.0%
        
        # 1. 市场状态调整
        market_adjustment = self._get_market_state_adjustment(current_row)
        
        # 3. 波动率调整
        volatility_adjustment = self._get_volatility_adjustment(current_row)
        
        # 计算最终动态阈值
        dynamic_threshold = base_threshold + market_adjustment  + volatility_adjustment
        
        # 确保阈值在合理范围内
        min_threshold = 1.0  # 最小阈值1.0%
        max_threshold = 8.0  # 最大阈值8.0%
        dynamic_threshold = max(min_threshold, min(max_threshold, dynamic_threshold))
        
        return dynamic_threshold
    

    
    def _get_market_state_adjustment(self, current_row):
        """基于市场状态的阈值调整"""
        # 获取市场状态
        market_regime = current_row.get('market_regime', 0)
        # print(f"_get_market_state_adjustment_market_regime: {market_regime}")
        # 基于市场状态调整阈值
        if market_regime == 2:  # 强震荡市场
            return -0.5  # 降低阈值0.5%，震荡市场需要更严格过滤
        elif market_regime == 1:  # 强趋势市场
            return 5.0  # 提高阈值1.0%，趋势市场允许更大偏离
        else:  # 混合市场
            return 0.0
    
   
    
    def _get_volatility_adjustment(self, current_row):
        """基于波动率的阈值调整"""
        # 获取ATR或波动率指标
        atr = current_row.get('atr', 0)
        close_price = current_row.get('close', 1)
        
        if atr > 0 and close_price > 0:
            # 计算ATR相对价格的比例
            atr_ratio = atr / close_price * 100
            
            # 基于ATR比例调整阈值
            if atr_ratio > 5.0:  # 高波动率
                return 1.5  # 提高阈值1.5%
            elif atr_ratio > 3.0:  # 中等波动率
                return 0.5  # 提高阈值0.5%
            elif atr_ratio < 1.0:  # 低波动率
                return -0.5  # 降低阈值0.5%
        
        return 0.0
    
    def _check_rsi_conditions(self, current_row, signal):
        """RSI过滤：避免超买超卖区域"""
        rsi = current_row.get('rsi', 50)
        if pd.isna(rsi):
            return signal, "正常"
        
        if signal == 1 and rsi >= self.rsi_overbought_threshold:
            return 0, f"多头RSI超买过滤(RSI{rsi:.1f} >= 阈值{self.rsi_overbought_threshold})"
        elif signal == -1 and rsi <= self.rsi_oversold_threshold:
            return 0, f"空头RSI超卖过滤(RSI{rsi:.1f} <= 阈值{self.rsi_oversold_threshold})"
        
        return signal, "正常"

    
    def _check_price_ma_entanglement(self, current_row):
        """价格均线纠缠过滤：基于价格与均线顺序关系的智能过滤"""
        current_price = current_row.get('close', 0)
        line_wma = current_row.get('lineWMA', 0)
        open_ema = current_row.get('openEMA', 0)
        close_ema = current_row.get('closeEMA', 0)
        
        # 检查数据有效性
        if (pd.isna(current_price) or pd.isna(line_wma) or 
            pd.isna(open_ema) or pd.isna(close_ema) or
            line_wma == 0 or open_ema == 0 or close_ema == 0):
            return False
        
        # 计算EMA的最大值和最小值
        ema_max = max(open_ema, close_ema)
        ema_min = min(open_ema, close_ema)
        
        # 定义价格与均线的顺序关系
        # 1. 完美多头排列：价格 > EMA最大 > LineWMA
        perfect_bullish = current_price > ema_max > line_wma
        
        # 2. 完美空头排列：价格 < EMA最小 < LineWMA
        perfect_bearish = current_price < ema_min < line_wma
        
        # 计算距离信息
        price_wma_distance = abs(current_price - line_wma) / line_wma * 100
        #print(f"price_wma_distance: {price_wma_distance}")
        ema_wma_distance = abs(ema_max - line_wma) / line_wma * 100
        ema_distance = abs(ema_max - ema_min) / ema_max * 100
        
        # 判断是否为纠缠状态
        is_entangled = False
        
        # 只有完美排列才不被过滤，其他所有排列都要被过滤
        if perfect_bullish or perfect_bearish:
            # 完美排列时，再判断距离
            if perfect_bullish:
                # 完美多头排列：检查距离是否过近
                if price_wma_distance < self.entanglement_distance_threshold:
                    is_entangled = True
            elif perfect_bearish:
                # 完美空头排列：检查距离是否过近
                if price_wma_distance < self.entanglement_distance_threshold:
                    is_entangled = True
        else:
            # 非完美排列：直接过滤
            is_entangled = True
        
        return is_entangled

    
    def _check_signal_filter(self, current_data, current_row, signal, trend_score=None, base_score=None):
        """
        趋势过滤器：基于趋势强度和基础评分过滤信号
        
        Args:
            current_data: 当前数据
            current_row: 当前行数据
            signal: 信号 (1=多头, -1=空头, 0=观望)
            
        Returns:
            tuple: (过滤后信号, 过滤原因)
        """
        try:
            # 获取趋势强度和基础评分 - 优先使用传递的参数
            if trend_score is None:
                trend_score = current_row.get('trend_score')
            if base_score is None:
                base_score = current_row.get('base_score')

            # 检查数据有效性
            if trend_score is None or pd.isna(trend_score):
                return signal, "正常"
            
            if base_score is None or pd.isna(base_score):
                return signal, "正常"
            
            # 获取过滤阈值 - 直接从当前实例的属性获取
            filter_long_base_score = getattr(self, 'filter_long_base_score')
            filter_short_base_score = getattr(self, 'filter_short_base_score')
            filter_long_trend_score = getattr(self, 'filter_long_trend_score')
            filter_short_trend_score = getattr(self, 'filter_short_trend_score')
            
            # logger.info(f"🔍 阈值获取调试:")
            # logger.info(f"  filter_long_base_score: {filter_long_base_score}")
            # logger.info(f"  filter_short_base_score: {filter_short_base_score}")
            # logger.info(f"  filter_long_trend_score: {filter_long_trend_score}")
            # logger.info(f"  filter_short_trend_score: {filter_short_trend_score}")

            # logger.info(f"🔍 趋势过滤器调试 - 信号:{signal}, 趋势评分:{trend_score}, 基础评分:{base_score}")
            # logger.info(f"🔍 空头阈值 - 趋势:{filter_short_trend_score} (类型:{type(filter_short_trend_score)}), 基础:{filter_short_base_score} (类型:{type(filter_short_base_score)})")
            # logger.info(f"🔍 多头阈值 - 趋势:{filter_long_trend_score} (类型:{type(filter_long_trend_score)}), 基础:{filter_long_base_score} (类型:{type(filter_long_base_score)})")
            
            # 根据信号方向进行过滤
            if signal == 1:  # 多头信号
                # 多头过滤逻辑：trend_score < filter_long_short_trend_score 过滤，base_score < filter_long_base_score 过滤
                if trend_score < filter_long_trend_score:
                    return 0, f"多头趋势强度不足(趋势评分{trend_score:.3f} < {filter_long_trend_score})"
                
                if base_score < filter_long_base_score:
                    return 0, f"多头基础评分不足(基础评分{base_score:.3f} < {filter_long_base_score})"
                    
            elif signal == -1:  # 空头信号
                # 空头过滤逻辑：trend_score > filter_short_trend_score 过滤，base_score > filter_short_base_score 过滤
                if trend_score > filter_short_trend_score:
                    return 0, f"空头趋势强度过高(趋势评分{trend_score:.3f} > {filter_short_trend_score})"
                
                if base_score > filter_short_base_score:
                    return 0, f"空头基础评分过高(基础评分{base_score:.3f} > {filter_short_base_score})"
            
            return signal, "正常"
            
        except Exception as e:
            # 如果计算失败，返回原始信号
            return signal, f"趋势过滤异常: {str(e)}"

    def _check_volatility_filter(self, current_data, current_row):
        """波动率过滤：控制风险"""
        try:
            if len(current_data) < self.volatility_period:
                return 1, "正常"
            
            # 计算历史波动率（基于收盘价的标准差）
            recent_prices = current_data['close'].tail(self.volatility_period)
            returns = recent_prices.pct_change().dropna()
            current_volatility = returns.std()
            
            # 检查波动率是否在合理范围内
            if current_volatility < self.min_volatility:
                return 0, f"波动率过低({current_volatility:.4f} < {self.min_volatility})"
            elif current_volatility > self.max_volatility:
                return 0, f"波动率过高({current_volatility:.4f} > {self.max_volatility})"
            
            return 1, "正常"
            
        except Exception as e:
            return 1, "正常"
    
class SharpeOptimizedStrategy:
    """
    基于夏普比率动态调整风险敞口的优化策略
    根据市场表现自动调整仓位大小，提高风险调整后的收益
    """
    
    def __init__(self, config=None, data_loader=None):
        """
        初始化夏普优化策略
        
        Args:
            config: 配置字典，可覆盖默认参数
            data_loader: 数据加载器实例
        """
        # 从config.py导入统一配置
        try:
            from config import OPTIMIZED_STRATEGY_CONFIG
            default_config = OPTIMIZED_STRATEGY_CONFIG
        except ImportError:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 无法导入OPTIMIZED_STRATEGY_CONFIG，使用默认配置")
            default_config = {}
        
        # 合并用户配置
        self.config = self._deep_merge(default_config, config or {})
        
        # 策略参数
        self.sharpe_lookback = self.config.get('sharpe_params', {}).get('sharpe_lookback', 30)
        self.target_sharpe = self.config.get('sharpe_params', {}).get('target_sharpe', 1.0)
        self.max_risk_multiplier = self.config.get('sharpe_params', {}).get('max_risk_multiplier', 2.0)
        self.risk_multiplier = self.config.get('sharpe_params', {}).get('initial_risk_multiplier', 1.0)
        
        # 夏普率计算相关变量
        self.returns = []
        self.portfolio_values = []
        
        # 风险管理状态
        self.position = 0  # 0=无仓位, 1=多仓, -1=空仓
        self.entry_price = 0  # 开仓价格
        self.high_point = 0  # 持仓期间的最高点
        self.low_point = float('inf')  # 持仓期间的最低点
        self.entry_time = None  # 开仓时间
        self.holding_periods = 0  # 持仓周期数
        
        # 交易统计
        self.trade_count = 0
        self.win_count = 0
        
        # 交易冷却期管理
        # 初始化信号过滤器


        self.long_threshold = self.config.get('signal_direction', {}).get('long_threshold', 0.6)
        self.short_threshold = self.config.get('signal_direction', {}).get('short_threshold', 0.25) 


        self.signal_filter = SignalFilter(self.config.get('signal_filters', {}), data_loader)


        
        # 风险管理配置
        self.stop_loss_config = self.config.get('risk_management', {}).get('stop_loss', {})
        self.take_profit_config = self.config.get('risk_management', {}).get('take_profit', {})
        
        # ===== 冷却处理系统 =====
        # 冷却处理配置：连续亏损后降低风险
        self.cooldown_treatment_config = self.config.get('cooldown_treatment', {})
        self.enable_cooldown_treatment = self.cooldown_treatment_config.get('enable_cooldown_treatment', True)
        
        # 冷却处理阈值
        self.cooldown_threshold = self.cooldown_treatment_config.get('consecutive_loss_threshold', 2)
        
        # 冷却处理状态变量
        self.cooldown_treatment_active = False  # 是否处于冷却处理状态
        self.cooldown_treatment_level = 0    # 冷却处理级别 (0=正常, 1=轻度, 2=中度, 3=重度)
        self.cooldown_treatment_start_time = None  # 冷却处理开始时间
        
        # 冷却处理效果参数
        self.position_size_reduction = 1.0  # 仓位大小减少比例
        
        # 交易历史记录 (用于计算连续盈亏)
        self.trade_history = []
        
        # 冷却处理模式：回测模式(风险控制-跳过交易) vs 实盘模式(风险控制-停止交易)
        self.cooldown_treatment_mode = self.cooldown_treatment_config.get('mode', 'backtest')
        
        # 回测模式风险控制变量
        self.skipped_trades_count = 0  # 已跳过的交易次数（风险控制）
        self.max_skip_trades = 0  # 最大跳过交易次数（风险控制）
        
        # 连续盈亏统计（统一管理）
        self.consecutive_losses = 0  # 连续亏损次数
        self.consecutive_wins = 0    # 连续盈利次数
        
        # 时间级别 (用于实盘模式时间计算)
        self.timeframe = "1h"
        
        # 数据加载器
        self.data_loader = data_loader
        
        # 设置窗口期 - 从配置中获取
        from config import WINDOW_CONFIG
        self.short_window = WINDOW_CONFIG.get('SHORT_WINDOW', 30)
        self.long_window = WINDOW_CONFIG.get('LONG_WINDOW', 90)
        


    def update_cooldown_treatment_status(self, trade_result=None):
        """
        更新冷却处理状态 - 主入口函数
        
        Args:
            trade_result: 交易结果 {'pnl': float, 'timestamp': datetime, 'reason': str}
        """
        if not self.enable_cooldown_treatment:
            logger.debug("❄️ 冷却处理功能已禁用")
            return
        
        # 1. 更新交易历史
        if trade_result:
            self.trade_history.append(trade_result)
            # 只保留最近20笔交易记录，避免内存占用过大
            if len(self.trade_history) > 20:
                self.trade_history = self.trade_history[-20:]
            logger.debug(f"📊 更新交易历史 - 当前交易数: {len(self.trade_history)}, 最新盈亏: {trade_result['pnl']:.4f}")
        
        # 2. 计算连续盈亏情况 - 统一使用策略内部的统计
        self._calculate_consecutive_results()
        logger.debug(f"📈 连续盈亏统计 - 连续亏损: {self.consecutive_losses}次, 连续盈利: {self.consecutive_wins}次")
        
        # 3. 检查是否需要启动冷却处理
        self._check_cooldown_treatment_activation()
        
        # 4. 检查是否可以恢复
        self._check_cooldown_treatment_recovery()
        
        # 5. 更新冷却处理效果参数
        self._update_cooldown_treatment_parameters()
    
    def _calculate_consecutive_results(self):
        """
        计算连续盈亏次数 - 从最新交易开始向前计算
        """
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        
        # 从最新的交易开始向前计算连续盈亏
        for trade in reversed(self.trade_history):
            pnl = trade['pnl']
            
            if pnl > 0:  # 盈利交易
                if self.consecutive_losses > 0:
                    break  # 遇到盈利，停止计算连续亏损
                self.consecutive_wins += 1
            elif pnl < 0:  # 亏损交易
                if self.consecutive_wins > 0:
                    break  # 遇到亏损，停止计算连续盈利
                self.consecutive_losses += 1
            else:  # 平局交易
                break  # 平局，停止计算
    
    def _check_cooldown_treatment_activation(self):
        """
        检查是否需要启动冷却处理 - 当连续亏损达到阈值时启动
        """
        if self.cooldown_treatment_active:
            logger.debug(f"❄️ 已在冷却处理中 - 级别: {self.cooldown_treatment_level}")
            return  # 已经在冷却处理中，无需重复启动
        
        # 获取连续亏损阈值
        threshold = self.cooldown_threshold
        
        # 检查是否达到启动条件
        if self.consecutive_losses >= threshold:
            # 获取当前时间用于日志
            current_time = datetime.now()
            time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"[{time_str}] 触发冷却处理 - 连续亏损: {self.consecutive_losses}次 >= 阈值: {threshold}次")
            logger.info(f"[{time_str}] 触发冷却处理 - 连续亏损: {self.consecutive_losses}次 >= 阈值: {threshold}次, 模式: {self.cooldown_treatment_mode}")
            
            # 根据模式启动相应的冷却处理
            if self.cooldown_treatment_mode == 'backtest':
                self._activate_backtest_cooldown_treatment()
            else:  # realtime mode
                self._activate_realtime_cooldown_treatment()
        else:
            logger.debug(f"冷却处理检查 - 连续亏损: {self.consecutive_losses}次 < 阈值: {threshold}次, 无需触发")
    
    def _activate_backtest_cooldown_treatment(self):
        """
        激活回测模式冷却处理 - 风险控制：跳过指定次数的交易
        """
        logger.info(f"开始激活回测模式冷却处理")
        
        # 获取回测模式配置
        backtest_config = self.cooldown_treatment_config.get('backtest_mode', {})
        skip_trades_levels = backtest_config.get('skip_trades_levels', {})
        
        # 根据连续亏损次数确定冷却处理级别
        if self.consecutive_losses >= skip_trades_levels.get('level_3', {}).get('consecutive_losses', 7):
            self.cooldown_treatment_level = 3  # 重度冷却处理
            self.max_skip_trades = skip_trades_levels.get('level_3', {}).get('skip_trades', 7)
        elif self.consecutive_losses >= skip_trades_levels.get('level_2', {}).get('consecutive_losses', 5):
            self.cooldown_treatment_level = 2  # 中度冷却处理
            self.max_skip_trades = skip_trades_levels.get('level_2', {}).get('skip_trades', 5)
        else:
            self.cooldown_treatment_level = 1  # 轻度冷却处理
            self.max_skip_trades = skip_trades_levels.get('level_1', {}).get('skip_trades', 3)
        
        # 重置风险控制跳过交易计数器
        self.skipped_trades_count = 0
        
        # 激活冷却处理状态（重要：先设置状态）
        self.cooldown_treatment_active = True
        self.cooldown_treatment_start_time = datetime.now()
        
        logger.info(f"设置冷却处理状态 - 级别: {self.cooldown_treatment_level}, "
                   f"最大跳过交易: {self.max_skip_trades}, 激活状态: {self.cooldown_treatment_active}")
        
        # 更新冷却处理参数
        self._update_cooldown_treatment_parameters()
        
        logger.info(f"回测模式冷却处理已激活 - 风险控制: "
                   f"连续亏损: {self.consecutive_losses}次, 跳过交易: {self.max_skip_trades}次")
    
    def _activate_realtime_cooldown_treatment(self):
        """
        激活实盘模式冷却处理 - 停止指定时间的交易
        """
        # 获取实盘模式配置
        realtime_config = self.cooldown_treatment_config.get('realtime_mode', {})
        cold_levels = realtime_config.get('cooldown_treatment_levels', {})
        
        # 根据连续亏损次数确定冷却处理级别
        if self.consecutive_losses >= cold_levels.get('level_3', {}).get('consecutive_losses', 7):
            self.cooldown_treatment_level = 3  # 重度冷却处理
        elif self.consecutive_losses >= cold_levels.get('level_2', {}).get('consecutive_losses', 5):
            self.cooldown_treatment_level = 2  # 中度冷却处理
        else:
            self.cooldown_treatment_level = 1  # 轻度冷却处理
        
        # 获取时间级别信息用于日志
        timeframe_hours = self._get_timeframe_hours()
        timeframe_name = f"{timeframe_hours}h" if timeframe_hours < 24 else f"{timeframe_hours//24}d"
        
        # 激活冷却处理状态
        self.cooldown_treatment_active = True
        self.cooldown_treatment_start_time = datetime.now()
        
        # 更新冷却处理参数
        self._update_cooldown_treatment_parameters()
        
        logger.info(f"实盘模式冷却处理已激活 - 级别: {self.cooldown_treatment_level}, "
                   f"连续亏损: {self.consecutive_losses}次, 时间级别: {timeframe_name}")
    
    def _check_cooldown_treatment_recovery(self):
        """
        检查是否可以恢复冷却处理 - 根据模式检查恢复条件
        """
        if not self.cooldown_treatment_active:
            return
        
        # 根据模式检查恢复条件
        can_recover = False
        if self.cooldown_treatment_mode == 'backtest':
            can_recover = self._check_backtest_recovery()
        else:  # realtime mode
            can_recover = self._check_realtime_recovery()
        
        # 如果可以恢复，重置冷却处理状态
        if can_recover:
            logger.info(f"满足恢复条件，准备重置冷却处理")
            self._reset_cooldown_treatment()
    
    def _check_backtest_recovery(self):
        """
        检查回测模式恢复条件 - 风险控制：跳过交易次数完成即可恢复
        """
        recovery_condition = self.skipped_trades_count >= self.max_skip_trades
        logger.info(f"检查回测恢复条件 - 跳过交易: {self.skipped_trades_count}/{self.max_skip_trades}, "
                   f"满足恢复: {recovery_condition}")
        return recovery_condition
    
    def _check_realtime_recovery(self):
        """
        检查实盘模式恢复条件 - 时间周期到期即可恢复
        """
        realtime_config = self.cooldown_treatment_config.get('realtime_mode', {})
        max_duration = realtime_config.get('max_cooldown_treatment_duration', 72)
        
        # 检查是否超过最大冷却处理时间
        if self.cooldown_treatment_start_time:
            # 根据时间级别计算实际小时数
            timeframe_hours = self._get_timeframe_hours()
            max_duration_hours = max_duration * timeframe_hours
            elapsed_hours = (datetime.now() - self.cooldown_treatment_start_time).total_seconds() / 3600
            
            recovery_condition = elapsed_hours >= max_duration_hours
            logger.info(f"检查实盘恢复条件 - 已过时间: {elapsed_hours:.2f}h/{max_duration_hours}h, "
                       f"满足恢复: {recovery_condition}")
            return recovery_condition
        
        return False
    
    def _reset_cooldown_treatment(self):
        """
        重置冷却处理状态 - 恢复正常交易
        """
        # 记录恢复日志（在重置前记录）
        if self.cooldown_treatment_mode == 'backtest':
            # 获取当前时间用于日志
            current_time = datetime.now()
            time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"[{time_str}] 冷却处理恢复 - 已跳过 {self.skipped_trades_count} 次交易")
            logger.info(f"[{time_str}] 冷却处理恢复 - 回测模式风险控制完成: 级别{self.cooldown_treatment_level}, 已跳过{self.skipped_trades_count}次交易, 连续亏损{self.consecutive_losses}次")
        else:
            # 获取时间级别信息用于日志
            timeframe_hours = self._get_timeframe_hours()
            timeframe_name = f"{timeframe_hours}h" if timeframe_hours < 24 else f"{timeframe_hours//24}d"
            realtime_config = self.cooldown_treatment_config.get('realtime_mode', {})
            max_duration = realtime_config.get('max_cooldown_treatment_duration', 72)
            # 获取当前时间用于日志
            current_time = datetime.now()
            time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"[{time_str}] 冷却处理恢复 - {max_duration}个{timeframe_name}时间周期到期")
            logger.info(f"[{time_str}] 冷却处理恢复 - 实盘模式时间到期: 级别{self.cooldown_treatment_level}, {max_duration}个{timeframe_name}周期, 连续亏损{self.consecutive_losses}次")
        
        # 重置状态变量
        self.cooldown_treatment_active = False
        self.cooldown_treatment_level = 0
        self.cooldown_treatment_start_time = None
        
        # 重置效果参数
        self.position_size_reduction = 1.0
        
        # 重置回测模式计数器
        self.skipped_trades_count = 0
        self.max_skip_trades = 0
        
        logger.info(f"冷却处理状态已重置")
    
    def _update_cooldown_treatment_parameters(self):
        """
        更新冷却处理效果参数 - 根据当前级别设置惩罚值
        """
        if not self.cooldown_treatment_active:
            # 未激活冷却处理时，无惩罚
            self.position_size_reduction = 1.0
            return
        
        # 根据模式更新参数
        if self.cooldown_treatment_mode == 'backtest':
            self._update_backtest_parameters()
        else:  # realtime mode
            self._update_realtime_parameters()
        
        logger.info(f"冷却处理状态 - 级别: {self.cooldown_treatment_level}, "
                   f"仓位减少: {self.position_size_reduction:.2f}")
    
    def _update_backtest_parameters(self):
        """
        更新回测模式冷却处理参数 - 根据级别设置信号惩罚和仓位减少
        """
        # 获取回测模式配置
        backtest_config = self.cooldown_treatment_config.get('backtest_mode', {})
        position_reduction_levels = backtest_config.get('position_reduction_levels', {})
        
        # 根据冷却处理级别设置仓位大小减少
        if self.cooldown_treatment_level == 3:
            self.position_size_reduction = position_reduction_levels.get('level_3', 0.5)
        elif self.cooldown_treatment_level == 2:
            self.position_size_reduction = position_reduction_levels.get('level_2', 0.7)
        else:  # level 1
            self.position_size_reduction = position_reduction_levels.get('level_1', 0.8)
    
    def _update_realtime_parameters(self):
        """
        更新实盘模式冷却处理参数 - 根据级别设置信号惩罚和仓位减少
        """
        # 获取实盘模式配置
        realtime_config = self.cooldown_treatment_config.get('realtime_mode', {})
        position_reduction_levels = realtime_config.get('position_reduction_levels', {})
        
        # 根据冷却处理级别设置仓位大小减少
        if self.cooldown_treatment_level == 3:
            self.position_size_reduction = position_reduction_levels.get('level_3', 0.5)
        elif self.cooldown_treatment_level == 2:
            self.position_size_reduction = position_reduction_levels.get('level_2', 0.7)
        else:  # level 1
            self.position_size_reduction = position_reduction_levels.get('level_1', 0.8)
    

    
    def apply_cooldown_treatment_to_position_size(self, position_size):
        """
        对仓位大小应用冷却处理减少
        
        Args:
            position_size: 原始仓位大小（可能是字典或浮点数）
            
        Returns:
            float: 应用冷却处理后的仓位大小
        """
        if not self.cooldown_treatment_active:
            # 如果是字典，返回size字段；如果是浮点数，直接返回
            if isinstance(position_size, dict):
                return position_size.get('size', 0.0)
            return position_size
        
        # 获取实际的仓位大小值
        if isinstance(position_size, dict):
            actual_size = position_size.get('size', 0.0)
        else:
            actual_size = position_size
        
        # 应用仓位大小减少
        adjusted_size = actual_size * self.position_size_reduction
        
        return adjusted_size
    
    def set_timeframe(self, timeframe):
        """
        设置时间级别 - 用于实盘模式时间计算
        
        Args:
            timeframe: 时间级别字符串，如 '1h', '4h', '1d'
        """
        self.timeframe = timeframe
    
    def _get_timeframe_hours(self):
        """
        获取时间级别对应的小时数 - 用于实盘模式时间计算
        
        Returns:
            int: 时间级别对应的小时数
        """
        timeframe = getattr(self, 'timeframe', '1h')
        
        # 解析时间级别字符串
        if timeframe.endswith('h'):
            return int(timeframe[:-1])
        elif timeframe.endswith('d'):
            return int(timeframe[:-1]) * 24
        elif timeframe.endswith('w'):
            return int(timeframe[:-1]) * 24 * 7
        else:
            return 1  # 默认1小时
    
    def should_skip_trade(self):
        """
        检查是否应该跳过交易（回测模式风险控制专用）
        
        Returns:
            bool: 是否跳过交易（风险控制）
        """
        # 检查是否处于回测模式冷却处理状态
        if not self.cooldown_treatment_active or self.cooldown_treatment_mode != 'backtest':
            return False
        
        # 记录当前冷却处理状态
        logger.debug(f"🔍 冷却处理状态检查 - 级别: {self.cooldown_treatment_level}, "
                    f"已跳过: {self.skipped_trades_count}/{self.max_skip_trades}")
        
        # 检查是否还需要跳过更多交易（风险控制）
        if self.skipped_trades_count < self.max_skip_trades:
            self.skipped_trades_count += 1
            logger.info(f"风险控制跳过交易 {self.skipped_trades_count}/{self.max_skip_trades}")
            
            # 在跳过交易时检查是否可以恢复（风险控制）
            if self.skipped_trades_count >= self.max_skip_trades:
                logger.info(f"跳过交易完成，准备恢复冷却处理")
                self._reset_cooldown_treatment()
                # 重置后立即返回False，避免继续跳过交易
                return False
            
            return True
        
        # 如果已经跳过足够次数但冷却处理仍然激活，记录状态
        if self.cooldown_treatment_active:
            logger.debug(f"🔍 冷却处理状态检查 - 已跳过: {self.skipped_trades_count}/{self.max_skip_trades}, 状态: 激活")
        
        return False
    
    def get_cooldown_treatment_status(self):
        """
        获取冷却处理状态信息 - 用于调试和监控
        
        Returns:
            dict: 冷却处理状态信息字典
        """
        # 基础状态信息
        status = {
            'cooldown_treatment_active': self.cooldown_treatment_active,
            'cooldown_treatment_level': self.cooldown_treatment_level,
            'consecutive_losses': self.consecutive_losses,
            'consecutive_wins': self.consecutive_wins,
            'position_size_reduction': self.position_size_reduction,
            'trade_history_length': len(self.trade_history),
            'cooldown_treatment_mode': self.cooldown_treatment_mode
        }
        
        # 添加回测模式特有信息
        if self.cooldown_treatment_mode == 'backtest':
            status.update({
                'skipped_trades_count': self.skipped_trades_count,
                'max_skip_trades': self.max_skip_trades
            })
        
        return status
    
    def reset_risk_management(self):
        """
        重置风险管理状态 - 用于回测开始时重置所有状态
        
        重置内容：
        - 冷却处理状态
        - 连续盈亏统计
        - 交易历史
        - 仓位信息
        """
        logger.info("重置风险管理状态")
        
        # 重置冷却处理状态
        self.cooldown_treatment_active = False
        self.cooldown_treatment_level = 0
        self.cooldown_treatment_start_time = None
        
        # 重置效果参数
        self.position_size_reduction = 1.0
        
        # 重置连续盈亏统计
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        
        # 重置交易历史
        self.trade_history = []
        
        # 重置回测模式计数器
        self.skipped_trades_count = 0
        self.max_skip_trades = 0
        
        # 重置仓位信息
        self.position = 0
        self.entry_price = 0
        self.high_point = 0
        self.low_point = float('inf')
        
        # 重置交易统计
        self.trade_count = 0
        self.win_count = 0
        

        
        logger.info("风险管理状态重置完成")

    
    def generate_signals_filter_status(self):
        """
        获取信号过滤器状态
        
        Returns:
            dict: 过滤器状态信息
        """
        return {
            'enable_price_deviation_filter': self.signal_filter.enable_price_deviation_filter,
            'enable_rsi_filter': self.signal_filter.enable_rsi_filter,
            'enable_volatility_filter': self.signal_filter.enable_volatility_filter,
            'enable_volume_filter': self.signal_filter.enable_volume_filter,
            'enable_price_ma_entanglement': self.signal_filter.enable_price_ma_entanglement,
            'enable_signal_filter': self.signal_filter.enable_signal_filter,
        }


    def _calculate_direction(self,current, signal_score):
        
        """
        根据评分计算多空方向
        
        Args:
            current: 当前数据点
    
        Returns:
            int: 趋势方向 (1: 上升, -1: 下降, 0: 中性)
        """
        if signal_score >self.long_threshold:
            direction = 1
        elif signal_score <self.short_threshold:
            direction = -1
        else:
            direction = 0   
        return direction
    
    def _calculate_signal(self, data, verbose=False, silent=False):
        """
        夏普优化策略 - 交易信号计算核心方法
        
        评分系统架构：
        1. 指标基础评分 (30%): ADX + MACD + Volume + LineWMA + RSI + 情绪 + 新闻
        2. 趋势强度评分 (40%): ATR + Volume + EMA + ADX趋势
        3. 风险评分 (20%): 波动率 + 夏普率 + 最大回撤
        4. 回撤评分 (10%): 历史回撤分析 + 风险控制
        
        处理流程：
        数据验证 → 方向计算 → 评分计算 → 权重配置 → 信号过滤 → 结果输出
        
        Args:
            data: 包含技术指标的历史数据
            verbose: 是否输出详细调试信息
            silent: 是否静默模式（不输出日志）
            
        Returns:
            dict: 包含完整信号信息的字典
        """
        
        # 1.数据验证
        if len(data) < 1:
            return {'signal': 0, 'reason': f'数据不足 ({len(data)} 条)'}
        
        # 2.获取当前数据点
        current = data.iloc[-1]
        
        
        #4.计算评分
        base_score = current.get('signal_score')
        #3.计算多空方向
        original_signal = self._calculate_direction(current,base_score) 
        
        # print(f"original_signal: {original_signal}")
        trend_score = current.get('trend_score')
        risk_score = self._calculate_risk_score(current, data)            # 计算风险评分
        drawdown_score = self._calculate_drawdown_score(current, data)    # 计算回撤评
        # 4.获取权重配置
        weights = self.config.get('final_score_weights', {
            'signal_weight': 0.6,    # 指标基础评分权重
            'trend_weight': 0.4,     # 趋势强度评分权重
            'risk_weight': 0.0,      # 风险评分权重
            'drawdown_weight': 0.0   # 回撤评分权重
        })
        
        # 确保权重是数值而不是字典
        signal_weight = weights.get('signal_weight') 
        trend_weight = weights.get('trend_weight') 
        risk_weight = weights.get('risk_weight')
        drawdown_weight = weights.get('drawdown_weight')

        # print(f"adx_trend_score: {current.get('adx_trend_score', 0.0)}")
        # print(f"rsi_trend_score: {current.get('rsi_trend_score', 0.0)}")
        # print(f"macd_trend_score: {current.get('macd_trend_score', 0.0)}")
        # print(f"ema_trend_score: {current.get('ema_trend_score', 0.0)}")
        # print(f"price_trend_score: {current.get('price_trend_score', 0.0)}")
        # print(f"atr_trend_score: {current.get('atr_trend_score', 0.0)}")
        # print(f"volume_trend_score: {current.get('volume_trend_score', 0.0)}")
        # print(f"bb_trend_score: {current.get('bb_trend_score', 0.0)}")
        # print(f"obv_trend_score: {current.get('obv_trend_score', 0.0)}")

        # print(f"adx_signal: {current.get('adx_signal', 0.0)}")
        # print(f"rsi_signal: {current.get('rsi_signal', 0.0)}")
        # print(f"macd_signal: {current.get('macd_signal', 0.0)}")
        # print(f"ema_signal: {current.get('ema_signal', 0.0)}")
        # print(f"price_signal: {current.get('price_signal', 0.0)}")
        # print(f"atr_signal: {current.get('atr_signal', 0.0)}")
        # print(f"volume_signal: {current.get('volume_signal', 0.0)}")
        # print(f"bb_signal: {current.get('bb_signal', 0.0)}")
        # print(f"obv_signal: {current.get('obv_signal', 0.0)}")

       
        # 5.计算综合评分
        signal_score = (
            base_score * signal_weight +      # 指标基础评分贡献
            trend_score * trend_weight +        # 趋势强度评分贡献
            risk_score * risk_weight +          # 风险评分贡献
            drawdown_score * drawdown_weight    # 回撤评分贡献
        )


        
        # print(f"original_signal: {original_signal}")
        
        # 6.调试输出（简化版）
        if verbose:
            print(f"📊 评分: 基础={base_score:.3f}, 趋势={trend_score:.3f}, 风险={risk_score:.3f}, 回撤={drawdown_score:.3f}")
            print(f"🎯 综合评分: {signal_score:.3f}")
        
        # 7.信号过滤 - 传递计算好的趋势评分
        filtered_signal, filter_reason = self.signal_filter.filter_signal(original_signal, data, len(data)-1, verbose, trend_score=trend_score, base_score=base_score)
        
        # 记录过滤器详细信息到日志
        # 获取数据时间戳
        data_time = data.index[-1] if len(data) > 0 else "未知时间"
        if hasattr(data_time, 'strftime'):
            time_str = data_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            time_str = str(data_time)
        
        if filtered_signal == 0:
            if not silent:
                logger.info(f"[{time_str}] 信号被过滤: 原始信号={original_signal}, 过滤原因={filter_reason}")
        else:
            if not silent:
                logger.debug(f"[{time_str}] 信号通过过滤: 原始信号={original_signal}, 过滤原因={filter_reason}")
        
        # 8.确定最终信号
        if filtered_signal > 0:
            signal, reason = 1, f'做多信号 (方向: {original_signal}, 评分: {signal_score:.2f})'
        elif filtered_signal < 0:
            signal, reason = -1, f'空头信号 (方向: {original_signal}, 评分: {signal_score:.2f})'
        else:
            signal, reason = 0, f'原始信号: {original_signal}, 过滤原因: {filter_reason}'
        
        # 9.计算仓位大小
        position_size = self._calculate_position_size(signal,signal_score)
        
        # 10.构建调试信息
        debug_info = {
            #基础指标
            'adx': current.get('adx', 0.0), #ADX
            'rsi': current.get('rsi', 50.0), #RSI
            'macd': current.get('macd', 0.0), #MACD
            'lineWMA': current.get('lineWMA', 0.0), #WMA
            'openEMA': current.get('openEMA', 0.0), #EMA
            'closeEMA': current.get('closeEMA', 0.0), #EMA
            'obv': current.get('obv', 0), #OBV
            'vix_fear': current.get('vix_fear', 20.0), #VIX恐慌指数
            'greed_score': current.get('greed_score', 50.0), #贪婪指数
            'sentiment_score': current.get('sentiment_score', 0.0), #情绪评分

            #趋势指标
            'adx_trend_score': current.get('adx_trend_score', 0.0), #ADX趋势评分
            'rsi_trend_score': current.get('rsi_trend_score', 0.0), #RSI趋势评分
            'macd_trend_score': current.get('macd_trend_score', 0.0), #MACD趋势评分
            'ema_trend_score': current.get('ema_trend_score', 0.0), #EMA趋势评分
            'price_trend_score': current.get('price_trend_score', 0.0), #价格趋势评分
            'atr_trend_score': current.get('atr_trend_score', 0.0), #ATR趋势评分
            'volume_trend_score': current.get('volume_trend_score', 0.0), #成交量趋势评分
            'bb_trend_score': current.get('bb_trend_score', 0.0), #布林带趋势评分
            'obv_trend_score': current.get('obv_trend_score', 0.0), #OBV趋势评分
            
            #风险指标
            'risk_score': risk_score, #风险评分
            'drawdown_score': drawdown_score, #回撤评分

            #最终评分   
            'signal': signal, #多空方向
            'signal_score': signal_score, #信号评分 
            'base_score': base_score, #基础评分
            'trend_score': trend_score, #趋势评分
            'original_signal': original_signal, #原始信号
            'sideways_score': current.get('sideways_score', 0.0), #震荡评分
            'position_size': position_size.get('size', 0.0) if isinstance(position_size, dict) else position_size, #仓位大小
            'signal_threshold': 0.0, #信号阈值
            'reason': reason, #信号原因 (信号生成原因)
        }
        
        # 11.更新持仓周期计数
        self.update_holding_periods()
        
        # 12.返回结果
        return {
            'signal': signal, #多空方向 (1=做多, -1=做空, 0=观望)
            'signal_score': signal_score, #信号评分(综合评分)
            'base_score': base_score, #基础评分
            'trend_score': trend_score, #趋势评分 (趋势强度评分)
            'risk_score': risk_score, #风险评分 (风险控制评分)
            'drawdown_score': drawdown_score, #回撤评分 (回撤控制评分)
            'position_size': position_size, #仓位大小 (动态仓位管理)
            'reason': reason, #信号原因 (信号生成原因)
            'original_signal': {'signal': original_signal}, #原始信号信息（过滤前）
            'debug_info': debug_info, #调试信息
            'filters': {
                'signal_filter': {
                    'passed': filtered_signal != 0, #是否通过过滤
                    'reason': filter_reason
                    },
            }
        }



    # def volatility_adjusted_weights(self, volatility_index):
    #     """ 波动率越高，降低趋势指标权重 """
    #     base_weights = {
    #         'adx_weight': 0.28,
    #         'macd_weight': 0.22,
    #         'volume_weight': 0.1,
    #         'line_wma_weight': 0.15,
    #         'rsi_weight': 0.18,
    #         'sentiment_weight': 0.07
    #     }
        
    #     # 调整因子 (0.5-1.5范围)
    #     trend_factor = 1.0 / (1.0 + 0.5 * volatility_index)
    #     osc_factor = 1.0 + 0.3 * volatility_index
        
    #     adjusted_weights = base_weights.copy()
    #     adjusted_weights['adx_weight'] *= trend_factor
    #     adjusted_weights['macd_weight'] *= trend_factor
    #     adjusted_weights['line_wma_weight'] *= trend_factor
        
    #     adjusted_weights['rsi_weight'] *= osc_factor
    #     adjusted_weights['volume_weight'] *= osc_factor
        
    #     # 重新归一化
    #     total = sum(adjusted_weights.values())
    #     return {k: v/total for k,v in adjusted_weights.items()}


    def _calculate_day_score(self, current):
        """计算日评分"""
        day_score = current.get('day_score', 0.0)
        
        return day_score    

   
     
 
        
        # 计算综合评分
        signal_score = 0.0

        return signal_score 

    def update_portfolio_value(self, portfolio_value):
        """
        更新投资组合价值，用于计算夏普率
        
        Args:
            portfolio_value: 当前投资组合价值
        """
        self.portfolio_values.append(portfolio_value)
        
        # 计算收益率
        if len(self.portfolio_values) > 1:
            return_rate = (portfolio_value - self.portfolio_values[-2]) / self.portfolio_values[-2]
            self.returns.append(return_rate)
        
        # 计算夏普率并调整风险
        if len(self.portfolio_values) >= self.sharpe_lookback:
            self.adjust_risk_exposure()
    
    def adjust_risk_exposure(self):
        """动态调整风险敞口基于夏普率"""
        if len(self.returns) < self.sharpe_lookback:
            return
        
        # 计算近期收益率
        recent_returns = self.returns[-self.sharpe_lookback:]
        
        # 计算夏普率
        mean_return = np.mean(recent_returns)
        std_return = np.std(recent_returns)
        
        if std_return > 0:
            sharpe_ratio = mean_return / std_return * np.sqrt(252)  # 年化
        else:
            sharpe_ratio = 0
        
        # 动态调整风险乘数
        if sharpe_ratio < 0.5:
            self.risk_multiplier = 0.5  # 高风险时降低仓位
        elif sharpe_ratio < self.target_sharpe:
            self.risk_multiplier = 0.8
        else:
            self.risk_multiplier = min(
                1.0 + (sharpe_ratio - self.target_sharpe),
                self.max_risk_multiplier
            )
        
        # 打印调试信息
        print(f"夏普率: {sharpe_ratio:.2f}, 风险乘数: {self.risk_multiplier:.2f}")
    
    def should_stop_loss(self, current_price, current_features=None, current_time=None):
        """
        检查是否应该止损 - 固定止损 + LineWMA反转止损 + 信号评分止损
        
        Args:
            current_price: 当前价格
            current_features: 当前特征数据
            current_time: 当前时间
            
        Returns:
            tuple: (是否止损, 止损原因)
        """
        if self.position == 0:
            return False, None
        
        # 计算当前亏损比例
        if self.position == 1:  # 多仓
            loss_ratio = (self.entry_price - current_price) / self.entry_price
        else:  # 空仓
            loss_ratio = (current_price - self.entry_price) / self.entry_price
        
        # 1. 固定止损（最高优先级）
        fixed_stop_ratio = self.stop_loss_config.get('fixed_stop_loss', 0.08)  # 默认8%
        if loss_ratio >= fixed_stop_ratio:
            reason = f"固定止损(亏损{loss_ratio*100:.1f}% >= {fixed_stop_ratio*100:.1f}%)"
            time_str = current_time.strftime('%Y-%m-%d %H:%M:%S') if current_time else "N/A"
            logger.info(f"[{time_str}]  {reason}: 开仓价={self.entry_price:.2f}, 当前价={current_price:.2f}")
            return True, reason

        # 2. LineWMA反转止损（止损达到固定止损一半时执行，不判断趋势）
        if current_features is not None:
            # 获取LineWMA值
            if 'row_data' in current_features:
                line_wma = current_features['row_data'].get('lineWMA', 0)
            else:
                line_wma = current_features.get('lineWMA', 0)
            
            # 检查LineWMA是否有效，且止损达到固定止损的一半
            if line_wma is not None and line_wma > 0 and loss_ratio >= fixed_stop_ratio * 0.3:
                if self.position == 1 and current_price < line_wma:  # 多头：价格跌破LineWMA
                    reason = f"多头LineWMA反转止损(价格{current_price:.2f} < LineWMA{line_wma:.2f})"
                    time_str = current_time.strftime('%Y-%m-%d %H:%M:%S') if current_time else "N/A"
                    logger.info(f"[{time_str}]  {reason}: 亏损{loss_ratio*100:.1f}%")
                    return True, reason
                elif self.position == -1 and current_price > line_wma:  # 空头：价格突破LineWMA
                    reason = f"空头LineWMA反转止损(价格{current_price:.2f} > LineWMA{line_wma:.2f})"
                    time_str = current_time.strftime('%Y-%m-%d %H:%M:%S') if current_time else "N/A"
                    logger.info(f"[{time_str}]  {reason}: 亏损{loss_ratio*100:.1f}%")
                    return True, reason


        
        return False, None


    def should_take_profit(self, current_price, current_features=None, current_time=None):
        """检查是否应该止盈 - 盈利状态下的止盈逻辑"""
        if self.position == 0:
            return False, None
        
        # 计算当前盈利比例
        if self.position == 1:  # 多仓
            profit_ratio = (current_price - self.entry_price) / self.entry_price
        else:  # 空仓
            profit_ratio = (self.entry_price - current_price) / self.entry_price
        
        # 策略0: LineWMA反转止盈（最高优先级）
        # 只要LineWMA出现反转立即止盈，不考虑盈利状态
        if current_features is not None:
            # 获取LineWMA数据
            if 'row_data' in current_features:
                line_wma = current_features['row_data'].get('lineWMA', 0)
                current_signal_score = current_features['row_data'].get('signal_score', 0)
            else:
                line_wma = current_features.get('lineWMA', 0)
                current_signal_score = current_features.get('signal_score', 0)
            
            # print(f"current_signal_score: {current_signal_score}")
            
            # 检查LineWMA是否有效
            if line_wma is not None and line_wma > 0:
                if self.position == 1:  # 多仓：价格跌破LineWMA

                    if current_price < line_wma and current_signal_score < 0.0:
                            # 如果没有记录持仓评分，则按原逻辑执行
                            status = "盈利" if profit_ratio > 0 else "亏损"
                            reason = f"多仓LineWMA反转且信号反转止盈({status}{profit_ratio*100:.1f}%)"
                            print(f"🟢 {reason}")
                            return True, reason
                else:  # 空仓：价格突破LineWMA
                    if current_price > line_wma and current_signal_score > 0:
                            # 如果没有记录持仓评分，则按原逻辑执行
                            status = "盈利" if profit_ratio > 0 else "亏损"
                            reason = f"空仓LineWMA反转且信号反转止盈({status}{profit_ratio*100:.1f}%)"
                            print(f"🟢 {reason}")
                            return True, reason
        
        # 策略1: 时间止损止盈（第二优先级）
        # 如果持仓超过指定周期且当前盈利，立即止盈
        time_based_take_profit_enabled = self.take_profit_config.get('time_based_take_profit', True)
        time_based_periods = self.take_profit_config.get('time_based_periods', 20)
        
        if time_based_take_profit_enabled and self.holding_periods >= time_based_periods and profit_ratio > 0:
            reason = f"时间止损止盈(持仓{self.holding_periods}周期, 盈利{profit_ratio*100:.1f}%)"
            print(f"🟢 {reason}")
            return True, reason
        
        # 确保只在盈利状态下执行其他止盈逻辑
        if profit_ratio <= 0:
            return False, None
        
        # 策略2: 回调止盈（第三优先级）
        if self.take_profit_config.get('enable_callback', True):
            callback_ratio = self.take_profit_config.get('callback_ratio', 0.03)  # 统一回调3%
            
            if self.position == 1:  # 多仓
                if current_price > self.high_point:
                    self.high_point = current_price
                else:
                    current_callback_ratio = (self.high_point - current_price) / self.high_point
                    if current_callback_ratio >= callback_ratio:
                        reason = f"多仓回调止盈(盈利{profit_ratio*100:.1f}%, 回调{current_callback_ratio*100:.1f}%)"
                        print(f"🟢 {reason}")
                        return True, reason
            else:  # 空仓
                if current_price < self.low_point:
                    self.low_point = current_price
                else:
                    current_callback_ratio = (current_price - self.low_point) / self.low_point
                    if current_callback_ratio >= callback_ratio:
                        reason = f"空仓回调止盈(盈利{profit_ratio*100:.1f}%, 反弹{current_callback_ratio*100:.1f}%)"
                        print(f"🟢 {reason}")
                        return True, reason
        
        # 策略3: RSI止盈（第四优先级）
        if current_features is not None:
            # 获取RSI数据
            if 'row_data' in current_features:
                rsi = current_features['row_data'].get('RSI', 50)
            else:
                rsi = current_features.get('RSI', 50)
            
            # RSI止盈逻辑
            rsi_take_profit_enabled = self.take_profit_config.get('rsi_take_profit', True)
            if rsi_take_profit_enabled:
                if self.position == 1:  # 多仓：RSI超买时止盈
                    if rsi >= self.take_profit_config.get('rsi_overbought_take_profit', 75):
                        reason = f"多仓RSI超买止盈(盈利{profit_ratio*100:.1f}%, RSI:{rsi:.1f})"
                        print(f"🟢 {reason}")
                        return True, reason
                else:  # 空仓：RSI超卖时止盈
                    if rsi <= self.take_profit_config.get('rsi_oversold_take_profit', 25):
                        reason = f"空仓RSI超卖止盈(盈利{profit_ratio*100:.1f}%, RSI:{rsi:.1f})"
                        print(f"🟢 {reason}")
                        return True, reason
        
        return False, None
    

    
    def check_risk_management(self, current_price, current_features, current_time=None):
        """
        检查风险管理 - 根据盈亏状态分别触发止盈或止损逻辑
        
        Returns:
            tuple: (action, reason)
        """
        if self.position == 0:
            return 'hold', '无持仓'
        
        # 计算当前盈亏比例
        if self.position == 1:  # 多仓
            profit_ratio = (current_price - self.entry_price) / self.entry_price
        else:  # 空仓
            profit_ratio = (self.entry_price - current_price) / self.entry_price
        
        # 根据盈亏状态分别处理
        if profit_ratio > 0:  # 盈利状态 - 触发止盈逻辑
            logger.debug(f"盈利状态检查止盈 - 盈亏: {profit_ratio*100:.2f}%")
            should_take, take_reason = self.should_take_profit(current_price, current_features, current_time)
            if should_take:
                return 'take_profit', take_reason
        else:  # 亏损状态 - 触发止损逻辑
            logger.debug(f"亏损状态检查止损 - 盈亏: {profit_ratio*100:.2f}%")
            should_stop, stop_reason = self.should_stop_loss(current_price, current_features, current_time)
            if should_stop:
                return 'stop_loss', stop_reason
        
        # 更新高低点
        self._update_high_low_points(current_price)
        
        return 'hold', '继续持仓'
    
    def get_position_status(self, current_price):
        """
        获取当前持仓状态信息
        
        Args:
            current_price: 当前价格
            
        Returns:
            dict: 包含盈亏状态、比例等信息
        """
        if self.position == 0:
            return {
                'position': 0,
                'profit_ratio': 0,
                'status': '无持仓',
                'is_profitable': False
            }
        
        # 计算盈亏比例
        if self.position == 1:  # 多仓
            profit_ratio = (current_price - self.entry_price) / self.entry_price
        else:  # 空仓
            profit_ratio = (self.entry_price - current_price) / self.entry_price
        
        return {
            'position': self.position,
            'profit_ratio': profit_ratio,
            'status': '盈利' if profit_ratio > 0 else '亏损',
            'is_profitable': profit_ratio > 0,
            'entry_price': self.entry_price,
            'current_price': current_price
        }
    
    def should_open_position(self, signal, current_features=None, current_time=None):
        """
        检查是否应该开仓 - 防止同方向重复开仓
        
        Args:
            signal: 交易信号 (1=多头, -1=空头, 0=观望)
            current_features: 当前特征数据
            current_time: 当前时间
            
        Returns:
            bool: 是否应该开仓
        """
        # 添加调试信息
        logger.info(f"[{current_time}] should_open_position检查 - signal: {signal}, position: {self.position}")
        
        # 无信号时不开仓
        if signal == 0:
            logger.info(f"[{current_time}] 无信号时不开仓 - signal: {signal}")
            return False
        
        # 检查是否已经持有相同方向的仓位
        if self.position == signal:
            position_name = "多头" if signal == 1 else "空头"
            logger.info(f"[{current_time}] 已持有{position_name}仓位，不允许重复开仓 - position: {self.position}, signal: {signal}")
            return False
        
        # 检查冷却处理
        if hasattr(self, 'should_skip_trade') and self.should_skip_trade():
            logger.info(f"[{current_time}] 冷却处理检查失败")
            return False
        
        logger.info(f"[{current_time}] 所有检查通过，允许开仓")
        return True
    
    def _update_high_low_points(self, current_price):
        """更新持仓期间的高低点"""
        if self.position == 1:  # 多仓
            if current_price > self.high_point:
                self.high_point = current_price
        elif self.position == -1:  # 空仓
            if current_price < self.low_point:
                self.low_point = current_price
    
    def update_position_info(self, position, entry_price, current_price, current_time=None, entry_signal_score=0.0):
        """更新持仓信息"""
        self.position = position
        self.entry_price = entry_price
        
        # 记录开仓时间（当开仓时）
        if position != 0 and current_time:
            self.entry_time = current_time
            self.holding_periods = 0  # 重置持仓周期计数
            # 保存开仓时的信号评分
            self.entry_signal_score = entry_signal_score
        elif position == 0:
            self.entry_time = None
            self.holding_periods = 0  # 重置持仓周期计数
            self.entry_signal_score = 0.0
        
        # 重置高低点
        if position == 1:  # 多仓
            self.high_point = current_price
            self.low_point = float('inf')
        elif position == -1:  # 空仓
            self.high_point = float('-inf')
            self.low_point = current_price
        else:  # 无持仓
            self.high_point = float('-inf')
            self.low_point = float('inf')
    
    def update_holding_periods(self):
        """更新持仓周期计数"""
        if self.position != 0:  # 有持仓时
            self.holding_periods += 1
    

    

    
    def get_risk_status(self, data):
        """获取风险状态"""
        # 首先尝试使用历史投资组合数据
        if len(self.portfolio_values) >= 10:
            # 计算当前夏普率
            recent_returns = self.returns[-min(30, len(self.returns)):]
            if len(recent_returns) > 0:
                mean_return = np.mean(recent_returns)
                std_return = np.std(recent_returns)
                current_sharpe = mean_return / std_return * np.sqrt(252) if std_return > 0 else 0
            else:
                current_sharpe = 0
            
            # 计算平均回撤
            if len(self.portfolio_values) > 1:
                max_value = max(self.portfolio_values)
                current_value = self.portfolio_values[-1]
                current_drawdown = (max_value - current_value) / max_value
            else:
                current_drawdown = 0
            
            # 风险等级评估
            if current_sharpe > 1.0 and current_drawdown < 0.05:
                risk_level = 'low'
                status = 'excellent'
                message = f'优秀表现 - 夏普比率: {current_sharpe:.2f}, 平均回撤: {current_drawdown*100:.1f}%'
            elif current_sharpe > 0.5 and current_drawdown < 0.1:
                risk_level = 'medium'
                status = 'good'
                message = f'良好表现 - 夏普比率: {current_sharpe:.2f}, 平均回撤: {current_drawdown*100:.1f}%'
            elif current_sharpe > 0 and current_drawdown < 0.15:
                risk_level = 'medium'
                status = 'normal'
                message = f'正常风险状态 - 夏普比率: {current_sharpe:.2f}, 平均回撤: {current_drawdown*100:.1f}%'
            else:
                risk_level = 'high'
                status = 'warning'
                message = f'高风险状态 - 夏普比率: {current_sharpe:.2f}, 平均回撤: {current_drawdown*100:.1f}%'
            
            return {
                'risk_level': risk_level,
                'status': status,
                'message': message
            }
        
        # 如果没有历史数据，基于当前市场数据评估风险
        if len(data) < 5:
            return {
                'risk_level': 'low',
                'status': 'insufficient_data',
                'message': '数据不足，无法评估风险'
            }
        
        try:
            # 基于技术指标评估市场风险
            current = data.iloc[-1]
            
            # 获取关键指标
            rsi = current.get('rsi', 50)
            atr = current.get('atr', 0)
            bb_position = current.get('bb_position', 0.5)
            
            # 计算价格波动率
            if len(data) >= 20:
                price_changes = data['close'].pct_change().dropna()
                volatility = price_changes.std() * np.sqrt(252)  # 年化波动率
            else:
                volatility = 0.3  # 默认值
            
            # 风险评估逻辑
            risk_factors = []
            
            # RSI极端值检查
            if rsi > 80 or rsi < 20:
                risk_factors.append('RSI极端值')
            
            # 布林带位置检查
            if bb_position > 0.9 or bb_position < 0.1:
                risk_factors.append('价格接近布林带边界')
            
            # 波动率检查
            if volatility > 0.5:  # 50%年化波动率
                risk_factors.append('高波动率')
            
            # 综合风险评估
            if len(risk_factors) >= 2:
                risk_level = 'high'
                status = 'warning'
                message = f'高风险 - 风险因素: {", ".join(risk_factors)}'
            elif len(risk_factors) == 1:
                risk_level = 'medium'
                status = 'normal'
                message = f'中等风险 - 风险因素: {", ".join(risk_factors)}'
            else:
                risk_level = 'low'
                status = 'good'
                message = f'低风险 - 市场状态良好 (RSI: {rsi:.1f}, 波动率: {volatility*100:.1f}%)'
            
            return {
                'risk_level': risk_level,
                'status': status,
                'message': message
            }
            
        except Exception as e:
            return {
                'risk_level': 'medium',
                'status': 'unknown',
                'message': f'风险评估异常: {str(e)}'
            }
    
    def _calculate_position_size(self,signal, signal_score):
        """
        动态仓位管理 - 基于评分计算仓位大小
        
        Args:
            score: 综合评分 (正数为多头，负数为空头)
            
        Returns:
            dict: 包含仓位信息的字典
        """
       
        # 确定主导方向和评分绝对值
        if signal ==  1:
            direction = 'bullish'
        elif signal == -1:
            direction = 'bearish'
        else:
            # 评分为0时，返回零仓位
            return {
                'size': 0.0,
                'direction': 'neutral',
                'dominant_score': 0.0,
                'reason': '评分为零，无仓位'
            }
        
        # 从配置文件获取仓位管理参数
        position_config = self.config.get('position_config', {})
        full_position_threshold_min = position_config.get('full_position_threshold_min', 0.0)
        full_position_threshold_max = position_config.get('full_position_threshold_max', 0.0)
        full_position_size = position_config.get('full_position_size', 0.10)
        max_adjusted_position = position_config.get('max_adjusted_position', 0.20)
        avg_adjusted_position = position_config.get('avg_adjusted_position', 0.20)
        
        # 大幅降低信号强度要求，确保有足够交易机会
        if signal_score >= full_position_threshold_max or signal_score <= full_position_threshold_min:
            position_size = full_position_size
            reason = f"完整仓位 - {direction}评分: {signal_score:.2f}"
        else:
            # 一般仓位
            position_size = avg_adjusted_position
            reason = f"一般仓位 - {direction}评分: {signal_score:.2f}"
        
        # 应用风险乘数调整
        # 确保risk_multiplier是数值
        if isinstance(self.risk_multiplier, (int, float)):
            risk_mult = self.risk_multiplier
        else:
            risk_mult = 1.0  # 默认值
            print(f"警告: risk_multiplier不是数值类型: {type(self.risk_multiplier)}, 使用默认值1.0")
        
        adjusted_position_size = position_size * risk_mult
        
        # 确保仓位大小在合理范围内
        adjusted_position_size = max(0.0, min(max_adjusted_position, adjusted_position_size))
        
        return {
            'size': adjusted_position_size,
            'direction': direction,
            'dominant_score': signal_score,
            'reason': reason
        }
    
    def _apply_signal_filters(self, original_signal, current_data, historical_data):
        """
        信号过滤器 - 对原始信号进行质量控制
        
        Args:
            original_signal: 原始信号 (1=多头, -1=空头, 0=观望)
            current_data: 当前数据点
            historical_data: 历史数据
            
        Returns:
            dict: 过滤后的信号信息
        """
        # 如果原始信号为观望，直接返回
        if original_signal == 0:
            return {
                'signal': 0,
                'reason': '观望信号',
                'filters': {'signal_filter': {'passed': True, 'reason': '观望信号'}}
            }
        
        # 使用SignalFilter进行信号过滤
        current_index = len(historical_data) - 1
        filtered_signal, filter_reason = self.signal_filter.filter_signal(
            original_signal, historical_data, current_index, verbose=False, silent=silent
        )
        
        # 记录过滤器详细信息到日志

        # 获取数据时间戳
        data_time = historical_data.index[-1] if len(historical_data) > 0 else "未知时间"
        if hasattr(data_time, 'strftime'):
            time_str = data_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            time_str = str(data_time)
        
        if filtered_signal == 0:
            if not silent:
                logger.info(f"[{time_str}] 🚨 信号被过滤: 原始信号={original_signal}, 过滤原因={filter_reason}")
        else:
            if not silent:
                logger.debug(f"[{time_str}] ✅ 信号通过过滤: 原始信号={original_signal}, 过滤原因={filter_reason}")
        
        # 记录过滤结果
        signal_type = "多头" if original_signal == 1 else "空头"
        if filtered_signal == 0:
            if not silent:
                logger.debug(f"[{time_str}] 🚨 {signal_type}信号被过滤: {filter_reason}")
        else:
            if not silent:
                logger.debug(f"[{time_str}] ✅ {signal_type}信号通过过滤")
        
        # 构建过滤器状态信息
        filters_status = self._build_filter_status(current_data, historical_data, filter_reason)
        
        # 构建过滤原因
        reason = self._build_filter_reason(original_signal, filtered_signal, filter_reason)
        
        return {
            'signal': filtered_signal,
            'reason': reason,
            'filters': filters_status
        }
    
    def _build_filter_status(self, current_data, historical_data, filter_reason):
        """构建过滤器状态信息"""
        filters_status = {}
        current_row = historical_data.iloc[-1] if len(historical_data) > 0 else None
        
        if current_row is not None:

            
            # 波动率过滤器状态
            if self.signal_filter.enable_volatility_filter:
                volatility = historical_data['returns'].tail(self.signal_filter.volatility_period).std() if len(historical_data) >= self.signal_filter.volatility_period else 0
                volatility_passed = self.signal_filter.min_volatility <= volatility <= self.signal_filter.max_volatility
                filters_status['volatility'] = {
                    'passed': volatility_passed,
                    'reason': f"波动率: {volatility:.4f} (范围: {self.signal_filter.min_volatility:.4f}-{self.signal_filter.max_volatility:.4f})"
                }
            

            
            # 均线纠缠过滤器状态
            if self.signal_filter.enable_price_ma_entanglement:
                ma_entanglement = current_row.get('ma_entanglement_score', 0)
                entanglement_passed = ma_entanglement >= self.signal_filter.entanglement_distance_threshold
                filters_status['ma_entanglement'] = {
                    'passed': entanglement_passed,
                    'reason': f"均线纠缠: {ma_entanglement:.3f}% (阈值: {self.signal_filter.entanglement_distance_threshold}%)"
                }

            # 趋势过滤器状态
            if self.signal_filter.enable_signal_filter:
                trend_score = abs(current_row.get('trend_score', 0.5))  # 使用绝对值
                # 趋势过滤器逻辑：检查趋势评分是否在有效范围内
                trend_passed = (trend_score >= self.signal_filter.trend_filter_threshold_min and 
                               trend_score <= self.signal_filter.trend_filter_threshold_max)
                filters_status['trend'] = {
                    'passed': trend_passed,
                    'reason': f"趋势评分: {trend_score:.2f} (有效范围: {self.signal_filter.trend_filter_threshold_min:.2f}-{self.signal_filter.trend_filter_threshold_max:.2f})"
                }

            # RSI过滤器状态
            if self.signal_filter.enable_rsi_filter:
                rsi = current_row.get('rsi', 50)
                # RSI过滤器逻辑：避免超买超卖区域
                rsi_passed = (rsi >= self.signal_filter.rsi_oversold_threshold and 
                             rsi <= self.signal_filter.rsi_overbought_threshold)
                filters_status['rsi'] = {
                    'passed': rsi_passed,
                    'reason': f"RSI: {rsi:.2f} (范围: {self.signal_filter.rsi_oversold_threshold:.2f}-{self.signal_filter.rsi_overbought_threshold:.2f})"
                }

        # 总体过滤器状态
        filters_status['signal_filter'] = {
            'passed': True,
            'reason': filter_reason
        }
        
        return filters_status
    
    def _build_filter_reason(self, original_signal, filtered_signal, filter_reason):
        """构建过滤原因"""
        if filtered_signal == 0:
            return f"原始信号: {original_signal}, 过滤原因: {filter_reason}"
        else:
            signal_type = "多头" if original_signal == 1 else "空头"
            if "信号通过过滤" in filter_reason:
                return filter_reason
            else:
                return f"{signal_type}信号通过过滤: {filter_reason}"

    
    

    def generate_signals(self, features, verbose=False, silent=False):
        """
        获取交易信号 - 适配回测系统的接口
        
        Args:
            features: 包含技术指标的DataFrame
            verbose: 是否输出详细信息
            silent: 是否静默模式（不输出日志）
            
        Returns:
            dict: 包含信号信息的字典
        """
        try:
            # 调用内部的计算信号方法
            signal_info = self._calculate_signal(features, verbose, silent)
            
            if verbose:
                # 简化输出，只显示关键信息
                signal_type = "多头" if signal_info['signal'] == 1 else "空头" if signal_info['signal'] == -1 else "观望"
                print(f"🎯 信号: {signal_type}({signal_info['signal']}), 评分: {signal_info['signal_score']:.3f}")
                
                # 显示关键指标（仅在verbose模式下）
                if 'debug_info' in signal_info:
                    debug = signal_info['debug_info']
                    print(f"📊 指标: ADX={debug['adx']:.1f}, RSI={debug['rsi']:.1f}, MACD={debug['macd']:.1f}")
                
                # 显示仓位信息
                if 'position_size' in signal_info:
                    pos_info = signal_info['position_size']
                    if isinstance(pos_info, dict):
                        print(f"💰 仓位: {pos_info.get('size', 0):.1%} ({pos_info.get('reason', 'N/A')})")
                    else:
                        print(f"💰 仓位: {pos_info:.1%}")
                
                # 显示过滤器状态（简化版）
                if 'filters' in signal_info:
                    filters = signal_info['filters']
                    passed_filters = sum(1 for f in filters.values() if f['passed'])
                    total_filters = len(filters)
                    
                    if passed_filters == total_filters:
                        print(f"✅ 过滤器: {passed_filters}/{total_filters} 通过")
                    else:
                        print(f"❌ 过滤器: {passed_filters}/{total_filters} 通过")
                        # 只显示失败的过滤器
                        for filter_name, filter_status in filters.items():
                            if not filter_status['passed']:
                                print(f"   ❌ {filter_name}: {filter_status['reason']}")
            
            return signal_info
            
        except Exception as e:
            if verbose:
                print(f"❌ 获取信号异常: {e}")
                import traceback
                print(f"详细错误信息: {traceback.format_exc()}")
            return {'signal': 0, 'strength': 0, 'reason': f'信号计算异常: {e}'}
    
    
    def get_parameter(self, category, key=None):
        """
        获取参数值
        
        Args:
            category: 参数类别
            key: 参数键（可选）
            
        Returns:
            参数值
        """
        if category in self.config:
            if key is None:
                return self.config[category]
            elif key in self.config[category]:
                return self.config[category][key]
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 参数键不存在: {category}.{key}")
                return None
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 参数类别不存在: {category}")
            return None
    

    

    
    def _deep_merge(self, default_config, user_config):
        """
        深度合并配置字典
        
        Args:
            default_config: 默认配置
            user_config: 用户配置
            
        Returns:
            dict: 合并后的配置
        """
        result = default_config.copy()
        
        for key, value in user_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
                
        return result

     


    def dynamic_weights(self, adx_value, last_close=None, atr_value=None):
        """动态权重调整
        Args:
            adx_value: 当前ADX值（标量）
            last_close: 最新收盘价（用于价格位置判断）
            atr_value: 当前ATR值（可选，用于波动率判断）
        Returns:
            dict: 各指标权重配置
        """
        # 输入标准化处理
        if hasattr(adx_value, '__len__') and len(adx_value) > 1:
            adx_value = adx_value.iloc[-1] if hasattr(adx_value, 'iloc') else adx_value[-1]
        
        # 基础权重配置
        strong_trend = {
            'adx': 0.35, 
            'ema': 0.30,
            'atr': 0.15,
            'volume': 0.05,
            'rsi': 0.10,
            'bb': 0.05
        }
        medium_trend = {
            'adx': 0.30,
            'ema': 0.30,
            'atr': 0.15,
            'volume': 0.10,
            'rsi': 0.10,
            'bb': 0.05
        }
        ranging = {
            'rsi': 0.30,
            'ema': 0.35,
            'adx': 0.10,
            'atr': 0.10,
            'volume': 0.10,
            'bb': 0.05
        }
        
        # 平滑过渡处理（避免参数突变）
        if adx_value > 40:
            # 强趋势市：如果接近边界则混合中等趋势配置
            if adx_value < 45:
                mix_factor = (adx_value - 40) / 5.0
                return self._mix_weights(strong_trend, medium_trend, mix_factor)
            return strong_trend
        elif adx_value > 25:
            # 中等趋势：可能在两个边界附近
            if adx_value > 35:  # 接近强趋势
                mix_factor = (adx_value - 35) / 5.0
                return self._mix_weights(medium_trend, strong_trend, mix_factor)
            elif adx_value < 30:  # 接近震荡市
                mix_factor = (30 - adx_value) / 5.0
                return self._mix_weights(medium_trend, ranging, mix_factor)
            return medium_trend
        else:
            # 震荡市：如果接近边界则混合中等趋势配置
            if adx_value > 20:
                mix_factor = (adx_value - 20) / 5.0
                return self._mix_weights(ranging, medium_trend, mix_factor)
            return ranging


    def _mix_weights(self, weights1, weights2, factor):
        """混合两种权重配置
        Args:
            weights1: 主配置
            weights2: 次配置
            factor: 混合因子(0-1)
        Returns:
            混合后的权重配置
        """
        mixed = {}
        for k in weights1.keys():
            mixed[k] = weights1[k] * (1-factor) + weights2[k] * factor
        return mixed

    def _calculate_trend_score(self, current):
        """
        计算趋势强度评分
        
        Args:
            current: 当前数据点
            
        Returns:
            float: 趋势强度评分 (多头为正分，空头为负分)
        """
         
        
        # 动态权重
        dynamic_weights=self.dynamic_weights(current.get('adx', 0))
        atr_trend_weight = dynamic_weights.get('atr')
        volume_trend_weight = dynamic_weights.get('volume')
        ema_trend_weight = dynamic_weights.get('ema')
        adx_trend_weight = dynamic_weights.get('adx')
        rsi_trend_weight = dynamic_weights.get('rsi')
        bb_trend_weight = dynamic_weights.get('bb')
        
         

        # 2.1 ADX趋势分析
        adx_trend_score = current.get('adx_trend_score', 0.0)
        
        # 2.2 ATR波动趋势分析
        atr_trend_score = current.get('atr_trend_score', 0.0)
        
        # 2.3 EMA趋势分析
        ema_trend_score =current.get('ema_trend_score', 0.0)
        
        # 2.4 交易量趋势分析 
        volume_trend_score=current.get('volume_trend_score', 0.0)

        #2.5 RSI趋势分析
        rsi_trend_score=current.get('rsi_trend_score', 0.0)

        #2.6 布林带趋势分析
        bb_trend_score=current.get('bb_trend_score', 0.0)

        # print(f"adx: {current.get('adx', 0.0)}")
        # print(f"adx_trend_score: {adx_trend_score}")
        # print(f"atr_trend_score: {atr_trend_score}")
        # print(f"ema_trend_score: {ema_trend_score}")
        # print(f"volume_trend_score: {volume_trend_score}")
        # print(f"rsi_trend_score: {rsi_trend_score}")
        # print(f"bb_trend_score: {bb_trend_score}")

        # 3.1最终趋势评分 - 所有评分都是正值
        trend_score = (
            atr_trend_score * atr_trend_weight +
            volume_trend_score * volume_trend_weight +
            ema_trend_score * ema_trend_weight +
            adx_trend_score * adx_trend_weight +
            rsi_trend_score * rsi_trend_weight+
            bb_trend_score * bb_trend_weight
        )
        
        # 3.2确保趋势评分在合理范围内（0-1）
        trend_score = max(0.0, min(1.0, trend_score))
        
        # 添加调试信息（仅在debug模式下）
        if hasattr(self, 'debug_mode') and self.debug_mode:
            print(f"📊 趋势评分详情:")
            print(f"   ADX趋势: {adx_trend_score:.3f}")
            print(f"   ATR趋势: {atr_trend_score:.3f}")
            print(f"   EMA趋势: {ema_trend_score:.3f}")
            print(f"   成交量趋势: {volume_trend_score:.3f}")
            print(f"   RSI趋势: {rsi_trend_score:.3f}")
            print(f"   BB趋势: {bb_trend_score:.3f}")
            print(f"   最终趋势评分: {trend_score:.3f}")
        
        return trend_score
            
         
    
    def _calculate_risk_score(self, current, data):
        """
        计算风险评分
        
        Args:
            current: 当前数据点
            data: 历史数据
            
        Returns:
            float: 风险评分 (正值，0-1)
        """
        if len(data) < 30:
            return 0.5  # 数据不足时返回中性评分
        
        # 计算波动率
        returns = data['close'].pct_change().dropna()
        if len(returns) < 30:
            return 0.5
        
        volatility = returns.std()
        
        # 计算夏普比率 - 使用配置中的窗口期
        short_window = getattr(self, 'short_window', 30)  # 默认30
        long_window = getattr(self, 'long_window', 90)    # 默认90
        
        sharpe_short = current.get(f"sharpe_ratio_{short_window}", 0.0)
        sharpe_long = current.get(f"sharpe_ratio_{long_window}", 0.0)
        
        # 风险评分：波动率越低，夏普率越高，风险评分越高
        volatility_score = max(0.0, 1.0 - volatility * 10)  # 波动率越低越好
        sharpe_score = min(1.0, max(0.0, (sharpe_short + sharpe_long) / 2))  # 夏普率越高越好
        
        # 综合风险评分 - 都使用正值
        risk_score = (volatility_score + sharpe_score) / 2
        
        # 确保返回正值
        return max(0.0, min(1.0, risk_score))

    def _calculate_drawdown_score(self, current, data):
        """
        计算回撤评分
        
        Args:
            current: 当前数据点
            data: 历史数据
            
        Returns:
            float: 回撤评分 (正值，0-1)
        """
        if len(data) < 30:
            return 0.5  # 数据不足时返回中性评分
        
        # 获取最大回撤 - 使用配置中的窗口期
        short_window = getattr(self, 'short_window', 30)  # 默认30
        long_window = getattr(self, 'long_window', 90)    # 默认90
        
        max_dd_short = current.get(f'max_drawdown_{short_window}', 0.0)
        max_dd_long = current.get(f'max_drawdown_{long_window}', 0.0)
        
        # 回撤评分：回撤越小，评分越高
        dd_short_score = max(0.0, 1.0 - abs(max_dd_short) * 2)  # 回撤越小越好
        dd_long_score = max(0.0, 1.0 - abs(max_dd_long) * 2)  # 回撤越小越好
        
        # 综合回撤评分 - 都使用正值
        drawdown_score = (dd_short_score + dd_long_score) / 2
        
        # 确保返回正值
        return max(0.0, min(1.0, drawdown_score))