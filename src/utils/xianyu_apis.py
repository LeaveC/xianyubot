"""
闲鱼API工具模块，提供了与闲鱼API交互的方法
"""

import requests
import json
import time
from loguru import logger
from utils.xianyu_utils import generate_device_id, generate_sign


class XianyuApis:
    """闲鱼API类，提供与闲鱼API交互的功能"""
    
    def __init__(self):
        """初始化闲鱼API类"""
        self.url = 'https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/'
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
    
    def get_token(self, cookies, device_id):
        """
        获取WebSocket连接所需的token
        
        Args:
            cookies (dict): Cookies字典
            device_id (str): 设备ID
            
        Returns:
            dict: 包含token的响应数据
        """
        try:
            params = {
                'jsv': '2.7.2',
                'appKey': '34839810',
                't': str(int(time.time() * 1000)),
                'sign': '',
                'v': '1.0',
                'type': 'originaljson',
                'accountSite': 'xianyu',
                'dataType': 'json',
                'timeout': '20000',
                'api': 'mtop.taobao.idlemessage.pc.login.token',
                'sessionOption': 'AutoLoginOnly',
                'spm_cnt': 'a21ybx.im.0.0',
            }
            
            data_val = '{"appKey":"444e9908a51d1cb236a27862abc769c9","deviceId":"' + device_id + '"}'
            data = {
                'data': data_val,
            }
            
            # 检查cookies中是否存在token字段
            if '_m_h5_tk' not in cookies:
                logger.error("获取token失败: cookies中缺少_m_h5_tk字段")
                return {"ret": ["FAIL_SYS_TOKEN_EMPTY::令牌为空"], "data": {}, "success": False}
            
            token = cookies['_m_h5_tk'].split('_')[0]
            sign = generate_sign(params['t'], token, data_val)
            params['sign'] = sign
            
            response = requests.post(self.url, params=params, cookies=cookies, headers=self.headers, data=data)
            
            # 检查响应状态
            if response.status_code != 200:
                logger.error(f"获取token失败，状态码: {response.status_code}")
                return {"ret": [f"HTTP_ERROR::{response.status_code}"], "data": {}, "success": False}
                
            # 解析响应
            res_json = response.json()
            
            # 检查token是否过期
            if "ret" in res_json and isinstance(res_json["ret"], list) and len(res_json["ret"]) > 0:
                error_msg = res_json["ret"][0]
                logger.warning(f"Token API返回错误: {error_msg}")
                
                # 常见的token过期错误代码
                token_expired_keywords = [
                    "TOKEN_EMPTY", "TOKEN_EXPIRED", "SESSION_EXPIRED", "SID_INVALID", 
                    "FAIL_SYS_TOKEN_EXOIRED", "FAIL_SYS_TOKEN_EMPTY"
                ]
                
                # 如果是token过期相关错误，添加明确的"令牌过期"标记
                if any(keyword in error_msg for keyword in token_expired_keywords):
                    res_json["ret"][0] += "::令牌过期"
                    logger.error(f"检测到token已过期: {error_msg}")
            
            return res_json
            
        except Exception as e:
            logger.error(f"获取token时发生错误: {str(e)}")
            return {"ret": [f"EXCEPTION::{str(e)}"], "data": {}, "success": False}
            
    def get_item_info(self, item_id, cookies):
        """
        获取商品信息
        
        Args:
            item_id (str): 商品ID
            cookies (dict): Cookies字典
            
        Returns:
            dict: 商品信息
        """
        try:
            url = f"https://h5api.m.goofish.com/h5/mtop.taobao.idle.pc.detail/1.0/"
            
            # 准备请求头部
            headers = self.headers.copy()
            # 添加Cookie
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            headers["Cookie"] = cookie_str
            
            # 准备请求参数
            params = {
                'jsv': '2.6.1',
                'appKey': '12574478',
                't': int(time.time() * 1000),
                'sign': '1',
                'v': '1.0',
                'type': 'originaljson',
                'dataType': 'json'
            }
            
            # 准备请求数据
            data = {
                'itemId': item_id
            }
            
            # 发送请求
            response = requests.post(url, headers=headers, params=params, json=data)
            
            # 检查响应状态
            if response.status_code != 200:
                logger.error(f"获取商品信息失败，状态码: {response.status_code}")
                return None
                
            # 解析响应
            result = response.json()
            if result.get("code") != 200:
                logger.error(f"获取商品信息失败，错误码: {result.get('code')}, 错误信息: {result.get('msg')}")
                return None
                
            # 返回商品信息
            return result.get("data", {})
            
        except Exception as e:
            logger.error(f"获取商品信息时发生错误: {str(e)}")
            return None 