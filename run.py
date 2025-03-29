#!/usr/bin/env python
"""
启动闲鱼机器人的主脚本
"""

import os
import sys

# 添加src目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
sys.path.insert(0, src_dir)

# 导入主模块
from src.main import main
import asyncio

if __name__ == "__main__":
    # 启动主程序
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程序被用户中断")
    except Exception as e:
        print(f"程序运行出错: {str(e)}") 