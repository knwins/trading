#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek信号整合器

功能：
1. 将DeepSeek API分析的实时技术指标整合到交易策略中
2. 提供综合评分系统，结合传统技术指标和AI分析
3. 支持期货交易的多空方向判断
4. 提供可配置的权重系统
"""

import logging
from typing import Dict, Any, Optional
from .deepseek_analyzer import DeepSeekAnalyzer

logger = logging.getLogger(__name__)

class DeepSeekSignalIntegrator:
    """
    DeepSeek信号整合器
    将AI分析结果整合到传统交易策略中
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化DeepSeek信号整合器
        
        Args:
            config: 配置字典，包含权重和参数设置
        """
        self.config = config or {}
        
        # 初始化DeepSeek分析器
        try:
            self.deepseek_analyzer = DeepSeekAnalyzer()
            self.enabled = True
            logger.info("✅ DeepSeek信号整合器初始化成功")
        except Exception as e:
            logger.warning(f"⚠️ DeepSeek分析器初始化失败: {e}")
            self.deepseek_analyzer = None
            self.enabled = False
        
        # 权重配置
        self.weights = self.config.get('deepseek_weights', {
            'trend_score_weight': 0.25,      # 趋势评分权重
            'indicator_score_weight': 0.25,   # 指标评分权重
            'sentiment_score_weight': 0.15,   # 市场情绪权重
            'overall_score_weight': 0.35      # 综合评分权重
        })
        
        # 信号阈值配置
        self.thresholds = self.config.get('deepseek_thresholds', {
            'strong_bullish': 0.7,   # 强看涨阈值
            'bullish': 0.6,          # 看涨阈值
            'neutral': 0.5,          # 中性阈值
            'bearish': 0.4,          # 看跌阈值
            'strong_bearish': 0.3    # 强看跌阈值
        })
        
        # 缓存管理 - 从配置文件读取
        self.cache_timeout = self.config.get('cache_timeout', 3600)  # 默认1小时缓存
        self.last_analysis = None
        self.last_analysis_time = 0
    
    def get_deepseek_analysis(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        获取DeepSeek分析结果
        
        Args:
            force_refresh: 是否强制刷新缓存
            
        Returns:
            DeepSeek分析结果字典，包含各项指标和评分
        """
        if not self.enabled:
            return None
        
        try:
            # 获取分析结果
            analysis = self.deepseek_analyzer.get_real_time_analysis(force_refresh)
            
            if analysis and 'indicators' in analysis:
                logger.debug("✅ 成功获取DeepSeek分析结果")
                return analysis
            else:
                logger.warning("⚠️ DeepSeek分析结果为空或格式错误")
                return None
                
        except Exception as e:
            logger.error(f"❌ 获取DeepSeek分析失败: {e}")
            return None
    
    def calculate_deepseek_signal_score(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算DeepSeek信号评分
        
        Args:
            analysis: DeepSeek分析结果
            
        Returns:
            包含信号评分和详细信息的字典
        """
        try:
            scores = analysis.get('scores', {})
            
            # 提取各项评分
            trend_score = scores.get('trend_score', {}).get('trend_score', 0.5)
            indicator_score = scores.get('indicator_score', {}).get('indicator_score', 0.5)
            sentiment_score = scores.get('sentiment_score', {}).get('sentiment_score', 0.5)
            overall_score = scores.get('overall_score', 0.5)
            
            # 计算加权综合评分
            weighted_score = (
                trend_score * self.weights['trend_score_weight'] +
                indicator_score * self.weights['indicator_score_weight'] +
                sentiment_score * self.weights['sentiment_score_weight'] +
                overall_score * self.weights['overall_score_weight']
            )
            
            # 获取趋势方向
            trend_direction = scores.get('trend_score', {}).get('trend_direction', 'neutral')
            sentiment_direction = scores.get('sentiment_score', {}).get('sentiment_direction', 'neutral')
            
            # 确定信号方向
            signal_direction = self._determine_signal_direction(
                weighted_score, trend_direction, sentiment_direction
            )
            
            # 确定信号强度
            signal_strength = self._determine_signal_strength(weighted_score)
            
            # 获取市场分析
            market_analysis = analysis.get('market_analysis', {})
            recommendation = market_analysis.get('recommendation', 'wait')
            confidence = market_analysis.get('confidence', 0.5)
            
            return {
                'deepseek_score': weighted_score,
                'signal_direction': signal_direction,
                'signal_strength': signal_strength,
                'trend_score': trend_score,
                'indicator_score': indicator_score,
                'sentiment_score': sentiment_score,
                'overall_score': overall_score,
                'trend_direction': trend_direction,
                'sentiment_direction': sentiment_direction,
                'recommendation': recommendation,
                'confidence': confidence,
                'weights_used': self.weights,
                'market_condition': market_analysis.get('market_condition', 'unknown'),
                'volatility': market_analysis.get('volatility', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"❌ 计算DeepSeek信号评分失败: {e}")
            return {
                'deepseek_score': 0.5,
                'signal_direction': 0,
                'signal_strength': 'unknown',
                'error': str(e)
            }
    
    def _determine_signal_direction(self, score: float, trend_direction: str, sentiment_direction: str) -> int:
        """
        确定信号方向
        
        Args:
            score: 综合评分
            trend_direction: 趋势方向 ('long', 'short', 'neutral')
            sentiment_direction: 情绪方向 ('long', 'short', 'neutral')
            
        Returns:
            信号方向 (1=多头, -1=空头, 0=观望)
        """
        try:
            # 基于评分的基础判断
            if score >= self.thresholds['strong_bullish']:
                base_signal = 1
            elif score >= self.thresholds['bullish']:
                base_signal = 1 if score > 0.55 else 0
            elif score <= self.thresholds['strong_bearish']:
                base_signal = -1
            elif score <= self.thresholds['bearish']:
                base_signal = -1 if score < 0.45 else 0
            else:
                base_signal = 0
            
            # 趋势和情绪一致性检查
            direction_consensus = 0
            
            if trend_direction == 'long' and sentiment_direction == 'long':
                direction_consensus = 1
            elif trend_direction == 'short' and sentiment_direction == 'short':
                direction_consensus = -1
            elif trend_direction == 'long' or sentiment_direction == 'long':
                direction_consensus = 0.5
            elif trend_direction == 'short' or sentiment_direction == 'short':
                direction_consensus = -0.5
            
            # 综合判断
            if base_signal == 1 and direction_consensus >= 0:
                return 1
            elif base_signal == -1 and direction_consensus <= 0:
                return -1
            elif abs(direction_consensus) >= 1 and score > 0.6:
                return int(direction_consensus)
            else:
                return 0
                
        except Exception as e:
            logger.error(f"❌ 确定信号方向失败: {e}")
            return 0
    
    def _determine_signal_strength(self, score: float) -> str:
        """
        确定信号强度
        
        Args:
            score: 综合评分
            
        Returns:
            信号强度 ('very_strong', 'strong', 'medium', 'weak', 'very_weak')
        """
        if score >= 0.8:
            return 'very_strong'
        elif score >= 0.7:
            return 'strong'
        elif score >= 0.6:
            return 'medium'
        elif score >= 0.4:
            return 'weak'
        else:
            return 'very_weak'
    
    def integrate_with_traditional_signal(self, traditional_signal: Dict[str, Any], 
                                        deepseek_weight: float = 0.3) -> Dict[str, Any]:
        """
        将DeepSeek分析结果与传统信号整合
        
        Args:
            traditional_signal: 传统策略生成的信号
            deepseek_weight: DeepSeek信号的权重 (0-1)
            
        Returns:
            整合后的信号字典
        """
        try:
            # 获取DeepSeek分析
            deepseek_analysis = self.get_deepseek_analysis()
            
            if not deepseek_analysis:
                logger.warning("⚠️ 无法获取DeepSeek分析，使用传统信号")
                traditional_signal['deepseek_status'] = 'unavailable'
                return traditional_signal
            
            # 计算DeepSeek信号评分
            deepseek_signal = self.calculate_deepseek_signal_score(deepseek_analysis)
            
            # 提取传统信号信息
            traditional_score = traditional_signal.get('signal_score', 0)
            traditional_direction = traditional_signal.get('signal', 0)
            
            # 提取DeepSeek信号信息
            deepseek_score = deepseek_signal.get('deepseek_score', 0.5)
            deepseek_direction = deepseek_signal.get('signal_direction', 0)
            
            # 权重设置
            traditional_weight = 1 - deepseek_weight
            
            # 计算综合评分
            if traditional_direction == 0:
                # 传统信号为观望时，主要参考DeepSeek信号
                integrated_score = deepseek_score
                integrated_direction = deepseek_direction
            elif deepseek_direction == 0:
                # DeepSeek信号为观望时，主要参考传统信号
                integrated_score = abs(traditional_score)
                integrated_direction = traditional_direction
            else:
                # 两个信号都有方向时，进行加权整合
                # 评分整合
                traditional_score_normalized = (abs(traditional_score) + 1) / 2  # 归一化到0-1
                integrated_score = (traditional_score_normalized * traditional_weight + 
                                  deepseek_score * deepseek_weight)
                
                # 方向整合
                if traditional_direction == deepseek_direction:
                    # 方向一致，加强信号
                    integrated_direction = traditional_direction
                    integrated_score = min(1.0, integrated_score * 1.1)  # 轻微加强
                else:
                    # 方向冲突，降低信号强度
                    if deepseek_weight > 0.5:
                        integrated_direction = deepseek_direction
                    else:
                        integrated_direction = traditional_direction
                    integrated_score = integrated_score * 0.8  # 降低强度
            
            # 构建整合后的信号
            integrated_signal = traditional_signal.copy()
            integrated_signal.update({
                'signal': integrated_direction,
                'signal_score': integrated_score * integrated_direction if integrated_direction != 0 else 0,
                'integrated_score': integrated_score,
                'original_signal': traditional_direction,
                'original_score': traditional_score,
                'deepseek_signal': deepseek_direction,
                'deepseek_score': deepseek_score,
                'deepseek_weight': deepseek_weight,
                'traditional_weight': traditional_weight,
                'deepseek_analysis': deepseek_signal,
                'deepseek_status': 'integrated',
                'integration_method': 'weighted_average'
            })
            
            logger.debug(f"✅ 信号整合完成: 传统={traditional_direction}({traditional_score:.3f}), "
                        f"DeepSeek={deepseek_direction}({deepseek_score:.3f}), "
                        f"整合={integrated_direction}({integrated_score:.3f})")
            
            return integrated_signal
            
        except Exception as e:
            logger.error(f"❌ 信号整合失败: {e}")
            traditional_signal['deepseek_status'] = 'error'
            traditional_signal['deepseek_error'] = str(e)
            return traditional_signal
    
    def get_deepseek_indicators(self) -> Optional[Dict[str, Any]]:
        """
        获取DeepSeek技术指标数据
        
        Returns:
            技术指标字典
        """
        try:
            analysis = self.get_deepseek_analysis()
            if analysis:
                return analysis.get('indicators', {})
            return None
        except Exception as e:
            logger.error(f"❌ 获取DeepSeek指标失败: {e}")
            return None
    
    def get_market_analysis(self) -> Optional[Dict[str, Any]]:
        """
        获取市场分析结果
        
        Returns:
            市场分析字典
        """
        try:
            analysis = self.get_deepseek_analysis()
            if analysis:
                return analysis.get('market_analysis', {})
            return None
        except Exception as e:
            logger.error(f"❌ 获取市场分析失败: {e}")
            return None
    
    def is_enabled(self) -> bool:
        """
        检查DeepSeek整合器是否可用
        
        Returns:
            是否可用
        """
        return self.enabled and self.deepseek_analyzer is not None
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取整合器状态信息
        
        Returns:
            状态信息字典
        """
        return {
            'enabled': self.enabled,
            'analyzer_available': self.deepseek_analyzer is not None,
            'weights': self.weights,
            'thresholds': self.thresholds,
            'cache_timeout': self.cache_timeout
        }