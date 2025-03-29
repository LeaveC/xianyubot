"""
闲鱼工具函数模块 - 纯Python实现版
提供生成签名、处理cookies等通用工具函数
"""

import json
import subprocess
from functools import partial
import os
import sys
import platform
from loguru import logger
import asyncio
from playwright.async_api import async_playwright
import re
import shutil

# 检测操作系统类型
IS_WINDOWS = platform.system() == 'Windows'

# 修复subprocess编码问题 - 为Windows系统专门设置
if IS_WINDOWS:
    # Windows下需要额外设置编码为utf-8，避免默认GBK编码导致的问题
    import subprocess as _subprocess
    _orig_popen = _subprocess.Popen
    
    def _popen_utf8(*args, **kwargs):
        # 始终指定UTF-8编码，防止使用GBK
        kwargs['encoding'] = 'utf-8'
        # 设置shell参数
        kwargs['shell'] = True
        # 确保stderr和stdout都使用管道，便于捕获
        kwargs['stderr'] = _subprocess.PIPE
        kwargs['stdout'] = _subprocess.PIPE
        return _orig_popen(*args, **kwargs)
    
    _subprocess.Popen = _popen_utf8
    logger.info("检测到Windows系统，已应用Windows特定的subprocess UTF-8编码配置")
else:
    # 非Windows系统通常默认使用UTF-8编码
    subprocess.Popen = partial(subprocess.Popen, encoding="utf-8")
    logger.info("检测到非Windows系统，应用标准subprocess编码配置")

# 纯Python实现的函数
def _py_generate_mid():
    """生成消息ID的纯Python实现"""
    import random
    import time
    return f"{int(1000 * random.random())}{int(time.time() * 1000)} 0"

def _py_generate_uuid():
    """生成UUID的纯Python实现"""
    import time
    return f"-{int(time.time() * 1000)}1"

def _py_generate_device_id(user_id):
    """生成设备ID的纯Python实现"""
    import random
    import time
    import uuid
    
    # 尝试使用uuid模块生成一个基于用户ID的确定性UUID
    try:
        device_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"xianyubot-{user_id}"))
        return f"{device_id}-{user_id}"
    except:
        # 回退到简单实现
        random_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        uuid_parts = []
        for i in range(36):
            if i in [8, 13, 18, 23]:
                uuid_parts.append("-")
            elif i == 14:
                uuid_parts.append("4")
            elif i == 19:
                random_idx = random.randint(0, 15)
                uuid_parts.append(random_chars[8 + random_idx])
            else:
                uuid_parts.append(random_chars[random.randint(0, 61)])
        return "".join(uuid_parts) + "-" + str(user_id)

def _py_generate_sign(t, token, data):
    """
    生成API请求签名的纯Python实现
    
    Args:
        t (str): 时间戳
        token (str): 用户token
        data (str): 请求数据
        
    Returns:
        str: MD5签名
    """
    import hashlib
    msg = f"{token}&{t}&34839810&{data}"
    return hashlib.md5(msg.encode('utf-8')).hexdigest()

def generate_mid():
    """生成消息ID"""
    return _py_generate_mid()

def generate_uuid():
    """生成UUID"""
    return _py_generate_uuid()

def generate_device_id(user_id):
    """
    生成设备ID
    
    Args:
        user_id (str): 用户ID
        
    Returns:
        str: 设备ID
    """
    return _py_generate_device_id(user_id)

def generate_sign(t, token, data):
    """
    生成API请求签名
    
    Args:
        t (str): 时间戳
        token (str): 用户token
        data (str): 请求数据
        
    Returns:
        str: 签名
    """
    return _py_generate_sign(t, token, data)

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

def cookies_dict_to_str(cookies_dict):
    """
    将cookies字典转换为字符串格式
    
    Args:
        cookies_dict (dict): Cookies字典
        
    Returns:
        str: 转换后的cookies字符串
    """
    return "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])

async def get_login_cookies():
    """
    打开Firefox浏览器，访问闲鱼消息页面，等待用户登录，并获取登录cookies
    如果存在已保存的浏览器状态，将尝试恢复该状态
    
    Returns:
        dict: 包含cookies和localStorage的字典
    """
    cookies_data = {}
    # 获取状态文件路径
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
    
    # 确保data目录存在
    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir)
            logger.info(f"创建数据目录: {data_dir}")
        except Exception as e:
            logger.error(f"创建数据目录失败: {e}")
    
    state_path = os.path.join(data_dir, 'playwright_state.json')
    
    try:
        # 根据操作系统选择浏览器
        browser_type = 'firefox'
        if IS_WINDOWS:
            # Windows下默认使用Chromium，可能更稳定
            browser_type = 'chromium'
            logger.info(f"Windows系统使用 {browser_type} 浏览器")
        else:
            logger.info(f"非Windows系统使用 {browser_type} 浏览器")
            
        logger.info(f"启动{browser_type}浏览器获取闲鱼登录凭证")
        async with async_playwright() as p:
            # 创建浏览器上下文选项
            context_options = {}
            
            # 检查是否存在已保存的状态
            if os.path.exists(state_path):
                logger.info("找到已保存的浏览器状态，尝试恢复...")
                try:
                    with open(state_path, 'r', encoding='utf-8') as f:
                        storage_state = json.load(f)
                    context_options["storage_state"] = storage_state
                except Exception as e:
                    logger.error(f"加载浏览器状态失败: {e}")
            
            # 启动选择的浏览器
            browser_launcher = getattr(p, browser_type)
            browser = await browser_launcher.launch(headless=False)
            
            # 创建新的浏览器上下文，并应用已保存的状态(如果有)
            context = await browser.new_context(**context_options)
            
            # 创建新页面
            page = await context.new_page()
            logger.info("正在打开闲鱼消息页面")
            
            # 访问闲鱼消息页面
            await page.goto("https://www.goofish.com/im")
            
            # 检查是否已登录
            already_logged_in = False
            try:
                # 等待5秒看是否有登录成功的标识
                cookies = await context.cookies()
                if any(cookie["name"] == "havana_lgc2_77" for cookie in cookies):
                    logger.info("通过已保存状态成功恢复登录")
                    already_logged_in = True
            except Exception:
                already_logged_in = False
            
            # 如果没有登录，则等待用户手动登录
            if not already_logged_in:
                logger.info("未检测到登录状态，请在打开的浏览器中手动登录闲鱼")
                logger.info("等待检测到登录状态...")
                
                # 等待登录成功的标识
                login_success = False
                max_wait_time = 300  # 最大等待时间5分钟
                start_time = asyncio.get_event_loop().time()
                
                while not login_success and (asyncio.get_event_loop().time() - start_time) < max_wait_time:
                    # 获取当前cookies
                    cookies = await context.cookies()
                    
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
            
            # 获取cookies和localStorage
            cookies = await context.cookies()
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
            cookies_str = cookies_dict_to_str(cookies_dict)
            logger.info(f"成功获取登录cookies: {cookies_str[:100]}...")
            
            # 保存cookies数据到文件
            save_path = os.path.join(data_dir, 'xianyu_cookies.json')
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(cookies_data, f, ensure_ascii=False, indent=2)
            logger.info(f"登录凭证已保存到: {save_path}")
            
            # 保存浏览器状态到文件
            try:
                storage_state = await context.storage_state()
                with open(state_path, 'w', encoding='utf-8') as f:
                    json.dump(storage_state, f, ensure_ascii=False, indent=2)
                logger.info(f"浏览器状态已保存到: {state_path}")
            except Exception as e:
                logger.error(f"保存浏览器状态失败: {e}")
            
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
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
        cookies_path = os.path.join(data_dir, 'xianyu_cookies.json')
        
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

def _py_decrypt(data):
    """
    解密数据的纯Python实现
    
    Args:
        data (str): base64编码的数据
        
    Returns:
        str: 解密后的JSON字符串
    """
    try:
        import base64
        import json
        import struct

        # 尝试导入 msgpack
        msgpack_available = False
        try:
            from msgpack import unpackb
            msgpack_available = True
        except ImportError:
            logger.error("缺少 'msgpack' 库，无法进行 msgpack 解码。请尝试运行 'pip install msgpack' 安装。")

        # 首先尝试标准base64解码
        try:
            decoded = base64.b64decode(data)
            result = decoded.decode('utf-8')
            json.loads(result)  # 验证是否为有效JSON
            logger.info("使用标准base64+UTF-8解码成功")
            return result
        except Exception as e:
            logger.debug(f"标准base64+UTF-8解码尝试失败: {e}")

        # 如果 msgpack 可用，尝试使用 msgpack 解包
        if msgpack_available:
            try:
                # 确保 decoded 变量存在 (来自上面的 try block)
                if 'decoded' not in locals():
                     decoded = base64.b64decode(data) # 如果第一次 base64 解码失败，这里可能需要重新解码

                unpacked = unpackb(decoded, raw=False, strict_map_key=False)
                logger.info("使用msgpack解包成功")
                return json.dumps(unpacked)
            except Exception as e:
                logger.debug(f"msgpack解包尝试失败: {e}")
        else:
            logger.debug("跳过 msgpack 解码，因为库不可用。")

        # 如果以上方法都失败，尝试通用解码方式 (提取可打印字符)
        logger.warning("标准解码和 msgpack 解码均失败，尝试提取可打印ASCII字符作为后备方案。")
        # 确保 decoded 变量存在
        if 'decoded' not in locals():
            try:
                decoded = base64.b64decode(data)
            except Exception as decode_err:
                logger.error(f"最终尝试Base64解码也失败: {decode_err}")
                return json.dumps({
                    "success": False,
                    "message": f"无法进行Base64解码: {decode_err}",
                    "base64Length": len(data)
                })

        printable_chars = []
        for byte in decoded:
            if 32 <= byte <= 126:  # 可打印ASCII字符
                printable_chars.append(chr(byte))

        if printable_chars:
            result = {"extractedText": ''.join(printable_chars)}
            logger.info(f"后备方案：提取到可打印字符: {result}")
            return json.dumps(result)

        logger.error("所有解码方法均失败，无法解析数据。")
        return json.dumps({
            "success": False,
            "message": "无法解码消息，尝试了UTF-8和msgpack（如果可用）",
            "base64Length": len(data)
        })
    except Exception as e:
        logger.error(f"Python解密数据时发生意外错误: {e}")
        return json.dumps({"error": f"解密失败: {str(e)}"})

def decrypt(data):
    """
    解密数据
    
    Args:
        data (str): 加密的数据
        
    Returns:
        str: 解密后的数据
    """
    logger.info("使用Python实现解密数据")
    return _py_decrypt(data)