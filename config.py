# -*- coding: utf-8 -*-
# ============================================================================
# 基础配置参数
# ============================================================================

# 交易对与时间级别配置
TRADING_CONFIG = {
    'SYMBOL': 'ETHUSDT',
    'TIMEFRAME': '1h',
    'TIMEFRAME_DAY': '1d',
    'TESTTIME': '2025-06-02 14:00:00',
    
    # 资金管理配置
    'CAPITAL_CONFIG': {
        'INITIAL_CAPITAL': 10000,        # 初始资金 (USDT)
        'POSITION_SIZE_PERCENT': 0.1,    # 每次开仓资金比例 (10%)
        'MAX_POSITION_SIZE': 0.5,        # 最大仓位比例 (50%)
        'MIN_POSITION_SIZE': 0.05,       # 最小仓位比例 (5%)
        'LEVERAGE': 10,                  # 杠杆倍数 (期货交易)
    },
    
    # 风险控制配置
    'RISK_CONFIG': {
        'MAX_DAILY_TRADES': 10,          # 每日最大交易次数
        'MIN_TRADE_INTERVAL': 300,       # 最小交易间隔(秒)
        'MAX_DAILY_LOSS': 0.05,          # 每日最大亏损比例 (5%)
        'MAX_TOTAL_LOSS': 0.20,          # 总资金最大亏损比例 (20%)
        'EMERGENCY_STOP_LOSS': 0.30,     # 紧急止损比例 (30%)
    },
}

# 策略窗口参数配置
WINDOW_CONFIG = {
    'SHORT_WINDOW': 200,  # 从30减少到10
    'LONG_WINDOW': 400,   # 从60减少到20
}

# 回测配置参数
BACKTEST_CONFIG = {
    'BACKTEST_DAYS': 60,
}

# ============================================================================
# 技术指标参数配置
# ============================================================================

# EMA指标参数配置
EMA_CONFIG = {
    'LINEEMA_PERIOD': 55,
    'OPENEMA_PERIOD': 25,
    'CLOSEEMA_PERIOD': 25,
    'EMA9_PERIOD': 9,
    'EMA20_PERIOD': 20,
    'EMA50_PERIOD': 50,
    'EMA104_PERIOD': 104,
}

# 技术指标参数配置
PERIOD_CONFIG = {
    'RSI_PERIOD': 14,
    'OBV_PERIOD': 20,    # OBV周期
    'ATR_PERIOD': 14,    # ATR周期   
}

# ============================================================================
# 日志和调试配置
# ============================================================================

# 日志配置
LOGGING_CONFIG = {
    'LEVEL': 'INFO',  # 改回INFO级别，减少日志输出
    'CONSOLE_OUTPUT': True,
    'FILE_OUTPUT': True,  # 启用文件输出
    'LOG_DIR': 'logs',  # 使用相对路径，在当前目录下创建logs文件夹
}

# 调试配置
DEBUG_CONFIG = {
    'SHOW_API_URLS': False,  # 关闭API URL显示
    'ENABLE_VERBOSE_OUTPUT': False,
    'ENABLE_SIGNAL_LOGGING': True,
    'ENABLE_PERFORMANCE_STATS': True,
    'LOG_LEVEL': LOGGING_CONFIG['LEVEL'],  # 统一日志级别
}

# ============================================================================
# 交易所API配置
# ============================================================================

# Binance API配置
BINANCE_API_CONFIG = {
    # 主网配置
    'MAINNET': {
        'BASE_URL': 'https://fapi.binance.com',
        'API_VERSION': 'v1',  # 修复：Binance合约API使用v1版本
        'FUTURES_API_VERSION': 'v1',  # 修复：Binance合约API使用v1版本
        'TIMEOUT': 10,
        'RECV_WINDOW': 10000,
    },
    
    # 现货API配置
    'SPOT': {
        'BASE_URL': 'https://api.binance.com',
        'API_VERSION': 'v3',
        'TIMEOUT': 10,
        'RECV_WINDOW': 10000,
    },
    
    # 通用配置
    'COMMON': {
        'DEFAULT_LEVERAGE': 10,
        'DEFAULT_MARGIN_TYPE': 'ISOLATED',
        'MAX_LEVERAGE': 125,
        'MIN_ORDER_SIZE': 0.001,
    }
}

# ============================================================================
# 策略配置
# ============================================================================

# SharpeOptimizedStrategy 配置
OPTIMIZED_STRATEGY_CONFIG = {
    # 基础窗口配置
    'windows': {
        'short': WINDOW_CONFIG['SHORT_WINDOW'],
        'long': WINDOW_CONFIG['LONG_WINDOW']
    },
    
    # 信号方向配置
    'signal_direction': {
        'long': 0.01,      # 多头，综合信号需要>0.3
        'short':-0.01,    # 空头，综合信号需要<-0.25
        'neutral': 0    # 中性信号
    },
    
    # 评分权重配置
    'score_weights': {
        'signal_weight': 0.6,     # 指标评分权重 30%
        'trend_weight': 0.4,      # 趋势强度评分权重 40%
        'risk_weight': 0.00,       # 风险评分权重 20%
        'drawdown_weight': 0.00    # 回撤评分权重 10%
    },
    
   
 
    # 信号过滤器配置
    'signal_filters': {
        # 核心过滤器开关 - 保留必要的过滤器
        
        # 过滤参数 - 调整阈值以产生被过滤信号
        'enable_price_deviation_filter': True, # 价格偏离过滤器（关闭）
        'price_deviation_threshold': 3.0,       # 价格偏离阈值3%
        
        # RSI过滤器
        'enable_rsi_filter': True,              # RSI过滤器
        'rsi_overbought_threshold': 85,         # RSI超买阈值（收紧）
        'rsi_oversold_threshold': 25,           # RSI超卖阈值（收紧）
        
        # 波动率过滤器参数
        'enable_volatility_filter': True,      # 波动率过滤器（关闭）
        'min_volatility': 0.003,                # 最小波动率
        'max_volatility': 0.60,                 # 最大波动率
        'volatility_period': 50,                # 波动率计算周期
        
        # 价格均线纠缠过滤参数 - 只使用距离阈值
        'enable_price_ma_entanglement': True,  # 价格均线纠缠过滤器
        'entanglement_distance_threshold': 0.03, # 纠缠距离阈值（放宽）
        
        # 信号过滤器参数
        'enable_signal_filter': True,            # 趋势过滤器
        'filter_long_base_score': 0.3,          # 多头信号评分阈值 过滤微弱信号
        'filter_long_trend_score': 0.2,         # 多头趋势评分阈值 过滤微弱趋势

        'filter_short_base_score': -0.3,         # 空头信号评分阈值 过滤微弱信号
        'filter_short_trend_score': -0.1,       # 空头趋势评分阈值 过滤微弱趋势
    },
    
    # 夏普优化策略参数
    'sharpe_params': {
        'sharpe_lookback': 30,           # 夏普率计算周期
        'target_sharpe': 1.0,            # 目标夏普率
        'max_risk_multiplier': 2.0,      # 最大风险乘数
        'initial_risk_multiplier': 1.0,  # 初始风险乘数
    },
    
    # 仓位管理配置,根据信号评分，管理仓位大小
    'position_config': {
        'full_score_threshold_min': 0.1,  # sigal_score全仓位阈值,信号评分<0.1时，
        'full_score_threshold_max': 0.7,  # sigal_score全仓位阈值,信号评分>0.7时
        'full_position_size': 1,          # 全仓位(100%) 
        'avg_adjusted_position': 0.2,     # 一般仓位阈值
        'max_adjusted_position': 0.9,     # 最大仓位阈值70%
    },
    
    # 风险管理配置
    'risk_management': {
        'stop_loss': {
            'enable': True,
            'fixed_stop_loss': 0.15,              # 固定止损 8%
        },
        'take_profit': {
            'enable': True,
            'rsi_take_profit': True,              # RSI技术止盈
            'rsi_overbought_take_profit': 75,     # RSI超买止盈阈值
            'rsi_oversold_take_profit': 25,       # RSI超卖止盈阈值
            'time_based_take_profit': False,       # 时间止损止盈
            'time_based_periods': 120,             # 时间止损周期数3天
            'enable_callback': True,              # 回调止盈
            'callback_periods': 12,               # 回调周期数
            'callback_threshold': 0.05,           # 回调阈值
        }
    },
    
    # 冷却处理配置
    'cooldown_treatment': {
        'enable_cooldown_treatment': True,
        'consecutive_loss_threshold': 2,  # 连续亏损阈值
        'mode': 'realtime',              # backtest 或 realtime
        
        # 回测模式配置
        'backtest_mode': {
            'level_1_skip_trades': 3,   # 轻度冷却跳过交易数
            'level_2_skip_trades': 5,   # 中度冷却跳过交易数
            'level_3_skip_trades': 7,   # 重度冷却跳过交易数
        },
        
        # 实盘模式配置
        'realtime_mode': {
            'max_cooldown_treatment_duration': 72,  # 最大冷却时间(小时)
            'cooldown_treatment_levels': {
                'level_1_duration': 24,  # 轻度冷却持续时间(小时)
                'level_2_duration': 48,  # 中度冷却持续时间(小时)
                'level_3_duration': 72,  # 重度冷却持续时间(小时)
            }
        }
    },
    
    # DeepSeek AI信号整合配置
    'enable_deepseek_integration': True,  # 是否启用DeepSeek AI信号整合
    'deepseek_mode': 'realtime_only',      # 模式: 'realtime_only'(仅实盘), 'backtest_only'(仅回测), 'both'(都启用)
    'deepseek_weight': 0.6,                # DeepSeek信号权重 (0-1)
    'deepseek_weights': {
        'trend_score_weight': 0.25,        # 趋势评分权重
        'indicator_score_weight': 0.25,    # 指标评分权重
        'sentiment_score_weight': 0.15,    # 市场情绪权重
        'overall_score_weight': 0.35       # 综合评分权重
    },
    'deepseek_thresholds': {
        'strong_bullish': 0.7,             # 强看涨阈值
        'bullish': 0.6,                    # 看涨阈值
        'neutral': 0.5,                    # 中性阈值
        'bearish': 0.4,                    # 看跌阈值
        'strong_bearish': 0.3              # 强看跌阈值
    },
    'cache_timeout': 3600,                  # 缓存超时时间(秒)
    'deepseek_api_config': {
        'connect_timeout': 10,             # 连接超时时间(秒)
        'read_timeout': 60,                # 读取超时时间(秒)
        'max_retries': 3,                  # 最大重试次数
        'retry_delay': 1,                  # 重试延迟(秒)
        'enable_connection_test': True,    # 是否启用连接测试
    },
}

# ============================================================================
# Telegram通知配置
# ============================================================================
TELEGRAM_CONFIG = {
    'BOT_TOKEN': '',                       # Telegram Bot Token (从环境变量或手动设置)
    'CHAT_ID': '',                         # Telegram Chat ID (从环境变量或手动设置)
    'ENABLED': True,                       # 是否启用Telegram通知
    'NOTIFICATION_TYPES': {
        'SIGNALS': True,                   # 交易信号通知
        'TRADES': True,                    # 交易执行通知
        'ERRORS': True,                    # 错误通知
        'STATUS': True,                    # 状态通知
    },
    'MESSAGE_FORMAT': {
        'PARSE_MODE': 'HTML',              # 消息格式: HTML 或 Markdown
        'DISABLE_WEB_PREVIEW': True,       # 禁用网页预览
    }
}