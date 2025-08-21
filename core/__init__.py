"""
量化交易系统核心模块

包含策略实现、数据加载、特征工程、回测引擎和交易所API等核心功能。
"""

# 导入核心模块
from .strategy import SharpeOptimizedStrategy, SignalFilter
from .data_loader import DataLoader
from .feature_engineer import FeatureEngineer
from .backtester import Backtester
from .exchange_api import RealExchangeAPI

# 导出主要类
__all__ = [
    'SharpeOptimizedStrategy',
    'SignalFilter',
    'DataLoader',
    'FeatureEngineer',
    'Backtester',
    'RealExchangeAPI'
]

# 版本信息
__version__ = '1.0.0'
__author__ = 'xniu.io'
__description__ = '量化交易系统核心模块' 