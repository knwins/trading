#!/usr/bin/env python38
# -*- coding: utf-8 -*-
"""
真实交易所API集成模块
支持Binance合约交易
"""

import ccxt
import time
import hmac
import hashlib
import requests
from datetime import datetime
from typing import Dict, Optional, Tuple
from config import BINANCE_API_CONFIG

def get_current_ip() -> str:
    """获取当前公网IP地址"""
    try:
        ip_services = [
            'https://api.ipify.org',
            'https://ifconfig.me/ip',
            'https://checkip.amazonaws.com',
            'https://ipinfo.io/ip',
            'https://icanhazip.com'
        ]
        
        for service in ip_services:
            try:
                response = requests.get(service, timeout=5)
                if response.status_code == 200:
                    ip = response.text.strip()
                    if ip and '.' in ip and len(ip.split('.')) == 4:
                        parts = ip.split('.')
                        if not (parts[0] == '10' or 
                               (parts[0] == '172' and 16 <= int(parts[1]) <= 31) or
                               (parts[0] == '192' and parts[1] == '168')):
                            return ip
            except:
                continue
        
        try:
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return f"本地IP: {local_ip} (公网IP获取失败)"
        except:
            return "IP获取失败"
    except:
        return "IP获取失败"

class RealExchangeAPI:
    """真实交易所API类"""
    
    def __init__(self, api_key: str = None, secret_key: str = None, testnet: bool = False):
        """初始化交易所API"""
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        
        # 从配置中获取API设置
        api_config = BINANCE_API_CONFIG['TESTNET'] if testnet else BINANCE_API_CONFIG['MAINNET']
        self.base_url = api_config['BASE_URL']
        self.api_version = api_config['API_VERSION']
        self.futures_api_version = api_config['FUTURES_API_VERSION']
        self.timeout = api_config['TIMEOUT']
        self.recv_window = api_config['RECV_WINDOW']
        
        # 初始化ccxt交易所
        exchange_config = {
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'sandbox': testnet,
            'options': {
                'defaultType': 'future',
                'adjustForTimeDifference': True,
                'recvWindow': self.recv_window,
            }
        }
        
        self.exchange = ccxt.binance(exchange_config)
        
        # 强制设置期货API端点
        self.exchange.urls['api'] = {
            'public': f'{self.base_url}/fapi/{self.api_version}',
            'private': f'{self.base_url}/fapi/{self.api_version}',
        }
        
        # 禁用现货API调用
        self.exchange.has['fetchBalance'] = False
        self.exchange.has['fetchTicker'] = True
        
        self.logger = None
    
    def set_logger(self, logger):
        """设置日志器"""
        self.logger = logger
    
    def _create_signature(self, query_string: str) -> str:
        """创建API签名"""
        return hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _make_api_request(self, endpoint: str, method: str = 'GET', params: dict = None) -> Dict:
        """统一的API请求方法"""
        try:
            timestamp = int(time.time() * 1000)
            
            # 构建查询参数
            query_params = {
                'timestamp': timestamp,
                'recvWindow': self.recv_window
            }
            if params:
                query_params.update(params)
            
            # 构建查询字符串
            query_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])
            
            # 创建签名
            signature = self._create_signature(query_string)
            
            # 构建URL
            url = f"{self.base_url}{endpoint}?{query_string}&signature={signature}"
            
            # 设置请求头
            headers = {'X-MBX-APIKEY': self.api_key}
            
            # 发送请求
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, timeout=self.timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, timeout=self.timeout)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            if response.status_code == 200:
                return {'success': True, 'data': response.json()}
            else:
                return {
                    'success': False, 
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def test_connection(self) -> Tuple[bool, str]:
        """测试API连接"""
        try:
            url = f"{self.base_url}/fapi/{self.api_version}/ticker/price?symbol=ETHUSDT"
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if 'price' in data:
                    return True, "✅ API连接正常"
                else:
                    return False, "❌ 无法获取市场数据"
            else:
                return False, f"❌ API连接失败: HTTP {response.status_code}"
        except Exception as e:
            return False, f"❌ API连接失败: {str(e)}"
    
    def get_balance(self) -> Dict:
        """获取合约账户余额"""
        result = self._make_api_request(f"/fapi/{self.futures_api_version}/account")
        
        if result['success']:
            account_data = result['data']
            total_balance = float(account_data.get('totalWalletBalance', 0))
            available_balance = float(account_data.get('availableBalance', 0))
            
            if self.logger:
                self.logger.info(f"合约账户余额: 总={total_balance:.2f}, 可用={available_balance:.2f}")
            
            return {
                'success': True,
                'total': total_balance,
                'available': available_balance,
                'used': total_balance - available_balance
            }
        else:
            if self.logger:
                self.logger.error(f"获取合约账户余额失败: {result['error']}")
            return {
                'success': False,
                'error': result['error'],
                'total': 0,
                'available': 0,
                'used': 0
            }
    
    def get_position(self, symbol: str = 'ETHUSDT') -> Dict:
        """获取当前仓位"""
        result = self._make_api_request(f"/fapi/{self.futures_api_version}/account")
        
        if result['success']:
            account_data = result['data']
            positions = account_data.get('positions', [])
            
            for pos in positions:
                if pos['symbol'] == symbol:
                    position_amt = float(pos['positionAmt'])
                    leverage = int(pos.get('leverage', 1))
                    # 安全获取marginType，如果不存在则使用默认值
                    margin_type = pos.get('marginType', BINANCE_API_CONFIG['COMMON']['DEFAULT_MARGIN_TYPE'])
                    
                    return {
                        'size': abs(position_amt),
                        'side': 'long' if position_amt > 0 else 'short' if position_amt < 0 else None,
                        'entry_price': float(pos.get('entryPrice', 0)),
                        'mark_price': float(pos.get('markPrice', 0)),
                        'unrealized_pnl': float(pos.get('unRealizedProfit', 0)),
                        'margin_type': margin_type,
                        'leverage': leverage
                    }
            
            # 如果没有找到仓位，返回默认值
            return {
                'size': 0, 'side': None, 'entry_price': 0, 'mark_price': 0, 
                'unrealized_pnl': 0, 'margin_type': BINANCE_API_CONFIG['COMMON']['DEFAULT_MARGIN_TYPE'], 
                'leverage': BINANCE_API_CONFIG['COMMON']['DEFAULT_LEVERAGE']
            }
        else:
            if self.logger:
                self.logger.error(f"获取仓位失败: {result['error']}")
            return {
                'size': 0, 'side': None, 'entry_price': 0, 'mark_price': 0, 
                'unrealized_pnl': 0, 'margin_type': BINANCE_API_CONFIG['COMMON']['DEFAULT_MARGIN_TYPE'], 
                'leverage': BINANCE_API_CONFIG['COMMON']['DEFAULT_LEVERAGE']
            }
    
    def set_margin_type(self, symbol: str, margin_type: str = 'ISOLATED') -> Dict:
        """设置保证金类型"""
        try:
            params = {
                'symbol': symbol,
                'marginType': margin_type
            }
            
            result = self._make_api_request(f"/fapi/{self.api_version}/marginType", method='POST', params=params)
            
            if result['success']:
                if self.logger:
                    self.logger.info(f"设置保证金类型成功: {symbol} {margin_type}")
                
                return {
                    'success': True,
                    'message': f'保证金类型设置成功: {margin_type}',
                    'symbol': symbol,
                    'margin_type': margin_type
                }
            else:
                error_msg = result['error']
                current_ip = get_current_ip()
                
                if '-4046' in error_msg:
                    error_msg = f'保证金类型设置失败: 当前有开仓，无法修改保证金类型 (IP: {current_ip})'
                elif '-2015' in error_msg:
                    error_msg = f'API权限不足: 请确保API密钥具有"期货交易"权限并已添加IP白名单 (IP: {current_ip})'
                else:
                    error_msg = f'保证金类型设置失败: {error_msg} (IP: {current_ip})'
                
                if self.logger:
                    self.logger.error(f"设置保证金类型失败: {error_msg}")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'symbol': symbol,
                    'margin_type': margin_type,
                    'ip_info': f'当前IP: {current_ip}'
                }
                
        except Exception as e:
            error_msg = str(e)
            current_ip = get_current_ip()
            
            if self.logger:
                self.logger.error(f"设置保证金类型失败: {error_msg}")
            
            return {
                'success': False,
                'error': f'{error_msg} (IP: {current_ip})',
                'symbol': symbol,
                'margin_type': margin_type,
                'ip_info': f'当前IP: {current_ip}'
            }
    
    def set_leverage(self, symbol: str, leverage: int) -> Dict:
        """设置杠杆"""
        try:
            # 检查当前仓位
            position = self.get_position(symbol)
            current_leverage = position.get('leverage', 1)
            current_size = position.get('size', 0)
            
            # 如果有开仓，无法修改杠杆
            if current_size > 0:
                return {
                    'success': False,
                    'error': f'当前有开仓 ({current_size})，无法修改杠杆。请先平仓后再设置杠杆。',
                    'current': current_leverage,
                    'target': leverage
                }
            
            # 如果杠杆已经是目标值，无需修改
            if current_leverage == leverage:
                return {
                    'success': True,
                    'message': f'杠杆已经是 {leverage}x，无需修改',
                    'current': current_leverage,
                    'target': leverage
                }
            
            # 设置杠杆
            params = {
                'symbol': symbol,
                'leverage': leverage
            }
            
            result = self._make_api_request(f"/fapi/{self.api_version}/leverage", method='POST', params=params)
            
            if result['success']:
                if self.logger:
                    self.logger.info(f"设置杠杆成功: {symbol} {leverage}x (原: {current_leverage}x)")
                
                return {
                    'success': True,
                    'message': f'杠杆设置成功: {current_leverage}x → {leverage}x',
                    'current': current_leverage,
                    'target': leverage
                }
            else:
                error_msg = result['error']
                current_ip = get_current_ip()
                
                if '-2015' in error_msg:
                    error_msg = f'API权限不足: 请确保API密钥具有"期货交易"权限并已添加IP白名单 (IP: {current_ip})'
                elif '-4046' in error_msg:
                    error_msg = f'杠杆设置失败: 请先设置保证金类型为ISOLATED (IP: {current_ip})'
                else:
                    error_msg = f'杠杆设置失败: {error_msg} (IP: {current_ip})'
                
                if self.logger:
                    self.logger.error(f"设置杠杆失败: {error_msg}")
                
                return {
                    'success': False,
                    'error': error_msg,
                    'current': current_leverage,
                    'target': leverage,
                    'ip_info': f'当前IP: {current_ip}'
                }
                
        except Exception as e:
            error_msg = str(e)
            current_ip = get_current_ip()
            
            if self.logger:
                self.logger.error(f"设置杠杆失败: {error_msg}")
            
            return {
                'success': False,
                'error': f'{error_msg} (IP: {current_ip})',
                'current': 1,
                'target': leverage,
                'ip_info': f'当前IP: {current_ip}'
            }
    
    def place_order(self, symbol: str, side: str, amount: float, order_type: str = 'market') -> Dict:
        """下单"""
        try:
            order = self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount
            )
            
            if self.logger:
                self.logger.info(f"下单成功: {symbol} {side} {amount} {order_type}")
            
            return {
                'success': True,
                'order_id': order['id'],
                'symbol': order['symbol'],
                'side': order['side'],
                'amount': order['amount'],
                'price': order['price'],
                'status': order['status']
            }
        except Exception as e:
            if self.logger:
                self.logger.error(f"下单失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def close_position(self, symbol: str) -> Dict:
        """平仓"""
        try:
            position = self.get_position(symbol)
            if position['size'] == 0:
                return {'success': True, 'message': '无仓位需要平仓'}
            
            # 计算平仓方向
            close_side = 'sell' if position['side'] == 'long' else 'buy'
            
            order = self.place_order(symbol, close_side, position['size'])
            
            if self.logger:
                self.logger.info(f"平仓成功: {symbol} {close_side} {position['size']}")
            
            return order
        except Exception as e:
            if self.logger:
                self.logger.error(f"平仓失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_order_status(self, order_id: str, symbol: str) -> Dict:
        """获取订单状态"""
        try:
            order = self.exchange.fetch_order(order_id, symbol)
            return {
                'id': order['id'],
                'symbol': order['symbol'],
                'side': order['side'],
                'amount': order['amount'],
                'price': order['price'],
                'status': order['status'],
                'filled': order['filled'],
                'remaining': order['remaining']
            }
        except Exception as e:
            if self.logger:
                self.logger.error(f"获取订单状态失败: {e}")
            return {'status': 'unknown', 'error': str(e)}
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """取消订单"""
        try:
            self.exchange.cancel_order(order_id, symbol)
            if self.logger:
                self.logger.info(f"取消订单成功: {order_id}")
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"取消订单失败: {e}")
            return False
