import asyncio
import os
import platform
import argparse
from loguru import logger
from dotenv import load_dotenv

from api.xianyu_websocket import XianyuLive
from agents.expert_agents import XianyuReplyBot
from core.context_manager import ChatContextManager
from utils.xianyu_utils import get_login_cookies, load_cookies, trans_cookies, cookies_dict_to_str

# 检测操作系统类型
IS_WINDOWS = platform.system() == 'Windows'

async def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='闲鱼机器人')
    parser.add_argument('--login', action='store_true', help='强制使用浏览器获取闲鱼登录凭证')
    args = parser.parse_args()
    
    # 加载环境变量
    load_dotenv()
    
    # 如果指定了强制登录选项，则打开浏览器获取登录凭证
    if args.login:
        logger.info("准备使用浏览器获取闲鱼登录凭证")
        cookies_data = await get_login_cookies()
        if not cookies_data:
            logger.error("获取登录凭证失败")
            return
        logger.info("成功获取登录凭证，继续启动机器人")
    
    # 尝试从文件加载cookies
    cookies_data = load_cookies()
    cookies_str = None
    
    if cookies_data and "cookies" in cookies_data:
        cookies_dict = cookies_data["cookies"]
        cookies_str = cookies_dict_to_str(cookies_dict)
        logger.info("成功从文件加载登录凭证")
    
    # 如果没有有效的cookies，自动打开浏览器获取
    if not cookies_str:
        logger.info("未找到有效的闲鱼cookies，自动启动浏览器获取登录凭证")
        cookies_data = await get_login_cookies()
        if not cookies_data or "cookies" not in cookies_data:
            logger.error("获取登录凭证失败，请重新运行程序")
            return
        
        cookies_dict = cookies_data["cookies"]
        cookies_str = cookies_dict_to_str(cookies_dict)
        logger.info("成功获取新的登录凭证")
    
    # 初始化回复机器人
    bot = XianyuReplyBot()
    
    # 初始化websocket连接
    xianyu_live = XianyuLive(cookies_str, bot)
    
    # 启动主循环
    await xianyu_live.main()

if __name__ == "__main__":
    try:
        # 在Windows上设置默认事件循环策略，解决asyncio兼容性问题
        if IS_WINDOWS:
            # Windows平台使用SelectorEventLoop避免ProactorEventLoop的问题
            # 解决Windows上常见的"Event loop is closed"错误
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            logger.info("Windows平台: 设置了WindowsSelectorEventLoopPolicy")
            
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序运行出错: {str(e)}")