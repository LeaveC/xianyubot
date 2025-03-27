"""
Agent基类模块
定义所有专家Agent的共同接口和基础功能
"""

from typing import List, Dict, Any, Optional
import concurrent.futures
from loguru import logger

from openai import OpenAI

# 创建线程池执行器，用于异步处理LLM调用
llm_executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)


class BaseAgent:
    """Agent基类，定义通用方法和接口"""

    def __init__(self, client: OpenAI, system_prompt: str, safety_filter):
        """
        初始化Agent
        
        Args:
            client: OpenAI API客户端
            system_prompt: 系统提示词
            safety_filter: 安全过滤函数
        """
        self.client = client
        self.system_prompt = system_prompt
        self.safety_filter = safety_filter

    def generate(self, user_msg: str, item_desc: str, context: str, bargain_count: int = 0) -> str:
        """
        生成回复的模板方法
        
        Args:
            user_msg: 用户消息
            item_desc: 商品描述
            context: 对话上下文
            bargain_count: 议价次数
            
        Returns:
            str: 生成的回复内容
        """
        messages = self._build_messages(user_msg, item_desc, context)
        response = self._call_llm(messages)
        return self.safety_filter(response)

    def _build_messages(self, user_msg: str, item_desc: str, context: str) -> List[Dict[str, str]]:
        """
        构建消息链
        
        Args:
            user_msg: 用户消息
            item_desc: 商品描述
            context: 对话上下文
            
        Returns:
            List[Dict[str, str]]: 消息链列表
        """
        return [
            {"role": "system", "content": f"【商品信息】{item_desc}\n【你与客户对话历史】{context}\n{self.system_prompt}"},
            {"role": "user", "content": user_msg}
        ]

    def _call_llm(self, messages: List[Dict], temperature: float = 0.4) -> str:
        """
        调用大模型生成回复
        
        Args:
            messages: 消息链
            temperature: 温度参数
            
        Returns:
            str: 生成的文本
        """
        # 定义实际执行的函数
        def _execute_llm_call():
            try:
                response = self.client.chat.completions.create(
                    model="qwen-max",  # 默认使用通义千问模型，可在子类中覆盖
                    messages=messages,
                    temperature=temperature,
                    max_tokens=500,
                    top_p=0.8
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"LLM调用失败: {e}")
                return "抱歉，系统繁忙，请稍后再试。"
                
        # 使用线程池提交任务并等待结果
        future = llm_executor.submit(_execute_llm_call)
        return future.result()  # 等待任务完成并获取结果 