#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek ETHUSDT实时技术指标分析 - 快速演示

功能：
1. 获取ETHUSDT实时技术指标
2. 显示MACD、ADX、ATR、布林带、RSI等指标
3. 展示新增的交易量和价格波动指标
4. 显示支撑阻力位
5. 提供期货交易建议
"""


import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .deepseek_analyzer import DeepSeekAnalyzer
except ImportError:
    from deepseek_analyzer import DeepSeekAnalyzer
import json

def main():
    """主函数"""
    print("🚀 DeepSeek ETHUSDT实时技术指标分析演示")
    print("=" * 60)
    
    try:
        # 创建分析器
        analyzer = DeepSeekAnalyzer()
        print("📊 正在获取ETHUSDT实时分析...")
        
        # 获取分析结果
        result = analyzer.get_real_time_analysis()
        
        if result and 'indicators' in result:
            # 显示基本信息
            print(f"\n💰 当前价格: ${result.get('current_price', 0):,.2f}")
            
            # 显示技术指标
            indicators = result['indicators']
            
            print("\n📈 技术指标:")
            print("-" * 40)
            
            # MACD
            macd = indicators.get('macd', {})
            print(f"MACD: {macd.get('macd', 0):.2f}")
            print(f"信号线: {macd.get('signal', 0):.2f}")
            print(f"柱状图: {macd.get('histogram', 0):.2f}")
            print(f"趋势: {macd.get('trend', 'N/A')}")
            
            # ADX
            adx = indicators.get('adx', {})
            adx_value = adx.get('adx')
            if adx_value is not None:
                print(f"\nADX: {adx_value:.2f}")
                print(f"趋势强度: {adx.get('trend_strength', 'N/A')}")
                print(f"趋势方向: {adx.get('trend_direction', 'N/A')}")
                print(f"状态: {adx.get('status', 'N/A')}")
            else:
                print(f"\nADX: 数据不足")
                print(f"状态: {adx.get('status', 'N/A')}")
                print(f"需要至少28个数据点来计算ADX")
            
            # RSI
            rsi = indicators.get('rsi', {})
            print(f"\nRSI: {rsi.get('rsi', 0):.2f}")
            print(f"状态: {rsi.get('status', 'N/A')}")
            
            # 布林带
            bb = indicators.get('bollinger_bands', {})
            print(f"\n布林带:")
            print(f"  上轨: ${bb.get('upper', 0):,.2f}")
            print(f"  中轨: ${bb.get('middle', 0):,.2f}")
            print(f"  下轨: ${bb.get('lower', 0):,.2f}")
            print(f"  位置: {bb.get('position', 0):.2f}")
            print(f"  挤压: {bb.get('squeeze', 'N/A')}")
            
            # 新增：交易量指标
            volume = indicators.get('volume', {})
            if volume:
                print(f"\n📊 交易量指标:")
                print(f"  当前成交量: {volume.get('current_volume', 0):,.0f}")
                print(f"  平均成交量: {volume.get('avg_volume', 0):,.0f}")
                print(f"  成交量比率: {volume.get('volume_ratio', 0):.2f}")
                print(f"  成交量趋势: {volume.get('volume_trend', 'N/A')}")
            
            # 新增：价格波动指标
            volatility = indicators.get('price_volatility', {})
            if volatility:
                print(f"\n💹 价格波动指标:")
                print(f"  波动率: {volatility.get('volatility', 0):.2f}%")
                print(f"  波动等级: {volatility.get('volatility_level', 'N/A')}")
                print(f"  价格动量: {volatility.get('price_momentum', 0):.2f}%")
                print(f"  动量方向: {volatility.get('momentum_direction', 'N/A')}")
            
            # 支撑阻力位
            sr = indicators.get('support_resistance', {})
            print(f"\n🎯 支撑阻力位:")
            resistance = sr.get('resistance', [])
            support = sr.get('support', [])
            print(f"  阻力位: {[f'${price:,.2f}' for price in resistance]}")
            print(f"  支撑位: {[f'${price:,.2f}' for price in support]}")
            
            # 评分系统
            scores = result.get('scores', {})
            print(f"\n📊 评分系统:")
            print("-" * 40)
            
            trend_score = scores.get('trend_score', {})
            print(f"趋势评分: {trend_score.get('trend_score', 0):.3f} ({trend_score.get('trend_level', 'N/A')})")
            print(f"趋势方向: {trend_score.get('trend_direction', 'N/A')}")
            
            indicator_score = scores.get('indicator_score', {})
            print(f"指标评分: {indicator_score.get('indicator_score', 0):.3f} ({indicator_score.get('indicator_level', 'N/A')})")
            
            sentiment_score = scores.get('sentiment_score', {})
            print(f"情绪评分: {sentiment_score.get('sentiment_score', 0):.3f} ({sentiment_score.get('sentiment_level', 'N/A')})")
            print(f"情绪方向: {sentiment_score.get('sentiment_direction', 'N/A')}")
            
            overall_score = scores.get('overall_score', 0)
            print(f"综合评分: {overall_score:.3f}")
            
            # 市场分析
            market = result.get('market_analysis', {})
            print(f"\n📋 市场分析:")
            print("-" * 40)
            print(f"市场状况: {market.get('market_condition', 'N/A')}")
            print(f"趋势: {market.get('trend', 'N/A')}")
            print(f"波动率: {market.get('volatility', 'N/A')}")
            print(f"建议: {market.get('recommendation', 'N/A')}")
            print(f"置信度: {market.get('confidence', 0):.2f}")
            
            # 期货交易建议
            print(f"\n🎯 期货交易建议:")
            print("-" * 40)
            
            # 基于评分的建议
            if overall_score > 0.7:
                print("✅ 市场条件优秀，可考虑交易")
            elif overall_score > 0.5:
                print("⚠️  市场条件一般，谨慎操作")
            else:
                print("❌ 市场条件较差，建议观望")
            
            # 基于趋势方向的建议
            trend_direction = trend_score.get('trend_direction', 'neutral')
            sentiment_direction = sentiment_score.get('sentiment_direction', 'neutral')
            
            if trend_direction == sentiment_direction and trend_direction != 'neutral':
                print(f"✅ 趋势和情绪方向一致，建议{trend_direction}操作")
            elif trend_direction != 'neutral':
                print(f"⚠️  趋势方向为{trend_direction}，但情绪方向不一致，谨慎操作")
            else:
                print("⏸️  趋势方向不明确，建议观望")
            
            # 基于交易量的建议
            if volume:
                volume_trend = volume.get('volume_trend', 'normal')
                if volume_trend == 'high':
                    print("✅ 高成交量，趋势确认性强")
                elif volume_trend == 'low':
                    print("⚠️  低成交量，可能假突破，等待确认")
                else:
                    print("📊 正常成交量，可正常操作")
            
            # 基于波动率的建议
            if volatility:
                volatility_level = volatility.get('volatility_level', 'medium')
                if volatility_level == 'high':
                    print("⚠️  高波动率，风险较大，需严格止损")
                elif volatility_level == 'low':
                    print("📊 低波动率，可能积蓄能量，关注突破")
                else:
                    print("✅ 适中波动率，适合期货交易")
            
        else:
            print("❌ 无法获取市场数据")
            
    except Exception as e:
        print(f"❌ 分析失败: {e}")
    
    print("\n" + "=" * 60)
    print("✅ 演示完成！")
    print("=" * 60)

if __name__ == "__main__":
    main() 