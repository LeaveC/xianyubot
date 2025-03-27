"""
闲鱼API接口模块
提供闲鱼相关API的封装，如获取token、商品信息等
"""

import json
import time
import requests
from loguru import logger

from ..utils.xianyu_utils import generate_sign, generate_device_id


class XianyuApi:
    """闲鱼API接口类"""
    
    def __init__(self):
        """初始化API接口"""
        self.base_url = 'https://h5api.m.goofish.com/h5/'
        self.headers = {
            'accept': 'application/json',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cache-control': 'no-cache',
            'origin': 'https://www.goofish.com',
            'pragma': 'no-cache',
            'priority': 'u=1, i',
            'referer': 'https://www.goofish.com/',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36',
        }
        
    def _build_params(self, api, t, sign):
        """
        构建通用请求参数
        
        Args:
            api (str): API路径
            t (str): 时间戳
            sign (str): 签名
            
        Returns:
            dict: 请求参数字典
        """
        return {
            'jsv': '2.7.2',
            'appKey': '34839810',
            't': t,
            'sign': sign,
            'v': '1.0',
            'type': 'originaljson',
            'accountSite': 'xianyu',
            'dataType': 'json',
            'timeout': '20000',
            'api': api,
            'sessionOption': 'AutoLoginOnly',
            'spm_cnt': 'a21ybx.im.0.0',
        }
    
    def get_token(self, cookies, device_id=None):
        """
        获取闲鱼聊天token
        
        Args:
            cookies (dict): Cookies字典
            device_id (str, optional): 设备ID，若为None则自动生成
            
        Returns:
            dict: API响应的JSON数据
        """
        # 如果没有提供设备ID，则尝试从cookies中获取unb并生成设备ID
        if not device_id and 'unb' in cookies:
            device_id = generate_device_id(cookies['unb'])
        
        if not device_id:
            logger.error("无法获取设备ID，请确保cookies中包含unb字段或手动提供设备ID")
            return None
            
        api = 'mtop.taobao.idlemessage.pc.login.token'
        t = str(int(time.time()) * 1000)
        data_val = f'{{"appKey":"444e9908a51d1cb236a27862abc769c9","deviceId":"{device_id}"}}'
        
        # 获取token并生成签名
        try:
            token = cookies['_m_h5_tk'].split('_')[0]
        except (KeyError, IndexError):
            logger.error("无法从cookies中获取_m_h5_tk，请检查cookies是否有效")
            return None
            
        sign = generate_sign(t, token, data_val)
        
        # 构建请求
        params = self._build_params(api, t, sign)
        data = {'data': data_val}
        
        # 发送请求
        url = f"{self.base_url}{api}/1.0/"
        try:
            response = requests.post(url, params=params, cookies=cookies, headers=self.headers, data=data)
            res_json = response.json()
            return res_json
        except Exception as e:
            logger.error(f"获取token时出错: {e}")
            return None

    def get_item_info(self, cookies, item_id):
        """
        获取商品信息
        
        Args:
            cookies (dict): Cookies字典
            item_id (str): 商品ID
            
        Returns:
            dict: 商品信息的JSON数据
        """
        api = 'mtop.taobao.idle.pc.detail'
        t = str(int(time.time()) * 1000)
        data_val = f'{{"itemId":"{item_id}"}}'
        
        try:
            token = cookies['_m_h5_tk'].split('_')[0]
        except (KeyError, IndexError):
            logger.error("无法从cookies中获取_m_h5_tk，请检查cookies是否有效")
            return None
            
        sign = generate_sign(t, token, data_val)
        
        params = self._build_params(api, t, sign)
        data = {'data': data_val}
        
        url = f"{self.base_url}{api}/1.0/"
        try:
            response = requests.post(url, params=params, cookies=cookies, headers=self.headers, data=data)
            res_json = response.json()
            return res_json
        except Exception as e:
            logger.error(f"获取商品信息时出错: {e}")
            return None 