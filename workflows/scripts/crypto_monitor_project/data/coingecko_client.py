# -*- coding: utf-8 -*-
"""
CoinGecko API客户端
负责获取市场数据和新闻信息
"""

import requests
import time
from typing import Dict, Any, Optional, List

from ..config import Settings


class CoinGeckoClient:
    """CoinGecko API客户端"""
    
    def __init__(self, settings: Settings):
        """
        初始化CoinGecko客户端
        
        Args:
            settings: 系统配置对象
        """
        self.settings = settings
        self.base_url = "https://api.coingecko.com/api/v3"
        self.request_interval = settings.api.coingecko_interval
        self.last_request_time = 0
    
    def _wait_for_rate_limit(self):
        """等待请求频率限制"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.request_interval:
            sleep_time = self.request_interval - elapsed
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def get_market_data(self, coin_id: str) -> Optional[Dict[str, Any]]:
        """
        获取币种市场数据
        
        Args:
            coin_id: CoinGecko币种ID
            
        Returns:
            Optional[Dict[str, Any]]: 市场数据，失败时返回None
        """
        self._wait_for_rate_limit()
        
        url = f"{self.base_url}/coins/{coin_id}"
        params = {
            'localization': 'false',
            'tickers': 'false',
            'market_data': 'true',
            'community_data': 'false',
            'developer_data': 'false',
            'sparkline': 'false'
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            market_data = data.get('market_data', {})
            
            return {
                'id': data.get('id'),
                'symbol': data.get('symbol'),
                'name': data.get('name'),
                'current_price_usd': market_data.get('current_price', {}).get('usd'),
                'market_cap_usd': market_data.get('market_cap', {}).get('usd'),
                'market_cap_rank': market_data.get('market_cap_rank'),
                'total_volume_usd': market_data.get('total_volume', {}).get('usd'),
                'price_change_24h': market_data.get('price_change_24h'),
                'price_change_percentage_24h': market_data.get('price_change_percentage_24h'),
                'price_change_percentage_7d': market_data.get('price_change_percentage_7d'),
                'price_change_percentage_30d': market_data.get('price_change_percentage_30d'),
                'circulating_supply': market_data.get('circulating_supply'),
                'total_supply': market_data.get('total_supply'),
                'max_supply': market_data.get('max_supply'),
                'ath': market_data.get('ath', {}).get('usd'),
                'ath_change_percentage': market_data.get('ath_change_percentage', {}).get('usd'),
                'atl': market_data.get('atl', {}).get('usd'),
                'atl_change_percentage': market_data.get('atl_change_percentage', {}).get('usd'),
                'last_updated': market_data.get('last_updated')
            }
            
        except Exception as e:
            print(f"❌ 获取{coin_id}市场数据失败: {e}")
            return None
    
    def get_global_market_data(self) -> Optional[Dict[str, Any]]:
        """
        获取全球市场数据
        
        Returns:
            Optional[Dict[str, Any]]: 全球市场数据，失败时返回None
        """
        self._wait_for_rate_limit()
        
        url = f"{self.base_url}/global"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            global_data = data.get('data', {})
            
            return {
                'active_cryptocurrencies': global_data.get('active_cryptocurrencies'),
                'upcoming_icos': global_data.get('upcoming_icos'),
                'ongoing_icos': global_data.get('ongoing_icos'),
                'ended_icos': global_data.get('ended_icos'),
                'markets': global_data.get('markets'),
                'total_market_cap_usd': global_data.get('total_market_cap', {}).get('usd'),
                'total_volume_24h_usd': global_data.get('total_volume', {}).get('usd'),
                'market_cap_percentage': global_data.get('market_cap_percentage', {}),
                'market_cap_change_percentage_24h_usd': global_data.get('market_cap_change_percentage_24h_usd'),
                'updated_at': global_data.get('updated_at')
            }
            
        except Exception as e:
            print(f"❌ 获取全球市场数据失败: {e}")
            return None
    
    def get_fear_greed_index(self) -> Optional[Dict[str, Any]]:
        """
        获取恐慌贪婪指数
        
        Returns:
            Optional[Dict[str, Any]]: 恐慌贪婪指数数据，失败时返回None
        """
        try:
            fng_url = "https://api.alternative.me/fng/"
            response = requests.get(fng_url, timeout=10)
            
            if response.status_code == 200:
                fng_data = response.json()
                if 'data' in fng_data and len(fng_data['data']) > 0:
                    latest_fng = fng_data['data'][0]
                    result = {
                        'value': int(latest_fng.get('value', 0)),
                        'classification': latest_fng.get('value_classification', '未知'),
                        'timestamp': latest_fng.get('timestamp', '未知'),
                        'time_until_update': latest_fng.get('time_until_update', '未知')
                    }
                    print(f"获取恐贪指数成功: {result['value']} ({result['classification']})")
                    return result
                else:
                    print("恐贪指数数据格式异常")
            else:
                print(f"恐贪指数API返回错误: {response.status_code}")
                
        except Exception as e:
            print(f"获取恐贪指数失败: {e}")
            
        return None
    
    def get_trending_coins(self) -> Optional[List[Dict[str, Any]]]:
        """
        获取热门币种
        
        Returns:
            Optional[List[Dict[str, Any]]]: 热门币种列表，失败时返回None
        """
        self._wait_for_rate_limit()
        
        url = f"{self.base_url}/search/trending"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            trending_coins = []
            
            for coin_data in data.get('coins', []):
                coin = coin_data.get('item', {})
                trending_coins.append({
                    'id': coin.get('id'),
                    'coin_id': coin.get('coin_id'),
                    'name': coin.get('name'),
                    'symbol': coin.get('symbol'),
                    'market_cap_rank': coin.get('market_cap_rank'),
                    'thumb': coin.get('thumb'),
                    'small': coin.get('small'),
                    'large': coin.get('large'),
                    'slug': coin.get('slug'),
                    'price_btc': coin.get('price_btc'),
                    'score': coin.get('score')
                })
            
            return trending_coins
            
        except Exception as e:
            print(f"❌ 获取热门币种失败: {e}")
            return None
    
    def get_major_coins_performance(self) -> Optional[List[Dict[str, Any]]]:
        """
        获取主流币种表现数据
        
        Returns:
            Optional[List[Dict[str, Any]]]: 主流币种表现数据，失败时返回None
        """
        self._wait_for_rate_limit()
        
        major_coins = ['bitcoin', 'ethereum', 'ripple', 'binancecoin', 'cardano', 'solana']
        url = f"{self.base_url}/coins/markets"
        params = {
            'vs_currency': 'usd',
            'ids': ','.join(major_coins),
            'order': 'market_cap_desc',
            'per_page': 6,
            'page': 1,
            'sparkline': 'false',
            'price_change_percentage': '24h'
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            coins_data = response.json()
            if coins_data:
                major_performance = []
                for coin in coins_data:
                    major_performance.append({
                        'id': coin.get('id'),
                        'symbol': coin.get('symbol'),
                        'name': coin.get('name'),
                        'current_price': coin.get('current_price', 0),
                        'price_change_24h': coin.get('price_change_percentage_24h', 0),
                        'market_cap': coin.get('market_cap', 0),
                        'total_volume': coin.get('total_volume', 0)
                    })
                print("获取主流币种表现数据成功")
                return major_performance
            else:
                print("主流币种数据格式异常")
                
        except Exception as e:
            print(f"获取主流币种表现失败: {e}")
            
        return None
    
    def get_market_overview(self, vs_currency: str = 'usd', per_page: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        获取市场概览
        
        Args:
            vs_currency: 对比货币
            per_page: 每页数量
            
        Returns:
            Optional[List[Dict[str, Any]]]: 市场概览数据，失败时返回None
        """
        self._wait_for_rate_limit()
        
        url = f"{self.base_url}/coins/markets"
        params = {
            'vs_currency': vs_currency,
            'order': 'market_cap_desc',
            'per_page': per_page,
            'page': 1,
            'sparkline': 'false'
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            market_overview = []
            
            for coin in data:
                market_overview.append({
                    'id': coin.get('id'),
                    'symbol': coin.get('symbol'),
                    'name': coin.get('name'),
                    'current_price': coin.get('current_price'),
                    'market_cap': coin.get('market_cap'),
                    'market_cap_rank': coin.get('market_cap_rank'),
                    'total_volume': coin.get('total_volume'),
                    'price_change_24h': coin.get('price_change_24h'),
                    'price_change_percentage_24h': coin.get('price_change_percentage_24h'),
                    'market_cap_change_24h': coin.get('market_cap_change_24h'),
                    'market_cap_change_percentage_24h': coin.get('market_cap_change_percentage_24h'),
                    'circulating_supply': coin.get('circulating_supply'),
                    'total_supply': coin.get('total_supply'),
                    'max_supply': coin.get('max_supply'),
                    'ath': coin.get('ath'),
                    'ath_change_percentage': coin.get('ath_change_percentage'),
                    'atl': coin.get('atl'),
                    'atl_change_percentage': coin.get('atl_change_percentage'),
                    'last_updated': coin.get('last_updated')
                })
            
            return market_overview
            
        except Exception as e:
            print(f"❌ 获取市场概览失败: {e}")
            return None
    
    def test_connectivity(self) -> bool:
        """
        测试API连通性
        
        Returns:
            bool: 连接是否成功
        """
        url = f"{self.base_url}/ping"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return True
            
        except Exception as e:
            print(f"❌ CoinGecko API连接测试失败: {e}")
            return False