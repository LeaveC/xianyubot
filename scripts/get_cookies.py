#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
闲鱼登录凭证获取脚本
使用Playwright自动打开Firefox浏览器，让用户在浏览器中手动登录闲鱼，获取登录凭证
"""

import asyncio
import json
import os
import sys

# 添加项目根目录到模块搜索路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.xianyu_utils import get_login_cookies
from loguru import logger

async def main():
    """获取闲鱼登录凭证的主函数"""
    try:
        logger.info("开始获取闲鱼登录凭证")
        
        # 获取登录凭证
        cookies_data = await get_login_cookies()
        
        if not cookies_data:
            logger.error("获取登录凭证失败")
            return 1
        
        logger.info("成功获取闲鱼登录凭证")
        
        # 打印登录状态检查提示
        if "cookies" in cookies_data and "havana_lgc2_77" in cookies_data["cookies"]:
            logger.info("登录状态正常，凭证有效")
        else:
            logger.warning("可能未正确获取登录状态，请检查cookies文件")
        
        return 0
    
    except Exception as e:
        logger.error(f"获取闲鱼登录凭证时发生错误: {str(e)}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 