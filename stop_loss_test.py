import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Tuple, Any
import json

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StopLossStrategy:
    """止损策略基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.stats = {
            'total_trades': 0,
            'stop_loss_trades': 0,
            'total_loss': 0.0,
            'avg_loss': 0.0,
            'max_loss': 0.0,
            'loss_details': []
        }
    
    def should_stop_loss(self, position: int, entry_price: float, current_price: float, 
                        current_features: Dict = None, holding_periods: int = 0) -> Tuple[bool, str]:
        """检查是否应该止损"""
        raise NotImplementedError
    
    def update_stats(self, loss_ratio: float):
        """更新统计数据"""
        self.stats['total_trades'] += 1
        self.stats['stop_loss_trades'] += 1
        self.stats['total_loss'] += loss_ratio
        self.stats['avg_loss'] = self.stats['total_loss'] / self.stats['stop_loss_trades']
        self.stats['max_loss'] = max(self.stats['max_loss'], loss_ratio)
        self.stats['loss_details'].append(loss_ratio)


class OriginalStopLoss(StopLossStrategy):
    """原始止损策略"""
    
    def __init__(self):
        super().__init__("原始止损策略")
        self.fixed_stop_ratio = 0.08  # 8%
    
    def should_stop_loss(self, position: int, entry_price: float, current_price: float, 
                        current_features: Dict = None, holding_periods: int = 0) -> Tuple[bool, str]:
        # 计算当前亏损比例
        if position == 1:  # 多仓
            loss_ratio = (entry_price - current_price) / entry_price
        else:  # 空仓
            loss_ratio = (current_price - entry_price) / entry_price
        
        # 固定止损
        if loss_ratio >= self.fixed_stop_ratio:
            return True, f"固定止损(亏损{loss_ratio*100:.1f}% >= {self.fixed_stop_ratio*100:.1f}%)"
        
        # LineWMA反转止损（止损达到固定止损一半时执行）
        if current_features and loss_ratio >= self.fixed_stop_ratio * 0.5:
            line_wma = current_features.get('lineWMA', 0)
            if line_wma > 0:
                if position == 1 and current_price < line_wma:
                    return True, f"多头LineWMA反转止损(价格{current_price:.2f} < LineWMA{line_wma:.2f})"
                elif position == -1 and current_price > line_wma:
                    return True, f"空头LineWMA反转止损(价格{current_price:.2f} > LineWMA{line_wma:.2f})"
        
        return False, ""


class TrailingStopLoss(StopLossStrategy):
    """追踪止损策略"""
    
    def __init__(self):
        super().__init__("追踪止损策略")
        self.trailing_ratio = 0.03  # 3%追踪止损
        self.break_even_ratio = 0.02  # 2%盈利后保本
        self.max_loss_ratio = 0.06  # 最大止损6%
    
    def should_stop_loss(self, position: int, entry_price: float, current_price: float, 
                        current_features: Dict = None, holding_periods: int = 0) -> Tuple[bool, str]:
        # 计算当前盈亏比例
        if position == 1:  # 多仓
            pnl_ratio = (current_price - entry_price) / entry_price
        else:  # 空仓
            pnl_ratio = (entry_price - current_price) / entry_price
        
        # 最大止损
        if pnl_ratio <= -self.max_loss_ratio:
            return True, f"最大止损(亏损{pnl_ratio*100:.1f}% <= -{self.max_loss_ratio*100:.1f}%)"
        
        # 追踪止损（盈利后）
        if pnl_ratio > self.break_even_ratio:
            # 从最高点回撤超过追踪比例
            if current_features and 'highest_price' in current_features:
                highest_price = current_features['highest_price']
                if position == 1:  # 多仓
                    drawdown = (highest_price - current_price) / highest_price
                else:  # 空仓
                    drawdown = (current_price - highest_price) / highest_price
                
                if drawdown >= self.trailing_ratio:
                    return True, f"追踪止损(回撤{drawdown*100:.1f}% >= {self.trailing_ratio*100:.1f}%)"
        
        return False, ""


class AdaptiveStopLoss(StopLossStrategy):
    """自适应止损策略"""
    
    def __init__(self):
        super().__init__("自适应止损策略")
        self.base_stop_ratio = 0.05  # 基础止损5%
        self.atr_multiplier = 2.0  # ATR倍数
        self.volatility_threshold = 0.02  # 波动率阈值
    
    def should_stop_loss(self, position: int, entry_price: float, current_price: float, 
                        current_features: Dict = None, holding_periods: int = 0) -> Tuple[bool, str]:
        # 计算当前亏损比例
        if position == 1:  # 多仓
            loss_ratio = (entry_price - current_price) / entry_price
        else:  # 空仓
            loss_ratio = (current_price - entry_price) / entry_price
        
        # 获取ATR和波动率
        atr = current_features.get('atr', 0) if current_features else 0
        atr_pct = current_features.get('atr_pct', 0) if current_features else 0
        
        # 自适应止损
        if atr > 0:
            # 基于ATR的动态止损
            atr_stop_ratio = (atr * self.atr_multiplier) / entry_price
            dynamic_stop_ratio = min(self.base_stop_ratio, atr_stop_ratio)
        else:
            dynamic_stop_ratio = self.base_stop_ratio
        
        # 根据波动率调整
        if atr_pct > self.volatility_threshold:
            # 高波动率时放宽止损
            dynamic_stop_ratio *= 1.5
        
        if loss_ratio >= dynamic_stop_ratio:
            return True, f"自适应止损(亏损{loss_ratio*100:.1f}% >= {dynamic_stop_ratio*100:.1f}%, ATR={atr:.2f})"
        
        return False, ""


class TimeBasedStopLoss(StopLossStrategy):
    """时间止损策略"""
    
    def __init__(self):
        super().__init__("时间止损策略")
        self.max_holding_periods = 48  # 最大持仓48个周期
        self.time_decay_ratio = 0.001  # 时间衰减比例
    
    def should_stop_loss(self, position: int, entry_price: float, current_price: float, 
                        current_features: Dict = None, holding_periods: int = 0) -> Tuple[bool, str]:
        # 计算当前亏损比例
        if position == 1:  # 多仓
            loss_ratio = (entry_price - current_price) / entry_price
        else:  # 空仓
            loss_ratio = (current_price - entry_price) / entry_price
        
        # 时间止损
        if holding_periods >= self.max_holding_periods:
            return True, f"时间止损(持仓{holding_periods}周期 >= {self.max_holding_periods})"
        
        # 时间衰减止损
        time_decay_stop = holding_periods * self.time_decay_ratio
        if loss_ratio >= time_decay_stop:
            return True, f"时间衰减止损(亏损{loss_ratio*100:.1f}% >= {time_decay_stop*100:.1f}%)"
        
        return False, ""


class HybridStopLoss(StopLossStrategy):
    """混合止损策略"""
    
    def __init__(self):
        super().__init__("混合止损策略")
        self.fixed_stop_ratio = 0.08  # 固定止损8%
        self.trailing_ratio = 0.03  # 追踪止损3%
        self.atr_multiplier = 2.0  # ATR倍数
        self.max_holding_periods = 72  # 最大持仓72周期
    
    def should_stop_loss(self, position: int, entry_price: float, current_price: float, 
                        current_features: Dict = None, holding_periods: int = 0) -> Tuple[bool, str]:
        # 计算当前盈亏比例
        if position == 1:  # 多仓
            pnl_ratio = (current_price - entry_price) / entry_price
        else:  # 空仓
            pnl_ratio = (entry_price - current_price) / entry_price
        
        # 1. 固定止损（最高优先级）
        if pnl_ratio <= -self.fixed_stop_ratio:
            return True, f"固定止损(亏损{pnl_ratio*100:.1f}% <= -{self.fixed_stop_ratio*100:.1f}%)"
        
        # 2. 时间止损
        if holding_periods >= self.max_holding_periods:
            return True, f"时间止损(持仓{holding_periods}周期 >= {self.max_holding_periods})"
        
        # 3. 追踪止损（盈利后）
        if pnl_ratio > 0.02:  # 盈利超过2%后启用追踪止损
            if current_features and 'highest_price' in current_features:
                highest_price = current_features['highest_price']
                if position == 1:  # 多仓
                    drawdown = (highest_price - current_price) / highest_price
                else:  # 空仓
                    drawdown = (current_price - highest_price) / highest_price
                
                if drawdown >= self.trailing_ratio:
                    return True, f"追踪止损(回撤{drawdown*100:.1f}% >= {self.trailing_ratio*100:.1f}%)"
        
        # 4. ATR动态止损
        atr = current_features.get('atr', 0) if current_features else 0
        if atr > 0:
            atr_stop_ratio = (atr * self.atr_multiplier) / entry_price
            if pnl_ratio <= -atr_stop_ratio:
                return True, f"ATR动态止损(亏损{pnl_ratio*100:.1f}% <= -{atr_stop_ratio*100:.1f}%)"
        
        return False, ""


class StopLossBacktester:
    """止损策略回测器"""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.strategies = [
            OriginalStopLoss(),
            TrailingStopLoss(),
            AdaptiveStopLoss(),
            TimeBasedStopLoss(),
            HybridStopLoss()
        ]
    
    def run_backtest(self, signals: pd.Series) -> Dict[str, Any]:
        """运行回测"""
        results = {}
        
        for strategy in self.strategies:
            logger.info(f"正在回测 {strategy.name}...")
            strategy_results = self._backtest_strategy(strategy, signals)
            results[strategy.name] = strategy_results
        
        return results
    
    def _backtest_strategy(self, strategy: StopLossStrategy, signals: pd.Series) -> Dict[str, Any]:
        """回测单个策略"""
        position = 0
        entry_price = 0
        entry_time = None
        holding_periods = 0
        highest_price = 0
        lowest_price = float('inf')
        
        trades = []
        
        for i, (timestamp, row) in enumerate(self.data.iterrows()):
            current_price = row['close']
            signal = signals.iloc[i] if i < len(signals) else 0
            
            # 更新最高最低价
            if position != 0:
                if position == 1:  # 多仓
                    highest_price = max(highest_price, current_price)
                    lowest_price = min(lowest_price, current_price)
                else:  # 空仓
                    highest_price = max(highest_price, lowest_price)
                    lowest_price = min(lowest_price, current_price)
            
            # 开仓
            if position == 0 and signal != 0:
                position = signal
                entry_price = current_price
                entry_time = timestamp
                holding_periods = 0
                highest_price = current_price
                lowest_price = current_price
                continue
            
            # 持仓中
            if position != 0:
                holding_periods += 1
                
                # 构建特征数据
                current_features = {
                    'lineWMA': row.get('lineWMA', 0),
                    'atr': row.get('atr', 0),
                    'atr_pct': row.get('atr_pct', 0),
                    'highest_price': highest_price,
                    'lowest_price': lowest_price
                }
                
                # 检查止损
                should_stop, reason = strategy.should_stop_loss(
                    position, entry_price, current_price, current_features, holding_periods
                )
                
                if should_stop:
                    # 计算亏损
                    if position == 1:  # 多仓
                        loss_ratio = (entry_price - current_price) / entry_price
                    else:  # 空仓
                        loss_ratio = (current_price - entry_price) / entry_price
                    
                    # 记录交易
                    trade = {
                        'entry_time': entry_time,
                        'exit_time': timestamp,
                        'position': position,
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'holding_periods': holding_periods,
                        'loss_ratio': loss_ratio,
                        'reason': reason
                    }
                    trades.append(trade)
                    
                    # 更新统计
                    strategy.update_stats(loss_ratio)
                    
                    # 平仓
                    position = 0
                    entry_price = 0
                    entry_time = None
                    holding_periods = 0
        
        return {
            'trades': trades,
            'stats': strategy.stats,
            'total_trades': len(trades),
            'stop_loss_rate': len(trades) / max(1, strategy.stats['total_trades']),
            'avg_loss': strategy.stats['avg_loss'],
            'max_loss': strategy.stats['max_loss']
        }
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """生成回测报告"""
        report = "=" * 80 + "\n"
        report += "止损策略回测报告\n"
        report += "=" * 80 + "\n\n"
        
        # 汇总统计
        summary_data = []
        for strategy_name, result in results.items():
            summary_data.append({
                '策略名称': strategy_name,
                '总交易数': result['total_trades'],
                '止损交易数': result['stats']['stop_loss_trades'],
                '止损率': f"{result['stop_loss_rate']*100:.1f}%",
                '平均亏损': f"{result['avg_loss']*100:.2f}%",
                '最大亏损': f"{result['max_loss']*100:.2f}%",
                '总亏损': f"{result['stats']['total_loss']*100:.2f}%"
            })
        
        summary_df = pd.DataFrame(summary_data)
        report += summary_df.to_string(index=False) + "\n\n"
        
        # 详细分析
        report += "详细分析:\n"
        report += "-" * 40 + "\n"
        
        for strategy_name, result in results.items():
            report += f"\n{strategy_name}:\n"
            report += f"  总交易数: {result['total_trades']}\n"
            report += f"  止损率: {result['stop_loss_rate']*100:.1f}%\n"
            report += f"  平均亏损: {result['avg_loss']*100:.2f}%\n"
            report += f"  最大亏损: {result['max_loss']*100:.2f}%\n"
            
            # 止损原因分析
            if result['trades']:
                reasons = [trade['reason'] for trade in result['trades']]
                reason_counts = pd.Series(reasons).value_counts()
                report += f"  止损原因分布:\n"
                for reason, count in reason_counts.items():
                    report += f"    {reason}: {count}次\n"
        
        return report
    
    def plot_results(self, results: Dict[str, Any], save_path: str = None):
        """绘制回测结果图表"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # 1. 止损率对比
        strategies = list(results.keys())
        stop_loss_rates = [results[s]['stop_loss_rate'] * 100 for s in strategies]
        
        ax1.bar(strategies, stop_loss_rates, color='skyblue', alpha=0.7)
        ax1.set_title('止损率对比')
        ax1.set_ylabel('止损率 (%)')
        ax1.tick_params(axis='x', rotation=45)
        
        # 2. 平均亏损对比
        avg_losses = [results[s]['avg_loss'] * 100 for s in strategies]
        
        ax2.bar(strategies, avg_losses, color='lightcoral', alpha=0.7)
        ax2.set_title('平均亏损对比')
        ax2.set_ylabel('平均亏损 (%)')
        ax2.tick_params(axis='x', rotation=45)
        
        # 3. 最大亏损对比
        max_losses = [results[s]['max_loss'] * 100 for s in strategies]
        
        ax3.bar(strategies, max_losses, color='gold', alpha=0.7)
        ax3.set_title('最大亏损对比')
        ax3.set_ylabel('最大亏损 (%)')
        ax3.tick_params(axis='x', rotation=45)
        
        # 4. 总交易数对比
        total_trades = [results[s]['total_trades'] for s in strategies]
        
        ax4.bar(strategies, total_trades, color='lightgreen', alpha=0.7)
        ax4.set_title('总交易数对比')
        ax4.set_ylabel('交易数')
        ax4.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"图表已保存到: {save_path}")
        
        plt.show()


def main():
    """主函数"""
    # 加载数据
    try:
        df = pd.read_csv('signals_sharpe_results.csv', index_col=0, parse_dates=True)
        logger.info(f"成功加载数据: {len(df)} 条记录")
    except FileNotFoundError:
        logger.error("未找到 signals_sharpe_results.csv 文件，请先运行 signals_sharpe.py")
        return
    
    # 提取信号
    signals = df['signal'].fillna(0)
    logger.info(f"信号统计: 做多{sum(signals == 1)}个, 做空{sum(signals == -1)}个")
    
    # 创建回测器
    backtester = StopLossBacktester(df)
    
    # 运行回测
    logger.info("开始回测...")
    results = backtester.run_backtest(signals)
    
    # 生成报告
    report = backtester.generate_report(results)
    print(report)
    
    # 保存报告
    with open('stop_loss_backtest_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    logger.info("报告已保存到: stop_loss_backtest_report.txt")
    
    # 绘制图表
    backtester.plot_results(results, 'stop_loss_comparison.png')
    
    # 保存详细结果
    detailed_results = {}
    for strategy_name, result in results.items():
        detailed_results[strategy_name] = {
            'stats': result['stats'],
            'total_trades': result['total_trades'],
            'stop_loss_rate': result['stop_loss_rate'],
            'avg_loss': result['avg_loss'],
            'max_loss': result['max_loss'],
            'trades': result['trades'][:10]  # 只保存前10笔交易作为示例
        }
    
    with open('stop_loss_detailed_results.json', 'w', encoding='utf-8') as f:
        json.dump(detailed_results, f, ensure_ascii=False, indent=2, default=str)
    logger.info("详细结果已保存到: stop_loss_detailed_results.json")


if __name__ == '__main__':
    main() 