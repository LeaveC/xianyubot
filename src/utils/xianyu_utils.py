"""
闲鱼工具函数模块
提供生成签名、处理cookies等通用工具函数
"""

import json
import subprocess
from functools import partial
import os
import execjs
from loguru import logger
import asyncio
from playwright.async_api import async_playwright

# 修复execjs编码问题
subprocess.Popen = partial(subprocess.Popen, encoding="utf-8")

def load_js_module():
    """加载JS脚本文件"""
    try:
        # 获取当前脚本所在目录的上一级，即项目根目录
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        js_path = os.path.join(project_root, 'static', 'xianyu_js_version_2.js')
        
        # 检查文件是否存在
        if not os.path.exists(js_path):
            logger.error(f"JS文件不存在: {js_path}")
            raise FileNotFoundError(f"找不到JS文件: {js_path}")
            
        # 读取并编译JS文件
        with open(js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()
            
        return execjs.compile(js_content)
    except Exception as e:
        logger.error(f"加载JS模块失败: {str(e)}")
        raise

# 初始化JS模块
try:
    xianyu_js = load_js_module()
except Exception as e:
    logger.warning(f"初始化JS模块失败，部分功能可能不可用: {str(e)}")
    xianyu_js = None

def trans_cookies(cookies_str):
    """
    将cookies字符串转换为字典格式
    
    Args:
        cookies_str (str): Cookies字符串，格式如"key1=value1; key2=value2"
        
    Returns:
        dict: 转换后的cookies字典
    """
    cookies = dict()
    for i in cookies_str.split("; "):
        try:
            cookies[i.split('=')[0]] = '='.join(i.split('=')[1:])
        except:
            continue
    return cookies

async def get_login_cookies():
    """
    打开Firefox浏览器，访问闲鱼消息页面，等待用户登录，并获取登录cookies
    
    Returns:
        dict: 包含cookies和localStorage的字典
    """
    cookies_data = {}
    try:
        logger.info("启动Firefox浏览器获取闲鱼登录凭证")
        async with async_playwright() as p:
            # 启动Firefox浏览器
            browser = await p.firefox.launch(headless=False)
            
            # 创建新页面
            page = await browser.new_page()
            logger.info("正在打开闲鱼消息页面")
            
            # 访问闲鱼消息页面
            await page.goto("https://www.goofish.com/im")
            
            # 等待用户手动登录
            logger.info("请在打开的浏览器中手动登录闲鱼")
            logger.info("等待检测到登录状态...")
            
            # 等待登录成功的标识
            # 通常登录后会出现一些特定元素，这里我们检查登录后特有的cookies
            login_success = False
            max_wait_time = 300  # 最大等待时间5分钟
            start_time = asyncio.get_event_loop().time()
            
            while not login_success and (asyncio.get_event_loop().time() - start_time) < max_wait_time:
                # 获取当前cookies
                cookies = await page.context.cookies()
                
                # 检查是否有登录成功的标识cookies
                if any(cookie["name"] == "havana_lgc2_77" for cookie in cookies):
                    login_success = True
                    break
                
                # 等待2秒后再次检查
                await asyncio.sleep(2)
            
            if not login_success:
                logger.warning("等待登录超时，可能未成功登录")
                await browser.close()
                return None
            
            # 获取cookies
            cookies = await page.context.cookies()
            cookies_dict = {cookie["name"]: cookie["value"] for cookie in cookies}
            
            # 获取localStorage数据
            local_storage = await page.evaluate("() => JSON.stringify(localStorage)")
            local_storage_dict = json.loads(local_storage)
            
            # 构建返回数据
            cookies_data = {
                "cookies": cookies_dict,
                "localStorage": local_storage_dict
            }
            
            # 输出cookies字符串格式
            cookies_str = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])
            logger.info(f"成功获取登录cookies: {cookies_str[:100]}...")
            
            # 保存cookies数据到文件
            save_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'xianyu_cookies.json'))
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(cookies_data, f, ensure_ascii=False, indent=2)
            logger.info(f"登录凭证已保存到: {save_path}")
            
            # 关闭浏览器
            await browser.close()
            
    except Exception as e:
        logger.error(f"获取登录cookies时发生错误: {str(e)}")
        return None
    
    return cookies_data

def load_cookies():
    """
    从文件加载保存的cookies
    
    Returns:
        dict: 包含cookies和localStorage的字典，如果文件不存在则返回None
    """
    try:
        # 获取cookies文件路径
        cookies_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'xianyu_cookies.json'))
        
        # 检查文件是否存在
        if not os.path.exists(cookies_path):
            logger.warning(f"Cookies文件不存在: {cookies_path}")
            return None
        
        # 读取cookies文件
        with open(cookies_path, 'r', encoding='utf-8') as f:
            cookies_data = json.load(f)
        
        logger.info("成功加载登录凭证")
        return cookies_data
    
    except Exception as e:
        logger.error(f"加载cookies时发生错误: {str(e)}")
        return None

def generate_mid():
    """生成消息ID"""
    if not xianyu_js:
        logger.error("JS模块未初始化，无法生成mid")
        return None
    return xianyu_js.call('generate_mid')

def generate_uuid():
    """生成UUID"""
    if not xianyu_js:
        logger.error("JS模块未初始化，无法生成uuid")
        return None
    return xianyu_js.call('generate_uuid')

def generate_device_id(user_id):
    """
    生成设备ID
    
    Args:
        user_id (str): 用户ID
        
    Returns:
        str: 设备ID
    """
    if not xianyu_js:
        logger.error("JS模块未初始化，无法生成device_id")
        return None
    return xianyu_js.call('generate_device_id', user_id)

def generate_sign(t, token, data):
    """
    生成API请求签名
    
    Args:
        t (str): 时间戳
        token (str): 用户token
        data (str): 请求数据
        
    Returns:
        str: 生成的签名
    """
    if not xianyu_js:
        logger.error("JS模块未初始化，无法生成sign")
        return None
    return xianyu_js.call('generate_sign', t, token, data)

def decrypt(data):
    """
    解密数据
    
    Args:
        data (str): 加密数据
        
    Returns:
        str: 解密后的数据
    """
    if not xianyu_js:
        logger.error("JS模块未初始化，无法解密数据")
        return None
    return xianyu_js.call('decrypt', data) 