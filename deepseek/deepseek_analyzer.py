# -*- coding: utf-8 -*-
"""
DeepSeek API ETHUSDT实时技术指标分析器
使用DeepSeek API获取ETHUSDT的实时技术指标，包括MACD、ADX、ATR、布林带等
强制返回JSON格式的趋势分析、支撑阻力位等信息
"""

import requests
import json
import time
import logging
import os
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TRADING_CONFIG, DEBUG_CONFIG

# 尝试导入python-dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("警告: 未安装python-dotenv，请运行: pip install python-dotenv")

# 配置日志
logging.basicConfig(level=getattr(logging, DEBUG_CONFIG['LOG_LEVEL']))
logger = logging.getLogger(__name__)

class DeepSeekAnalyzer:
    """
    DeepSeek API分析器
    用于获取ETHUSDT实时技术指标和趋势分析
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.deepseek.com"):
        """
        初始化DeepSeek分析器
        
        Args:
            api_key: DeepSeek API密钥，如果为None则从环境变量或.env文件中读取
            base_url: DeepSeek API基础URL
        """
        # 获取API密钥
        if api_key is None:
            api_key = os.getenv('DEEPSEEK_API_KEY')
            if api_key is None:
                logger.warning("未找到DEEPSEEK_API_KEY，DeepSeek API功能将不可用")
                api_key = "dummy_key"  # 使用占位符以支持基础功能
        
        self.api_key = api_key
        self.base_url = base_url
        self.session = self._create_session()
        
        # 缓存配置 - 从配置文件读取
        try:
            from config import OPTIMIZED_STRATEGY_CONFIG
            self.cache_duration = OPTIMIZED_STRATEGY_CONFIG.get('cache_timeout', 3600)  # 默认1小时
        except ImportError:
            self.cache_duration = 3600  # 默认1小时
        
        self.last_analysis = None
        self.last_analysis_time = 0
        
    def _create_session(self) -> requests.Session:
        """
        创建配置了重试机制和连接池的requests session
        
        Returns:
            配置好的requests.Session对象
        """
        session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,  # 总重试次数
            backoff_factor=1,  # 退避因子
            status_forcelist=[429, 500, 502, 503, 504],  # 需要重试的HTTP状态码
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        # 配置连接适配器
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,  # 连接池大小
            pool_maxsize=20,     # 最大连接数
            pool_block=False     # 连接池满时不阻塞
        )
        
        # 将适配器应用到http和https
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 只有在有有效API密钥时才设置认证头
        if self.api_key != "dummy_key":
            session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'TradingBot/1.0'
            })
        
        return session
    
    def test_api_connection(self) -> bool:
        """
        测试DeepSeek API连接
        
        Returns:
            True if connection successful, False otherwise
        """
        if self.api_key == "dummy_key":
            logger.warning("API密钥未配置，无法测试连接")
            return False
            
        try:
            url = f"{self.base_url}/v1/models"
            timeout_config = (5, 10)  # 较短的超时时间用于测试
            
            logger.info("正在测试DeepSeek API连接...")
            response = self.session.get(url, timeout=timeout_config)
            response.raise_for_status()
            
            logger.info("DeepSeek API连接测试成功")
            return True
            
        except requests.exceptions.Timeout:
            logger.error("DeepSeek API连接测试超时")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("DeepSeek API连接测试失败 - 网络连接问题")
            return False
        except requests.exceptions.HTTPError as e:
            if hasattr(e.response, 'status_code'):
                if e.response.status_code == 401:
                    logger.error("DeepSeek API连接测试失败 - API密钥无效")
                else:
                    logger.error(f"DeepSeek API连接测试失败 - HTTP {e.response.status_code}")
            return False
        except Exception as e:
            logger.error(f"DeepSeek API连接测试失败: {e}")
            return False
    
    def get_ethusdt_data(self, timeframe: str = '1h', limit: int = 100) -> Optional[pd.DataFrame]:
        """
        获取ETHUSDT的K线数据
        
        Args:
            timeframe: 时间框架 (1m, 5m, 15m, 1h, 4h, 1d)
            limit: 获取的K线数量
            
        Returns:
            DataFrame包含OHLCV数据
        """
        try:
            # 使用Binance API获取数据
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': 'ETHUSDT',
                'interval': timeframe,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 转换为DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # 数据类型转换
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"获取ETHUSDT数据失败: {e}")
            return None
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        计算技术指标
        
        Args:
            df: 包含OHLCV数据的DataFrame
            
        Returns:
            包含所有技术指标的字典
        """
        try:
            indicators = {}
            
            # 计算MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            histogram = macd - signal
            
            indicators['macd'] = {
                'macd': float(macd.iloc[-1]),
                'signal': float(signal.iloc[-1]),
                'histogram': float(histogram.iloc[-1]),
                'trend': 'bullish' if macd.iloc[-1] > signal.iloc[-1] else 'bearish'
            }
            
            # 计算ADX (Average Directional Index) - 改进版本
            high = df['high']
            low = df['low']
            close = df['close']
            
            # 检查数据是否足够
            if len(df) < 28:  # 需要至少28个数据点来计算ADX
                logger.warning(f"数据不足，无法计算ADX。需要至少28个数据点，当前只有{len(df)}个")
                indicators['adx'] = {
                    'adx': None,
                    'di_plus': None,
                    'di_minus': None,
                    'trend_strength': 'unknown',
                    'trend_direction': 'unknown',
                    'status': 'insufficient_data'
                }
            else:
                # True Range
                tr1 = high - low
                tr2 = abs(high - close.shift(1))
                tr3 = abs(low - close.shift(1))
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr = tr.rolling(window=14).mean()
                
                # Directional Movement
                dm_plus = (high - high.shift(1)).clip(lower=0)
                dm_minus = (low.shift(1) - low).clip(lower=0)
                
                # 当DM+ > DM- 且 DM+ > 0时，DM+ = DM+，否则DM+ = 0
                dm_plus = np.where((dm_plus > dm_minus) & (dm_plus > 0), dm_plus, 0)
                dm_minus = np.where((dm_minus > dm_plus) & (dm_minus > 0), dm_minus, 0)
                
                # 平滑处理 - 使用指数移动平均，避免除零
                dm_plus_smoothed = pd.Series(dm_plus, index=atr.index).ewm(span=14, adjust=False).mean()
                dm_minus_smoothed = pd.Series(dm_minus, index=atr.index).ewm(span=14, adjust=False).mean()
                
                # 避免除零错误 - 确保所有操作数都是pandas Series且索引一致
                di_plus = pd.Series(np.where(atr > 0, 100 * dm_plus_smoothed / atr, 0), index=atr.index)
                di_minus = pd.Series(np.where(atr > 0, 100 * dm_minus_smoothed / atr, 0), index=atr.index)
                
                # ADX计算 - 改进版本
                # 避免除零错误，使用更稳定的计算方式
                denominator = di_plus + di_minus
                dx = np.where(denominator > 0, 100 * abs(di_plus - di_minus) / denominator, 0)
                adx = pd.Series(dx).ewm(span=14, adjust=False).mean()
                
                # 获取最新值并处理NaN
                adx_value = adx.iloc[-1]
                di_plus_value = di_plus.iloc[-1]
                di_minus_value = di_minus.iloc[-1]
                
                # 检查是否为NaN
                if pd.isna(adx_value) or pd.isna(di_plus_value) or pd.isna(di_minus_value):
                    # 尝试使用最近的有效值
                    adx_valid = adx.dropna()
                    di_plus_valid = di_plus.dropna()
                    di_minus_valid = di_minus.dropna()
                    
                    if len(adx_valid) > 0:
                        adx_value = adx_valid.iloc[-1]
                    else:
                        adx_value = 0.0
                        
                    if len(di_plus_valid) > 0:
                        di_plus_value = di_plus_valid.iloc[-1]
                    else:
                        di_plus_value = 0.0
                        
                    if len(di_minus_valid) > 0:
                        di_minus_value = di_minus_valid.iloc[-1]
                    else:
                        di_minus_value = 0.0
                
                # 确保值在合理范围内
                adx_value = max(0.0, min(100.0, adx_value))
                di_plus_value = max(0.0, min(100.0, di_plus_value))
                di_minus_value = max(0.0, min(100.0, di_minus_value))
                
                indicators['adx'] = {
                    'adx': float(adx_value),
                    'di_plus': float(di_plus_value),
                    'di_minus': float(di_minus_value),
                    'trend_strength': 'strong' if adx_value > 25 else 'weak',
                    'trend_direction': 'bullish' if di_plus_value > di_minus_value else 'bearish',
                    'status': 'calculated'
                }
            
            # 计算ATR
            indicators['atr'] = {
                'atr': float(atr.iloc[-1]),
                'atr_percent': float(atr.iloc[-1] / close.iloc[-1] * 100)
            }
            
            # 计算布林带
            sma = close.rolling(window=20).mean()
            std = close.rolling(window=20).std()
            upper_band = sma + (std * 2)
            lower_band = sma - (std * 2)
            
            current_price = float(close.iloc[-1])
            current_sma = float(sma.iloc[-1])
            current_upper = float(upper_band.iloc[-1])
            current_lower = float(lower_band.iloc[-1])
            
            # 计算布林带位置
            bb_position = (current_price - current_lower) / (current_upper - current_lower)
            
            indicators['bollinger_bands'] = {
                'upper': current_upper,
                'middle': current_sma,
                'lower': current_lower,
                'position': float(bb_position),
                'squeeze': 'yes' if (current_upper - current_lower) / current_sma < 0.1 else 'no'
            }
            
            # 计算RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            indicators['rsi'] = {
                'rsi': float(rsi.iloc[-1]),
                'status': 'overbought' if rsi.iloc[-1] > 70 else 'oversold' if rsi.iloc[-1] < 30 else 'neutral'
            }
            
            # 计算交易量指标
            volume = df['volume']
            volume_sma = volume.rolling(window=20).mean()
            volume_ratio = volume.iloc[-1] / volume_sma.iloc[-1] if volume_sma.iloc[-1] > 0 else 1.0
            
            # 计算价格波动指标
            price_change = close.pct_change()
            price_volatility = price_change.rolling(window=20).std() * 100  # 转换为百分比
            
            # 计算价格动量
            price_momentum = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] * 100  # 5周期价格变化百分比
            
            indicators['volume'] = {
                'current_volume': float(volume.iloc[-1]),
                'avg_volume': float(volume_sma.iloc[-1]),
                'volume_ratio': float(volume_ratio),
                'volume_trend': 'high' if volume_ratio > 1.5 else 'normal' if volume_ratio > 0.8 else 'low'
            }
            
            indicators['price_volatility'] = {
                'volatility': float(price_volatility.iloc[-1]),
                'volatility_level': 'high' if price_volatility.iloc[-1] > 3.0 else 'medium' if price_volatility.iloc[-1] > 1.5 else 'low',
                'price_momentum': float(price_momentum),
                'momentum_direction': 'up' if price_momentum > 0 else 'down'
            }
            
            # 计算支撑和阻力位
            support_resistance = self.calculate_support_resistance(df)
            indicators['support_resistance'] = support_resistance
            
            return indicators
            
        except Exception as e:
            logger.error(f"计算技术指标失败: {e}")
            return {}
    
    def calculate_support_resistance(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """
        计算支撑和阻力位
        
        Args:
            df: 包含OHLCV数据的DataFrame
            
        Returns:
            包含支撑和阻力位的字典
        """
        try:
            high = df['high']
            low = df['low']
            close = df['close']
            
            # 使用最近20个周期的数据计算
            recent_highs = high.tail(20)
            recent_lows = low.tail(20)
            
            # 阻力位：最近的高点
            resistance_levels = sorted(recent_highs.nlargest(3).unique(), reverse=True)
            
            # 支撑位：最近的低点
            support_levels = sorted(recent_lows.nsmallest(3).unique())
            
            # 添加当前价格附近的水平
            current_price = close.iloc[-1]
            
            # 如果阻力位太远，添加当前价格上方的水平
            if resistance_levels and resistance_levels[0] > current_price * 1.05:
                resistance_levels.insert(0, current_price * 1.02)
            
            # 如果支撑位太远，添加当前价格下方的水平
            if support_levels and support_levels[0] < current_price * 0.95:
                support_levels.append(current_price * 0.98)
            
            return {
                'resistance': [float(level) for level in resistance_levels[:3]],
                'support': [float(level) for level in support_levels[:3]],
                'current_price': float(current_price)
            }
            
        except Exception as e:
            logger.error(f"计算支撑阻力位失败: {e}")
            return {'resistance': [], 'support': [], 'current_price': 0.0}
    
    def calculate_trend_score(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算期货趋势评分（考虑多空头）
        
        Args:
            indicators: 技术指标字典
            
        Returns:
            趋势评分结果
        """
        try:
            score = 0.0
            details = {}
            
            # MACD趋势评分 (权重: 0.25)
            macd = indicators.get('macd', {})
            macd_trend = macd.get('trend', 'neutral')
            histogram = macd.get('histogram', 0)
            
            if macd_trend == 'bullish':
                macd_score = 0.8
                if histogram > 0:  # 柱状图为正，多头信号更强
                    macd_score += 0.2
            elif macd_trend == 'bearish':
                macd_score = 0.2
                if histogram < 0:  # 柱状图为负，空头信号更强
                    macd_score -= 0.2
            else:
                macd_score = 0.5  # 中性
            macd_score = max(0.0, min(1.0, macd_score))
            details['macd_score'] = macd_score
            score += macd_score * 0.25
            
            # ADX趋势评分 (权重: 0.25)
            adx = indicators.get('adx', {})
            adx_value = adx.get('adx', 0)
            adx_direction = adx.get('trend_direction', 'neutral')
            
            if adx_value > 25:  # 强趋势
                adx_score = 0.9
                if adx_direction == 'bullish':
                    adx_score += 0.1  # 多头趋势
                else:
                    adx_score -= 0.1  # 空头趋势
            else:  # 弱趋势
                adx_score = 0.5
            adx_score = max(0.0, min(1.0, adx_score))
            details['adx_score'] = adx_score
            score += adx_score * 0.25
            
            # 布林带位置评分 (权重: 0.2)
            bb = indicators.get('bollinger_bands', {})
            bb_position = bb.get('position', 0.5)
            
            # 期货考虑：接近上轨可能是做空机会，接近下轨可能是做多机会
            if bb_position > 0.8:  # 接近上轨，可能做空
                position_score = 0.2
            elif bb_position < 0.2:  # 接近下轨，可能做多
                position_score = 0.8
            elif bb_position > 0.6:  # 偏上，谨慎做多
                position_score = 0.4
            elif bb_position < 0.4:  # 偏下，谨慎做空
                position_score = 0.6
            else:  # 中间位置，中性
                position_score = 0.5
            details['position_score'] = position_score
            score += position_score * 0.2
            
            # RSI动量评分 (权重: 0.15)
            rsi = indicators.get('rsi', {})
            rsi_value = rsi.get('rsi', 50)
            
            # 期货考虑：超买可能是做空信号，超卖可能是做多信号
            if rsi_value > 75:  # 极度超买，强烈做空信号
                momentum_score = 0.1
            elif rsi_value > 70:  # 超买，做空信号
                momentum_score = 0.3
            elif rsi_value < 25:  # 极度超卖，强烈做多信号
                momentum_score = 0.9
            elif rsi_value < 30:  # 超卖，做多信号
                momentum_score = 0.7
            elif 40 <= rsi_value <= 60:  # 中性区域
                momentum_score = 0.5
            else:  # 其他情况
                momentum_score = 0.5
            details['momentum_score'] = momentum_score
            score += momentum_score * 0.15
            
            # 价格动量评分 (权重: 0.1)
            # 基于价格波动指标计算动量
            price_volatility_data = indicators.get('price_volatility', {})
            price_momentum = price_volatility_data.get('price_momentum', 0)
            momentum_direction = price_volatility_data.get('momentum_direction', 'neutral')
            
            # 期货考虑：价格动量和方向
            if momentum_direction == 'up' and price_momentum > 1.0:  # 上涨动量强
                momentum_score = 0.8
            elif momentum_direction == 'down' and price_momentum < -1.0:  # 下跌动量强
                momentum_score = 0.2
            elif abs(price_momentum) < 0.5:  # 动量较弱
                momentum_score = 0.5
            else:
                momentum_score = 0.5
            details['price_momentum_score'] = momentum_score
            score += momentum_score * 0.1
            
            # 交易量评分 (权重: 0.05)
            volume_data = indicators.get('volume', {})
            volume_ratio = volume_data.get('volume_ratio', 1.0)
            volume_trend = volume_data.get('volume_trend', 'normal')
            
            # 期货考虑：高交易量通常支持趋势
            if volume_trend == 'high' and volume_ratio > 1.5:
                volume_score = 0.8  # 高交易量支持趋势
            elif volume_trend == 'normal':
                volume_score = 0.6  # 正常交易量
            else:
                volume_score = 0.4  # 低交易量，趋势可能不可靠
            details['volume_score'] = volume_score
            score += volume_score * 0.05
            
            # 确定趋势方向和强度
            if score > 0.7:
                trend_level = 'strong_bullish'
                trend_direction = 'long'
            elif score > 0.6:
                trend_level = 'bullish'
                trend_direction = 'long'
            elif score > 0.4:
                trend_level = 'neutral'
                trend_direction = 'neutral'
            elif score > 0.3:
                trend_level = 'bearish'
                trend_direction = 'short'
            else:
                trend_level = 'strong_bearish'
                trend_direction = 'short'
            
            return {
                'trend_score': round(score, 3),
                'trend_level': trend_level,
                'trend_direction': trend_direction,  # 新增：明确多空方向
                'details': details
            }
            
        except Exception as e:
            logger.error(f"计算趋势评分失败: {e}")
            return {'trend_score': 0.5, 'trend_level': 'neutral', 'trend_direction': 'neutral', 'details': {}}
    
    def calculate_indicator_score(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算期货指标评分（考虑多空头信号）
        
        Args:
            indicators: 技术指标字典
            
        Returns:
            指标评分结果
        """
        try:
            score = 0.0
            details = {}
            
            # MACD指标评分 (权重: 0.25)
            macd = indicators.get('macd', {})
            macd_value = macd.get('macd', 0)
            signal_value = macd.get('signal', 0)
            histogram_value = macd.get('histogram', 0)
            
            # MACD线评分 - 期货考虑：金叉死叉信号
            if macd_value > signal_value:
                macd_line_score = 0.8
                if histogram_value > 0:  # 柱状图为正，多头信号更强
                    macd_line_score += 0.2
            else:
                macd_line_score = 0.2
                if histogram_value < 0:  # 柱状图为负，空头信号更强
                    macd_line_score -= 0.2
            macd_line_score = max(0.0, min(1.0, macd_line_score))
            details['macd_line_score'] = macd_line_score
            
            # 信号线评分 - 期货考虑：信号强度
            signal_score = 0.5 + (abs(signal_value) / 100) if abs(signal_value) < 100 else 0.5
            signal_score = max(0.0, min(1.0, signal_score))
            details['signal_score'] = signal_score
            
            macd_score = (macd_line_score + signal_score) / 2
            details['macd_score'] = macd_score
            score += macd_score * 0.25
            
            # RSI指标评分 (权重: 0.25) - 期货考虑：超买超卖信号
            rsi = indicators.get('rsi', {})
            rsi_value = rsi.get('rsi', 50)
            
            # 期货交易中，RSI的极端值可能是反转信号
            if 45 <= rsi_value <= 55:  # 中性区域，适合趋势跟踪
                rsi_score = 0.8
            elif 35 <= rsi_value < 45 or 55 < rsi_value <= 65:  # 温和区域
                rsi_score = 0.7
            elif rsi_value < 25 or rsi_value > 75:  # 极端超买超卖，可能反转
                rsi_score = 0.9
            elif rsi_value < 35 or rsi_value > 65:  # 超买超卖区域
                rsi_score = 0.6
            else:  # 其他情况
                rsi_score = 0.5
            details['rsi_score'] = rsi_score
            score += rsi_score * 0.25
            
            # 布林带指标评分 (权重: 0.25) - 期货考虑：突破和回归
            bb = indicators.get('bollinger_bands', {})
            bb_position = bb.get('position', 0.5)
            bb_squeeze = bb.get('squeeze', 'no')
            
            # 位置评分 - 期货考虑：边界突破和回归
            if 0.4 <= bb_position <= 0.6:  # 中间区域，适合趋势跟踪
                bb_position_score = 0.8
            elif bb_position < 0.2 or bb_position > 0.8:  # 极端位置，可能反转
                bb_position_score = 0.9
            elif bb_position < 0.4 or bb_position > 0.6:  # 偏边界，谨慎操作
                bb_position_score = 0.6
            else:  # 其他情况
                bb_position_score = 0.5
            
            # 挤压评分 - 期货考虑：波动率收缩后的突破
            bb_squeeze_score = 0.8 if bb_squeeze == 'yes' else 0.6  # 挤压后可能有大行情
            
            bb_score = (bb_position_score + bb_squeeze_score) / 2
            details['bollinger_bands_score'] = bb_score
            score += bb_score * 0.25
            
            # ATR指标评分 (权重: 0.25) - 期货考虑：波动率和止损设置
            atr = indicators.get('atr', {})
            atr_percent = atr.get('atr_percent', 2.0)
            
            # 波动率评分 - 期货考虑：适中的波动率有利于交易
            if 1.5 <= atr_percent <= 4.0:  # 适中波动率，适合期货交易
                atr_score = 0.9
            elif 1.0 <= atr_percent < 1.5:  # 低波动率，可能缺乏机会
                atr_score = 0.6
            elif atr_percent > 6.0:  # 高波动率，风险较大
                atr_score = 0.4
            elif 4.0 < atr_percent <= 6.0:  # 较高波动率
                atr_score = 0.7
            else:  # 其他情况
                atr_score = 0.5
            
            details['atr_score'] = atr_score
            score += atr_score * 0.2
            
            # 交易量指标评分 (权重: 0.15)
            volume_data = indicators.get('volume', {})
            volume_ratio = volume_data.get('volume_ratio', 1.0)
            volume_trend = volume_data.get('volume_trend', 'normal')
            
            # 期货考虑：交易量对趋势的确认
            if volume_trend == 'high' and volume_ratio > 1.5:
                volume_score = 0.9  # 高交易量确认趋势
            elif volume_trend == 'normal' and 0.8 <= volume_ratio <= 1.2:
                volume_score = 0.7  # 正常交易量
            elif volume_trend == 'low' and volume_ratio < 0.5:
                volume_score = 0.3  # 低交易量，趋势不可靠
            else:
                volume_score = 0.5  # 其他情况
            details['volume_score'] = volume_score
            score += volume_score * 0.15
            
            # 价格波动指标评分 (权重: 0.1)
            price_volatility_data = indicators.get('price_volatility', {})
            volatility = price_volatility_data.get('volatility', 2.0)
            volatility_level = price_volatility_data.get('volatility_level', 'medium')
            
            # 期货考虑：适中的波动率有利于交易
            if volatility_level == 'medium' and 1.5 <= volatility <= 4.0:
                volatility_score = 0.8  # 适中波动率
            elif volatility_level == 'low' and volatility < 1.5:
                volatility_score = 0.6  # 低波动率，机会较少
            elif volatility_level == 'high' and volatility > 6.0:
                volatility_score = 0.4  # 高波动率，风险较大
            else:
                volatility_score = 0.5  # 其他情况
            details['volatility_score'] = volatility_score
            score += volatility_score * 0.1
            
            return {
                'indicator_score': round(score, 3),
                'indicator_level': 'excellent' if score > 0.8 else 'good' if score > 0.7 else 'fair' if score > 0.6 else 'poor' if score > 0.4 else 'very_poor',
                'details': details
            }
            
        except Exception as e:
            logger.error(f"计算指标评分失败: {e}")
            return {'indicator_score': 0.5, 'indicator_level': 'fair', 'details': {}}
    
    def calculate_sentiment_score(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算期货市场情绪评分（考虑多空头情绪）
        
        Args:
            indicators: 技术指标字典
            
        Returns:
            市场情绪评分结果
        """
        try:
            score = 0.0
            details = {}
            
            # RSI情绪评分 (权重: 0.3) - 期货考虑：极端情绪反转
            rsi = indicators.get('rsi', {})
            rsi_value = rsi.get('rsi', 50)
            rsi_status = rsi.get('status', 'neutral')
            
            # 期货交易中，极端情绪可能是反转信号
            if rsi_value > 80:  # 极度超买，可能做空机会
                rsi_sentiment = 0.1
            elif rsi_value > 70:  # 超买，谨慎做多
                rsi_sentiment = 0.3
            elif rsi_value < 20:  # 极度超卖，可能做多机会
                rsi_sentiment = 0.9
            elif rsi_value < 30:  # 超卖，谨慎做空
                rsi_sentiment = 0.7
            elif 45 <= rsi_value <= 55:  # 中性区域，情绪稳定
                rsi_sentiment = 0.5
            else:  # 其他情况
                rsi_sentiment = 0.5
            details['rsi_sentiment'] = rsi_sentiment
            score += rsi_sentiment * 0.3
            
            # 布林带情绪评分 (权重: 0.25) - 期货考虑：边界突破情绪
            bb = indicators.get('bollinger_bands', {})
            bb_position = bb.get('position', 0.5)
            bb_squeeze = bb.get('squeeze', 'no')
            
            # 位置情绪 - 期货考虑：边界突破和回归
            if bb_position > 0.9:  # 接近上轨，可能做空机会
                bb_position_sentiment = 0.2
            elif bb_position > 0.7:  # 偏上轨，谨慎情绪
                bb_position_sentiment = 0.3
            elif bb_position < 0.1:  # 接近下轨，可能做多机会
                bb_position_sentiment = 0.8
            elif bb_position < 0.3:  # 偏下轨，谨慎情绪
                bb_position_sentiment = 0.7
            elif 0.4 <= bb_position <= 0.6:  # 中间区域，情绪稳定
                bb_position_sentiment = 0.5
            else:  # 其他情况
                bb_position_sentiment = 0.5
            
            # 挤压情绪 - 期货考虑：波动率收缩后的情绪紧张
            bb_squeeze_sentiment = 0.3 if bb_squeeze == 'yes' else 0.7  # 挤压时情绪紧张，可能有大行情
            
            bb_sentiment = (bb_position_sentiment + bb_squeeze_sentiment) / 2
            details['bollinger_bands_sentiment'] = bb_sentiment
            score += bb_sentiment * 0.25
            
            # MACD情绪评分 (权重: 0.25) - 期货考虑：趋势情绪
            macd = indicators.get('macd', {})
            macd_value = macd.get('macd', 0)
            signal_value = macd.get('signal', 0)
            histogram_value = macd.get('histogram', 0)
            
            # MACD趋势情绪 - 期货考虑：趋势强度和方向
            if macd_value > signal_value:
                macd_sentiment = 0.7  # 多头情绪
                if histogram_value > 0:  # 柱状图为正，多头情绪更强
                    macd_sentiment += 0.2
            else:
                macd_sentiment = 0.3  # 空头情绪
                if histogram_value < 0:  # 柱状图为负，空头情绪更强
                    macd_sentiment -= 0.2
            macd_sentiment = max(0.0, min(1.0, macd_sentiment))
            details['macd_sentiment'] = macd_sentiment
            score += macd_sentiment * 0.25
            
            # 价格动量情绪评分 (权重: 0.2) - 期货考虑：综合动量情绪
            current_price = indicators.get('support_resistance', {}).get('current_price', 0)
            if current_price > 0:
                # 基于RSI和布林带位置计算综合情绪
                rsi_value = rsi.get('rsi', 50)
                bb_position = bb.get('position', 0.5)
                
                # 期货综合情绪计算
                if rsi_value > 75 and bb_position > 0.8:  # 极度超买且接近上轨
                    momentum_sentiment = 0.1  # 极度乐观，可能反转
                elif rsi_value < 25 and bb_position < 0.2:  # 极度超卖且接近下轨
                    momentum_sentiment = 0.9  # 极度悲观，可能反转
                elif rsi_value > 70 and bb_position > 0.7:  # 超买且接近上轨
                    momentum_sentiment = 0.2  # 过度乐观
                elif rsi_value < 30 and bb_position < 0.3:  # 超卖且接近下轨
                    momentum_sentiment = 0.8  # 过度悲观
                elif rsi_value > 60 and bb_position > 0.6:  # 偏乐观
                    momentum_sentiment = 0.4  # 适度乐观
                elif rsi_value < 40 and bb_position < 0.4:  # 偏悲观
                    momentum_sentiment = 0.6  # 适度悲观
                else:  # 中性
                    momentum_sentiment = 0.5
            else:
                momentum_sentiment = 0.5  # 中性
            details['momentum_sentiment'] = momentum_sentiment
            score += momentum_sentiment * 0.15
            
            # 交易量情绪评分 (权重: 0.05)
            volume_data = indicators.get('volume', {})
            volume_ratio = volume_data.get('volume_ratio', 1.0)
            volume_trend = volume_data.get('volume_trend', 'normal')
            
            # 期货考虑：交易量反映市场情绪
            if volume_trend == 'high' and volume_ratio > 2.0:
                volume_sentiment = 0.3  # 极高交易量，可能情绪过度
            elif volume_trend == 'high' and volume_ratio > 1.5:
                volume_sentiment = 0.6  # 高交易量，情绪活跃
            elif volume_trend == 'normal':
                volume_sentiment = 0.5  # 正常交易量，情绪稳定
            elif volume_trend == 'low' and volume_ratio < 0.5:
                volume_sentiment = 0.4  # 低交易量，情绪低迷
            else:
                volume_sentiment = 0.5  # 其他情况
            details['volume_sentiment'] = volume_sentiment
            score += volume_sentiment * 0.05
            
            # 确定情绪方向和强度
            if score > 0.8:
                sentiment_level = 'very_bullish'
                sentiment_direction = 'long'
            elif score > 0.6:
                sentiment_level = 'bullish'
                sentiment_direction = 'long'
            elif score > 0.4:
                sentiment_level = 'neutral'
                sentiment_direction = 'neutral'
            elif score > 0.2:
                sentiment_level = 'bearish'
                sentiment_direction = 'short'
            else:
                sentiment_level = 'very_bearish'
                sentiment_direction = 'short'
            
            return {
                'sentiment_score': round(score, 3),
                'sentiment_level': sentiment_level,
                'sentiment_direction': sentiment_direction,  # 新增：明确多空方向
                'details': details
            }
            
        except Exception as e:
            logger.error(f"计算市场情绪评分失败: {e}")
            return {'sentiment_score': 0.5, 'sentiment_level': 'neutral', 'sentiment_direction': 'neutral', 'details': {}}
    
    def analyze_market_condition(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析市场状况
        
        Args:
            indicators: 技术指标字典
            
        Returns:
            市场分析结果
        """
        try:
            analysis = {
                'market_condition': 'unknown',
                'trend': 'unknown',
                'volatility': 'unknown',
                'recommendation': 'unknown',
                'confidence': 0.0
            }
            
            # 分析趋势
            macd_trend = indicators.get('macd', {}).get('trend', 'unknown')
            adx_trend = indicators.get('adx', {}).get('trend_direction', 'unknown')
            adx_strength = indicators.get('adx', {}).get('trend_strength', 'weak')
            
            # 分析波动率
            atr_percent = indicators.get('atr', {}).get('atr_percent', 0)
            bb_squeeze = indicators.get('bollinger_bands', {}).get('squeeze', 'no')
            
            # 分析RSI
            rsi = indicators.get('rsi', {}).get('rsi', 50)
            rsi_status = indicators.get('rsi', {}).get('status', 'neutral')
            
            # 确定市场状况
            if adx_strength == 'strong':
                if macd_trend == 'bullish' and adx_trend == 'bullish':
                    analysis['market_condition'] = 'strong_uptrend'
                    analysis['trend'] = 'bullish'
                    analysis['recommendation'] = 'buy'
                    analysis['confidence'] = 0.8
                elif macd_trend == 'bearish' and adx_trend == 'bearish':
                    analysis['market_condition'] = 'strong_downtrend'
                    analysis['trend'] = 'bearish'
                    analysis['recommendation'] = 'sell'
                    analysis['confidence'] = 0.8
            else:
                if bb_squeeze == 'yes':
                    analysis['market_condition'] = 'consolidation'
                    analysis['trend'] = 'sideways'
                    analysis['recommendation'] = 'wait'
                    analysis['confidence'] = 0.6
                else:
                    analysis['market_condition'] = 'weak_trend'
                    analysis['trend'] = 'mixed'
                    analysis['recommendation'] = 'wait'
                    analysis['confidence'] = 0.4
            
            # 分析波动率
            if atr_percent > 5:
                analysis['volatility'] = 'high'
            elif atr_percent > 2:
                analysis['volatility'] = 'medium'
            else:
                analysis['volatility'] = 'low'
            
            # RSI过滤
            if rsi_status == 'overbought' and analysis['recommendation'] == 'buy':
                analysis['recommendation'] = 'wait'
                analysis['confidence'] *= 0.7
            elif rsi_status == 'oversold' and analysis['recommendation'] == 'sell':
                analysis['recommendation'] = 'wait'
                analysis['confidence'] *= 0.7
            
            return analysis
            
        except Exception as e:
            logger.error(f"分析市场状况失败: {e}")
            return {
                'market_condition': 'unknown',
                'trend': 'unknown',
                'volatility': 'unknown',
                'recommendation': 'unknown',
                'confidence': 0.0
            }
    
    def query_deepseek_api(self, prompt: str) -> Optional[str]:
        """
        查询DeepSeek API
        
        Args:
            prompt: 查询提示
            
        Returns:
            API响应内容
        """
        # 检查是否有有效的API密钥
        if self.api_key == "dummy_key":
            logger.info("DeepSeek API密钥未配置，跳过API调用")
            return None
            
        try:
            url = f"{self.base_url}/v1/chat/completions"
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的加密货币技术分析师。请分析ETHUSDT的技术指标，并返回JSON格式的分析结果。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 2000
            }
            
            # 使用更长的超时时间和连接超时
            timeout_config = (10, 60)  # (连接超时, 读取超时)
            
            # 记录请求参数
            logger.info(f"🔍 DeepSeek API请求:")
            logger.info(f"  URL: {url}")
            logger.info(f"  模型: {payload['model']}")
            logger.info(f"  温度: {payload['temperature']}")
            logger.info(f"  最大令牌: {payload['max_tokens']}")
            logger.info(f"  系统提示: {payload['messages'][0]['content'][:100]}...")
            logger.info(f"  用户提示: {payload['messages'][1]['content'][:200]}...")
            
            response = self.session.post(url, json=payload, timeout=timeout_config)
            response.raise_for_status()
            
            result = response.json()
            
            # 记录响应数据
            logger.info(f"✅ DeepSeek API响应:")
            logger.info(f"  状态码: {response.status_code}")
            logger.info(f"  响应时间: {response.elapsed.total_seconds():.2f}秒")
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                logger.info(f"  响应内容长度: {len(content)} 字符")
                logger.info(f"  响应内容预览: {content[:300]}...")
                if len(content) > 300:
                    logger.info(f"  完整响应内容: {content}")
            else:
                logger.warning(f"  响应格式异常: {result}")
            
            return result['choices'][0]['message']['content']
            
        except requests.exceptions.Timeout as e:
            logger.error(f"⏰ DeepSeek API超时: {e}")
            logger.info("  💡 建议: 检查网络连接或稍后重试")
            logger.info(f"  📊 超时配置: 连接={timeout_config[0]}秒, 读取={timeout_config[1]}秒")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"🌐 DeepSeek API连接错误: {e}")
            logger.info("  💡 建议: 检查网络连接或API服务状态")
            logger.info(f"  🔗 目标URL: {url}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"❌ DeepSeek API HTTP错误: {e}")
            if hasattr(e.response, 'status_code'):
                logger.error(f"  HTTP状态码: {e.response.status_code}")
                logger.error(f"  响应头: {dict(e.response.headers)}")
                try:
                    error_detail = e.response.json()
                    logger.error(f"  错误详情: {error_detail}")
                except:
                    logger.error(f"  响应内容: {e.response.text[:500]}...")
                
                if e.response.status_code == 401:
                    logger.error("  💡 建议: API密钥可能无效或已过期")
                elif e.response.status_code == 429:
                    logger.error("  💡 建议: API调用频率过高，请稍后重试")
                elif e.response.status_code >= 500:
                    logger.error("  💡 建议: 服务器内部错误，请稍后重试")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"📄 DeepSeek API响应JSON解析失败: {e}")
            logger.error(f"  📍 错误位置: 行{e.lineno}, 列{e.colno}")
            logger.error(f"  📝 原始响应: {response.text[:500]}...")
            return None
        except Exception as e:
            logger.error(f"❓ DeepSeek API查询失败: {e}")
            logger.error(f"  🔍 异常类型: {type(e).__name__}")
            import traceback
            logger.error(f"  📋 详细堆栈: {traceback.format_exc()}")
            return None
    
    def get_real_time_analysis(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        获取实时分析结果
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            完整的分析结果
        """
        try:
            # 检查缓存
            current_time = time.time()
            if (not force_refresh and 
                self.last_analysis and 
                current_time - self.last_analysis_time < self.cache_duration):
                return self.last_analysis
            
            # 获取数据
            df = self.get_ethusdt_data()
            if df is None:
                return {'error': '无法获取市场数据'}
            
            # 计算技术指标
            indicators = self.calculate_technical_indicators(df)
            if not indicators:
                return {'error': '无法计算技术指标'}
            
            # 分析市场状况
            market_analysis = self.analyze_market_condition(indicators)
            
            # 计算各种评分
            trend_score = self.calculate_trend_score(indicators)
            indicator_score = self.calculate_indicator_score(indicators)
            sentiment_score = self.calculate_sentiment_score(indicators)
            
            # 构建分析结果
            analysis_result = {
                'timestamp': datetime.now().isoformat(),
                'symbol': 'ETHUSDT',
                'current_price': indicators.get('support_resistance', {}).get('current_price', 0.0),
                'indicators': indicators,
                'market_analysis': market_analysis,
                'scores': {
                    'trend_score': trend_score,
                    'indicator_score': indicator_score,
                    'sentiment_score': sentiment_score,
                    'overall_score': round((trend_score['trend_score'] + indicator_score['indicator_score'] + sentiment_score['sentiment_score']) / 3, 3)
                },
                'summary': {
                    'trend': market_analysis['trend'],
                    'condition': market_analysis['market_condition'],
                    'recommendation': market_analysis['recommendation'],
                    'confidence': market_analysis['confidence'],
                    'trend_level': trend_score['trend_level'],
                    'trend_direction': trend_score.get('trend_direction', 'neutral'),  # 新增：趋势方向
                    'indicator_level': indicator_score['indicator_level'],
                    'sentiment_level': sentiment_score['sentiment_level'],
                    'sentiment_direction': sentiment_score.get('sentiment_direction', 'neutral')  # 新增：情绪方向
                }
            }
            
            # 使用DeepSeek API进行深度分析
            deepseek_analysis = self.get_deepseek_analysis(indicators, market_analysis, trend_score, indicator_score, sentiment_score)
            if deepseek_analysis:
                analysis_result['deepseek_analysis'] = deepseek_analysis
            
            # 更新缓存
            self.last_analysis = analysis_result
            self.last_analysis_time = current_time
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"获取实时分析失败: {e}")
            return {'error': f'分析失败: {str(e)}'}
    
    def get_deepseek_analysis(self, indicators: Dict[str, Any], market_analysis: Dict[str, Any], 
                             trend_score: Dict[str, Any], indicator_score: Dict[str, Any], 
                             sentiment_score: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        使用DeepSeek API进行深度分析
        
        Args:
            indicators: 技术指标
            market_analysis: 市场分析
            trend_score: 趋势评分
            indicator_score: 指标评分
            sentiment_score: 情绪评分
            
        Returns:
            DeepSeek分析结果
        """
        try:
            # 构建提示词
            prompt = f"""
请分析以下ETHUSDT的技术指标数据，并返回JSON格式的分析结果：

技术指标：
- MACD: {indicators.get('macd', {})}
- ADX: {indicators.get('adx', {})}
- ATR: {indicators.get('atr', {})}
- 布林带: {indicators.get('bollinger_bands', {})}
- RSI: {indicators.get('rsi', {})}
- 支撑阻力位: {indicators.get('support_resistance', {})}

市场分析：
- 市场状况: {market_analysis.get('market_condition', 'unknown')}
- 趋势: {market_analysis.get('trend', 'unknown')}
- 波动率: {market_analysis.get('volatility', 'unknown')}
- 建议: {market_analysis.get('recommendation', 'unknown')}

评分系统：
- 趋势评分: {trend_score.get('trend_score', 0)} ({trend_score.get('trend_level', 'neutral')})
- 指标评分: {indicator_score.get('indicator_score', 0)} ({indicator_score.get('indicator_level', 'fair')})
- 情绪评分: {sentiment_score.get('sentiment_score', 0)} ({sentiment_score.get('sentiment_level', 'neutral')})

请返回JSON格式的分析结果，包括：
1. 趋势分析（上涨/下跌/震荡）
2. 关键支撑位和阻力位
3. 风险提示
4. 操作建议
5. 置信度评分
6. 综合评分分析

请确保返回的是有效的JSON格式。
"""
            
            response = self.query_deepseek_api(prompt)
            if not response:
                return None
            
            # 尝试解析JSON响应
            try:
                # 查找JSON内容
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response[start_idx:end_idx]
                    return json.loads(json_str)
                else:
                    # 如果没有找到JSON，返回文本分析
                    return {
                        'analysis_text': response,
                        'format': 'text'
                    }
                    
            except json.JSONDecodeError:
                # 如果JSON解析失败，返回文本分析
                return {
                    'analysis_text': response,
                    'format': 'text'
                }
                
        except Exception as e:
            logger.error(f"DeepSeek深度分析失败: {e}")
            return None
    
    def get_analysis_json(self, force_refresh: bool = False) -> str:
        """
        获取JSON格式的分析结果
        
        Args:
            force_refresh: 是否强制刷新
            
        Returns:
            JSON字符串
        """
        try:
            analysis = self.get_real_time_analysis(force_refresh)
            return json.dumps(analysis, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"生成JSON失败: {e}")
            return json.dumps({'error': f'生成JSON失败: {str(e)}'}, indent=2, ensure_ascii=False)

# 使用示例
if __name__ == "__main__":
    # API密钥将从环境变量或.env文件中自动读取
    analyzer = DeepSeekAnalyzer()
    
    # 获取实时分析
    result = analyzer.get_real_time_analysis()
    print(json.dumps(result, indent=2, ensure_ascii=False)) 