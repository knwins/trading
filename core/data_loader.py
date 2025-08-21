# -*- coding: utf-8 -*-
# data_loader.py
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import time
import random
from config import *
import pytz  # 添加时区支持

load_dotenv()  # 加载环境变量（仅用于敏感参数）

class TimezoneHandler:
    """统一处理时区转换的类"""
    
    def __init__(self):
        # 设置香港时区
        self.hk_tz = pytz.timezone('Asia/Hong_Kong')
        self.utc_tz = pytz.UTC
        
    def parse_datetime(self, date_str, default_hour=0, default_minute=0, default_second=0):
        """
        解析日期时间字符串，统一转换为香港时区
        
        Args:
            date_str: 日期时间字符串，支持格式：
                     - 'YYYY-MM-DD'
                     - 'YYYY-MM-DD HH:MM:SS'
            default_hour: 默认小时（当只有日期时）
            default_minute: 默认分钟（当只有日期时）
            default_second: 默认秒数（当只有日期时）
            
        Returns:
            datetime: 香港时区的datetime对象
        """
        try:
            if " " in date_str:  # 包含时间信息
                dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            else:  # 只有日期信息
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                dt = dt.replace(hour=default_hour, minute=default_minute, second=default_second)
            
            # 设置为香港时区
            return self.hk_tz.localize(dt)
        except ValueError as e:
            raise ValueError(f"日期格式错误: {date_str}, 错误: {e}")
    
    def to_utc_timestamp(self, hk_datetime):
        """
        将香港时区的datetime转换为UTC时间戳（毫秒）
        
        Args:
            hk_datetime: 香港时区的datetime对象
            
        Returns:
            int: UTC时间戳（毫秒）
        """
        if hk_datetime.tzinfo is None:
            hk_datetime = self.hk_tz.localize(hk_datetime)
        
        utc_datetime = hk_datetime.astimezone(self.utc_tz)
        return int(utc_datetime.timestamp() * 1000)
    
    def from_utc_timestamp(self, utc_timestamp_ms):
        """
        将UTC时间戳（毫秒）转换为香港时区的datetime
        
        Args:
            utc_timestamp_ms: UTC时间戳（毫秒）
            
        Returns:
            datetime: 香港时区的datetime对象
        """
        utc_datetime = datetime.fromtimestamp(utc_timestamp_ms / 1000, self.utc_tz)
        return utc_datetime.astimezone(self.hk_tz)
    
    def get_current_hk_time(self):
        """
        获取当前香港时间
        
        Returns:
            datetime: 当前香港时间
        """
        return datetime.now(self.hk_tz)
    
    def get_current_utc_timestamp(self):
        """
        获取当前UTC时间戳（毫秒）
        
        Returns:
            int: 当前UTC时间戳（毫秒）
        """
        return int(datetime.now(self.utc_tz).timestamp() * 1000)
    
    def validate_time_range(self, start_timestamp, end_timestamp, max_days_back=365, silent=False):
        """
        验证时间范围的合理性
        
        Args:
            start_timestamp: 开始时间戳（毫秒）
            end_timestamp: 结束时间戳（毫秒）
            max_days_back: 最大回看天数
            
        Returns:
            tuple: (调整后的开始时间戳, 调整后的结束时间戳)
        """
        current_timestamp = self.get_current_utc_timestamp()
        
        # 检查是否包含未来时间
        if start_timestamp > current_timestamp or end_timestamp > current_timestamp:
            if not silent:
                print(f"⚠️ 检测到未来时间范围，调整为过去{max_days_back}天")
            end_timestamp = current_timestamp
            start_timestamp = end_timestamp - (max_days_back * 24 * 60 * 60 * 1000)
        
        # 检查时间范围是否合理
        if end_timestamp <= start_timestamp:
            raise ValueError("结束时间必须大于开始时间")
        
        # 检查时间范围是否过长
        max_range_ms = max_days_back * 24 * 60 * 60 * 1000
        if end_timestamp - start_timestamp > max_range_ms:
            print(f"⚠️ 时间范围过长，调整为{max_days_back}天")
            start_timestamp = end_timestamp - max_range_ms
        
        return start_timestamp, end_timestamp
    
    def format_datetime_for_display(self, dt):
        """
        格式化datetime用于显示
        
        Args:
            dt: datetime对象
            
        Returns:
            str: 格式化的时间字符串
        """
        if dt.tzinfo is None:
            dt = self.hk_tz.localize(dt)
        elif dt.tzinfo != self.hk_tz:
            dt = dt.astimezone(self.hk_tz)
        
        return dt.strftime('%Y-%m-%d %H:%M:%S')

class DataLoader:
    def __init__(self, timeframe="1h"):
        self.symbol = TRADING_CONFIG["SYMBOL"]
        self.timeframe = timeframe
        
        # 初始化时区处理器
        self.tz_handler = TimezoneHandler()
        
        # 支持的时间级别映射
        self.timeframe_mapping = {
            "MIN5": "5m",
            "MIN15": "15m",
            "MIN30": "30m", 
            "HOUR1": "1h",
            "HOUR2": "2h",
            "HOUR4": "4h",
            "HOUR8": "8h",
            "DAY1": "1d",
        }
        
        # 使用合约API（仅生产环境）
        self.api_endpoints = [
            "https://fapi.binance.com/fapi/v1"
        ]
        
        # 强制使用真实数据，不使用模拟数据
        self.use_mock_data = False
        # 跳过网络连接测试，允许离线模式
        try:
            self._test_connection()
        except Exception as e:
            print(f"⚠️ 网络连接测试失败，将使用模拟数据: {e}")
            self.use_mock_data = True
        
        # 贪婪指数缓存
        self.fear_greed_cache = {}
        self.fear_greed_cache_timeout = 3600  # 1小时缓存
    
    def _test_connection(self):
        """测试API连接"""
        print("🔍 正在测试API连接...")
        print(f" 交易对: {self.symbol}")
        print(f"⏰ 时间框架: {self.timeframe}")
        
        try:
            endpoint = self.api_endpoints[0]
            print(f"🔗 测试API端点: {endpoint}")
            response = requests.get(f"{endpoint}/time", timeout=5)
            if response.status_code == 200:
                print(f"✅ 成功连接到Binance合约API: {endpoint}")
            else:
                print(f"⚠️ 合约API端点响应异常: {response.status_code}")
                raise ConnectionError("合约API端点响应异常")
        except Exception as e:
            print(f"❌ API端点连接失败: {e}")
            raise ConnectionError("无法连接到Binance合约API端点，请检查网络连接")
    
    def _make_request(self, url, params=None, max_retries=3):
        """发送HTTP请求，带重试机制"""
        for attempt in range(max_retries):
            try:
                endpoint = self.api_endpoints[0]
                full_url = f"{endpoint}{url}"
                
                # 显示完整的API URL（仅在调试模式下）
                if DEBUG_CONFIG["SHOW_API_URLS"]:
                    print(f"🌐 请求API URL: {full_url}")
                    if params:
                        print(f"📋 请求参数: {params}")
                
                # 添加随机延迟，避免请求过于频繁
                time.sleep(random.uniform(0.2, 1.0))  # 增加延迟时间
                
                response = requests.get(full_url, params=params, timeout=30)  # 增加超时时间
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:  # 请求频率限制
                    print(f"⚠ 请求频率限制，等待后重试...")
                    time.sleep(5 + (2 ** attempt))  # 增加基础等待时间
                    continue
                elif response.status_code == 503:  # 服务不可用
                    print(f"⚠ 服务不可用，等待后重试...")
                    time.sleep(10 + (2 ** attempt))  # 更长的等待时间
                    continue
                else:
                    print(f"⚠ API响应异常: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"⚠ 请求异常 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(3 + (2 ** attempt))  # 增加基础等待时间
                else:
                    print(f"❌ 所有重试失败，跳过此请求")
                    return None
        
        return None
    

    
    def get_klines(self, start_date, end_date, silent=False):
        """获取指定时间范围的 K 线数据（开盘价、收盘价等）"""
        
        try:
            if not silent:
                print(" 正在获取Binance合约真实历史数据...")
            
            # 使用统一的时区处理器解析日期
            start_datetime = self.tz_handler.parse_datetime(start_date, default_hour=0, default_minute=0, default_second=0)
            
            # 处理结束日期
            if " " in end_date:  # 包含时间信息
                end_datetime = self.tz_handler.parse_datetime(end_date)
                # 为了确保包含目标时间点，将结束时间延长1小时
                end_datetime = end_datetime + timedelta(hours=1)
            else:  # 只有日期信息
                end_datetime = self.tz_handler.parse_datetime(end_date, default_hour=23, default_minute=59, default_second=59)
            
            # 转换为UTC时间戳
            start_timestamp = self.tz_handler.to_utc_timestamp(start_datetime)
            end_timestamp = self.tz_handler.to_utc_timestamp(end_datetime)
            
            # 验证时间范围合理性
            start_timestamp, end_timestamp = self.tz_handler.validate_time_range(
                start_timestamp, 
                end_timestamp, 
                max_days_back=BACKTEST_CONFIG.get('BACKTEST_DAYS', 60),
                silent=silent
            )
            
            # 显示香港时间范围
            start_hk = self.tz_handler.from_utc_timestamp(start_timestamp)
            end_hk = self.tz_handler.from_utc_timestamp(end_timestamp)
            if not silent:
                print(f"📅 实际请求时间范围: {self.tz_handler.format_datetime_for_display(start_hk)} 至 {self.tz_handler.format_datetime_for_display(end_hk)} (香港时间)")
            
            # 分页获取完整数据
            all_klines = []
            current_start = start_timestamp
            page_count = 0
            
            while current_start < end_timestamp and page_count < 100:  # 增加最大页数限制，支持更长时间范围
                try:
                    params = {
                        "symbol": self.symbol,
                        "interval": self.timeframe,
                        "startTime": current_start,
                        "endTime": end_timestamp,
                        "limit": 1000  # Binance API最大限制
                    }
                
                    if not silent:
                        print(f"  📡 正在获取第 {page_count + 1} 页合约数据...")
                    klines_data = self._make_request("/klines", params)
                    
                    if klines_data is None:
                        print("❌ 获取合约数据失败")
                        raise ConnectionError("无法从合约API获取数据")
                    
                    if not klines_data:  # 没有更多数据
                        if not silent:
                            print("  ✅ 数据获取完成")
                        break
                        
                    # 转换为标准格式并添加到总列表
                    for kline in klines_data:
                        all_klines.append([
                            int(kline[0]),  # 时间戳
                            float(kline[1]),  # open
                            float(kline[2]),  # high
                            float(kline[3]),  # low
                            float(kline[4]),  # close
                            float(kline[5])   # volume
                        ])
                    
                    # 更新下一次请求的开始时间
                    if klines_data:
                        current_start = int(klines_data[-1][0]) + 1
                    else:
                        break
                    
                    page_count += 1
                    if not silent:
                        print(f"  ✅ 已获取 {len(all_klines)} 条数据...")
                    
                    # 添加短暂延迟避免API限制
                    time.sleep(0.1)
                    
                except KeyboardInterrupt:
                    print("\n⚠ 用户中断数据获取")
                    raise KeyboardInterrupt("用户中断数据获取")
                except Exception as e:
                    print(f"❌ 获取第 {page_count + 1} 页数据失败: {e}")
                    raise e
            
            if all_klines:
                if not silent:
                    print(f" 成功获取 {len(all_klines)} 条合约历史数据")
                
                # 过滤数据，只保留到目标时间点的数据
                if " " in end_date:  # 如果指定了具体时间
                    try:
                        # 使用统一的时区处理器处理目标时间
                        target_end_time = self.tz_handler.parse_datetime(end_date)
                        target_end_timestamp = self.tz_handler.to_utc_timestamp(target_end_time)
                        
                        # 过滤掉超过目标时间的数据
                        filtered_klines = [kline for kline in all_klines if kline[0] <= target_end_timestamp]
                        if len(filtered_klines) != len(all_klines) and not silent:
                            print(f"  📊 过滤后保留 {len(filtered_klines)} 条数据 (目标时间: {self.tz_handler.format_datetime_for_display(target_end_time)} 香港时间)")
                        klines = filtered_klines
                    except Exception as e:
                        print(f"⚠️ 时间过滤失败，使用全部数据: {e}")
                        klines = all_klines
                else:
                    klines = all_klines
            else:
                print("❌ 未获取到任何合约数据")
                raise ValueError("未获取到任何合约历史数据")
            
        except Exception as e:
            print(f"❌ 获取合约历史数据失败: {e}")
            raise e
        
        # 转换为 DataFrame 并格式化
        df = pd.DataFrame(
            klines,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        
        # 验证时间戳的有效性
        if df.empty:
            print("⚠️ 警告: 数据为空")
            return df
        
        # 将UTC时间戳转换为香港时间 - 统一时区处理
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(self.tz_handler.hk_tz)
        
        # 验证时区转换结果
        if df["datetime"].isna().any():
            print("⚠️ 警告: 部分时间戳转换失败")
        
        df = df.set_index("datetime").drop(columns=["timestamp"])
        
        # 显示数据时间范围
        if not df.empty and not silent:
            print(f"📊 数据时间范围: {df.index.min()} 至 {df.index.max()} (香港时间)")
        
        return df.astype(float)  # 确保数值类型正确
    
    def get_current_timestamp(self):
        """
        获取当前UTC时间戳（毫秒）
        
        Returns:
            int: 当前UTC时间戳（毫秒）
        """
        return self.tz_handler.get_current_utc_timestamp()
    
    def test_timezone_handling(self):
        """
        测试时区处理功能
        
        Returns:
            dict: 测试结果
        """
        try:
            print("🧪 测试时区处理功能...")
            
            # 测试1: 解析不同格式的日期
            test_cases = [
                "2025-01-15",
                "2025-01-15 14:30:00",
                "2025-01-15 23:59:59"
            ]
            
            results = {}
            for test_date in test_cases:
                try:
                    parsed = self.tz_handler.parse_datetime(test_date)
                    timestamp = self.tz_handler.to_utc_timestamp(parsed)
                    converted_back = self.tz_handler.from_utc_timestamp(timestamp)
                    formatted = self.tz_handler.format_datetime_for_display(converted_back)
                    
                    results[test_date] = {
                        'parsed': str(parsed),
                        'timestamp': timestamp,
                        'converted_back': str(converted_back),
                        'formatted': formatted,
                        'success': True
                    }
                except Exception as e:
                    results[test_date] = {
                        'error': str(e),
                        'success': False
                    }
            
            # 测试2: 时间范围验证
            current_time = self.tz_handler.get_current_utc_timestamp()
            future_time = current_time + (24 * 60 * 60 * 1000)  # 未来1天
            past_time = current_time - (24 * 60 * 60 * 1000)    # 过去1天
            
            try:
                validated_start, validated_end = self.tz_handler.validate_time_range(
                    future_time, future_time + 1000, max_days_back=30
                )
                results['time_validation'] = {
                    'future_time_adjusted': True,
                    'validated_start': validated_start,
                    'validated_end': validated_end,
                    'success': True
                }
            except Exception as e:
                results['time_validation'] = {
                    'error': str(e),
                    'success': False
                }
            
            # 测试3: 当前时间获取
            current_hk = self.tz_handler.get_current_hk_time()
            current_utc_ts = self.tz_handler.get_current_utc_timestamp()
            
            results['current_time'] = {
                'hk_time': str(current_hk),
                'utc_timestamp': current_utc_ts,
                'formatted_hk': self.tz_handler.format_datetime_for_display(current_hk),
                'success': True
            }
            
            print("✅ 时区处理测试完成")
            return results
            
        except Exception as e:
            print(f"❌ 时区处理测试失败: {e}")
            return {'error': str(e), 'success': False}
    
    def get_fear_greed_index(self, date=None):
        """
        获取恐惧贪婪指数
        
        Args:
            date: 指定日期，格式为 'YYYY-MM-DD'，默认为当前日期
            
        Returns:
            dict: 包含贪婪指数信息的字典
        """
        try:
            # 如果没有指定日期，使用当前日期
            if date is None:
                date = self.tz_handler.get_current_hk_time().strftime('%Y-%m-%d')
            
            # 检查缓存
            cache_key = f"fear_greed_{date}"
            current_time = time.time()
            
            if cache_key in self.fear_greed_cache:
                cache_data = self.fear_greed_cache[cache_key]
                if current_time - cache_data['timestamp'] < self.fear_greed_cache_timeout:
                    return cache_data['data']
            
            # 从 Alternative.me API 获取数据
            url = "https://api.alternative.me/fng/"
            params = {
                'limit': 1,
                'format': 'json'
            }
            
            # 如果指定了日期，添加日期参数
            if date:
                try:
                    # 将日期转换为时间戳
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    timestamp = int(date_obj.timestamp())
                    params['date'] = timestamp
                    print(f"📅 请求指定日期的贪婪指数: {date} (时间戳: {timestamp})")
                except ValueError as e:
                    print(f"⚠️ 日期格式错误: {e}")
                    # 如果日期格式错误，使用当前日期
                    date = datetime.now().strftime('%Y-%m-%d')
            
            print(f"🔍 正在获取贪婪指数数据...")
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('data') and len(data['data']) > 0:
                    latest = data['data'][0]
                    
                    # 根据外部数据确定贪婪程度（按照图片标准）
                    external_value = int(latest['value'])
                    if external_value > 75:
                        greed_level = 1.0  # 极度贪婪 (76-100)
                    elif external_value > 55:
                        greed_level = 0.8  # 贪婪 (56-75)
                    elif external_value > 45:
                        greed_level = 0.6  # 中性 (46-55)
                    elif external_value > 25:
                        greed_level = 0.4  # 恐惧 (26-45)
                    else:
                        greed_level = 0.2  # 极度恐惧 (0-25)
                    
                    fear_greed_data = {
                        'value': external_value,
                        'classification': latest['value_classification'],
                        'greed_level': greed_level,
                        'timestamp': latest['timestamp'],
                        'date': date
                    }
                    
                    # 缓存数据
                    self.fear_greed_cache[cache_key] = {
                        'data': fear_greed_data,
                        'timestamp': current_time
                    }
                    
                    print(f"✅ 贪婪指数: {fear_greed_data['value']} ({fear_greed_data['classification']})")
                    return fear_greed_data
                else:
                    print("⚠️ 贪婪指数数据格式异常")
                    return self._get_default_fear_greed()
            else:
                print(f"⚠️ 贪婪指数API请求失败: {response.status_code}")
                return self._get_default_fear_greed()
                
        except Exception as e:
            print(f"❌ 获取贪婪指数失败: {e}")
            return self._get_default_fear_greed()
    
    def _get_default_fear_greed(self):
        """获取默认贪婪指数（当API不可用时）"""
        return {
            'value': 50,
            'classification': 'Neutral',
            'greed_level': 0.6,  # 中性
            'timestamp': str(int(time.time())),
            'date': self.tz_handler.get_current_hk_time().strftime('%Y-%m-%d')
        }
    
    def get_vix_fear_index(self, date=None):
        """
        获取VIX恐慌指数
        
        Args:
            date: 指定日期，格式为 'YYYY-MM-DD'，默认为当前日期
            
        Returns:
            dict: 包含VIX恐慌指数信息的字典
        """
        try:
            # 如果没有指定日期，使用当前日期
            if date is None:
                date = self.tz_handler.get_current_hk_time().strftime('%Y-%m-%d')
            
            # 检查缓存
            cache_key = f"vix_fear_{date}"
            current_time = time.time()
            
            if cache_key in self.fear_greed_cache:
                cache_data = self.fear_greed_cache[cache_key]
                if current_time - cache_data['timestamp'] < self.fear_greed_cache_timeout:
                    return cache_data['data']
            
            # 根据日期生成不同的模拟VIX数据
            vix_data = self._get_simulated_vix_data(date)
            
            # 缓存数据
            self.fear_greed_cache[cache_key] = {
                'data': vix_data,
                'timestamp': current_time
            }
            
            print(f"✅ VIX恐慌指数: {vix_data['value']:.2f} ({vix_data['classification']})")
            return vix_data
                
        except Exception as e:
            print(f"❌ 获取VIX恐慌指数失败: {e}")
            return self._get_default_vix_fear()
    
    def _get_simulated_vix_data(self, date=None):
        """获取模拟VIX数据（实际项目中需要替换为真实API）"""
        # 这里使用模拟数据，实际项目中应该调用真实的VIX API
        # 例如：Alpha Vantage API, Yahoo Finance API 等
        
        # 根据日期生成一致的模拟VIX值
        import random
        if date:
            # 使用日期作为随机种子，确保同一天返回相同的值
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            seed = date_obj.year * 10000 + date_obj.month * 100 + date_obj.day
            random.seed(seed)
        
        vix_value = random.uniform(15, 35)
        
        # 根据VIX值确定恐慌程度（按照图片标准）
        if vix_value > 40:
            classification = "Extreme Fear"
            fear_level = 1.0
        elif vix_value > 30:
            classification = "High Fear"
            fear_level = 0.8
        elif vix_value > 20:
            classification = "Fear"
            fear_level = 0.6
        elif vix_value > 15:
            classification = "Neutral"
            fear_level = 0.4
        else:
            classification = "Low Fear"
            fear_level = 0.2
        
        return {
            'value': round(vix_value, 2),
            'classification': classification,
            'fear_level': fear_level,
            'timestamp': str(int(time.time())),
            'date': self.tz_handler.get_current_hk_time().strftime('%Y-%m-%d')
        }
    
    def _get_default_vix_fear(self):
        """获取默认VIX恐慌指数（当API不可用时）"""
        return {
            'value': 20.0,
            'classification': 'Neutral',
            'fear_level': 0.4,
            'timestamp': str(int(time.time())),
            'date': self.tz_handler.get_current_hk_time().strftime('%Y-%m-%d')
        }
    
    def get_timeframe_data(self, timeframe, start_date=None, end_date=None, limit=1000):
        """
        获取指定时间级别的K线数据
        
        Args:
            timeframe: 时间级别 ('1h', '4h', '1d' 等)
            start_date: 开始日期，格式为 'YYYY-MM-DD' 或 'YYYY-MM-DD HH:MM:SS'
            end_date: 结束日期，格式为 'YYYY-MM-DD' 或 'YYYY-MM-DD HH:MM:SS'
            limit: 数据条数限制
            
        Returns:
            DataFrame: K线数据
        """
        try:
            print(f"📡 正在获取 {timeframe} 时间级别数据...")
            
            # 验证时间级别
            if timeframe not in self.timeframe_mapping.values():
                raise ValueError(f"不支持的时间级别: {timeframe}")
            
            # 设置默认时间范围
            if end_date is None:
                # 使用当前时间，但确保不超过当前时间
                current_time = self.tz_handler.get_current_hk_time()
                end_date = self.tz_handler.format_datetime_for_display(current_time)
            
            if start_date is None:
                # 根据时间级别计算合适的开始时间
                # 限制历史数据范围，避免超出API限制
                if timeframe == '1h':
                    start_time = current_time - timedelta(days=180)
                elif timeframe == '2h':
                    # 2小时数据应该与1小时数据使用相同的时间范围
                    start_time = current_time - timedelta(days=180)
                elif timeframe == '4h':
                    # 4小时数据应该与1小时数据使用相同的时间范围
                    start_time = current_time - timedelta(days=180)
                elif timeframe == '1d':
                    start_time = current_time - timedelta(days=365)  # 减少到365天
                else:
                    start_time = current_time - timedelta(days=180)
                start_date = self.tz_handler.format_datetime_for_display(start_time)
            
            # 使用统一的时区处理器转换时间格式
            start_time = self.tz_handler.parse_datetime(start_date)
            start_timestamp = self.tz_handler.to_utc_timestamp(start_time)
            
            end_time = self.tz_handler.parse_datetime(end_date)
            end_timestamp = self.tz_handler.to_utc_timestamp(end_time)
            
            # 调试时间戳转换（仅在需要时显示）
            if DEBUG_CONFIG["SHOW_API_URLS"]:
                print(f"🔍 4小时数据时间戳调试:")
                print(f"  - start_date: {start_date}")
                print(f"  - end_date: {end_date}")
                print(f"  - start_time: {start_time}")
                print(f"  - end_time: {end_time}")
                print(f"  - start_timestamp: {start_timestamp}")
                print(f"  - end_timestamp: {end_timestamp}")
            
            # 验证时间范围合理性
            # 根据时间级别调整最大历史天数
            if timeframe == '1h':
                max_days = 180
            elif timeframe == '4h':
                max_days = 180
            elif timeframe == '1d':
                max_days = 365
            else:
                max_days = 180
                
            start_timestamp, end_timestamp = self.tz_handler.validate_time_range(
                start_timestamp, 
                end_timestamp, 
                max_days_back=max_days
            )
            
            # 构建API请求参数
            params = {
                'symbol': self.symbol,
                'interval': timeframe,
                'startTime': start_timestamp,
                'endTime': end_timestamp,
                'limit': limit
            }
            
            # 发送请求
            endpoint = self.api_endpoints[0]
            url = "/klines"
            
            if DEBUG_CONFIG["SHOW_API_URLS"]:
                print(f"🌐 请求 {timeframe} 数据 URL: {endpoint}{url}")
                print(f"📋 请求参数: {params}")
            
            response_data = self._make_request(url, params)
            
            if not response_data:
                print(f"❌ 未获取到 {timeframe} 时间级别数据")
                return pd.DataFrame()
            
            # 转换为DataFrame - 处理不同列数的响应
            if response_data and len(response_data) > 0:
                # 检查第一行数据的列数
                first_row = response_data[0]
                if len(first_row) >= 6:
                    # 标准K线数据格式
                    df = pd.DataFrame(
                        response_data,
                        columns=["timestamp", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"]
                    )
                    # 只保留需要的列
                    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
                else:
                    print(f"❌ 响应数据格式异常，列数: {len(first_row)}")
                    return pd.DataFrame()
            else:
                print(f"❌ 响应数据为空")
                return pd.DataFrame()
            
            # 转换时间戳
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True).dt.tz_convert(self.tz_handler.hk_tz)
            df = df.set_index("datetime").drop(columns=["timestamp"])
            
            print(f"✅ 成功获取 {len(df)} 条 {timeframe} 时间级别数据")
            print(f"📊 时间范围: {df.index.min()} 至 {df.index.max()} (香港时间)")
            
            return df.astype(float)
            
        except Exception as e:
            print(f"❌ 获取 {timeframe} 时间级别数据失败: {e}")
            return pd.DataFrame()