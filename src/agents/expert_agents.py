"""
专家Agent模块
实现各种专业领域的Agent，如价格专家、技术专家等
"""

from typing import Dict, List, Any, Optional
import re
from loguru import logger

from .base import BaseAgent


class PriceAgent(BaseAgent):
    """议价处理Agent"""

    def generate(self, user_msg: str, item_desc: str, context: str, bargain_count: int=0) -> str:
        """
        生成议价回复
        
        Args:
            user_msg: 用户消息
            item_desc: 商品描述
            context: 对话上下文
            bargain_count: 议价次数
            
        Returns:
            str: 生成的回复
        """
        # 根据议价次数动态调整温度
        dynamic_temp = self._calc_temperature(bargain_count)
        
        # 构建消息，添加议价轮次信息
        messages = self._build_messages(user_msg, item_desc, context)
        messages[0]['content'] += f"\n▲当前议价轮次：{bargain_count}"
        
        # 调用LLM生成回复
        def _execute_llm_call():
            try:
                response = self.client.chat.completions.create(
                    model="qwen-max",
                    messages=messages,
                    temperature=dynamic_temp,  # 动态温度
                    max_tokens=500,
                    top_p=0.8
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"议价Agent调用失败: {e}")
                return "抱歉，系统繁忙，请稍后再试。"
                
        # 使用线程池执行
        from .base import llm_executor
        future = llm_executor.submit(_execute_llm_call)
        result = future.result()
        
        return self.safety_filter(result)
        
    def _calc_temperature(self, bargain_count: int) -> float:
        """
        根据议价次数计算温度参数
        
        Args:
            bargain_count: 议价次数
            
        Returns:
            float: 计算后的温度参数
        """
        # 议价次数越多，温度越高，回复越多样化
        base_temp = 0.3
        increment = min(bargain_count * 0.1, 0.5)  # 最大增加0.5
        return base_temp + increment


class TechAgent(BaseAgent):
    """技术专家Agent"""
    
    def generate(self, user_msg: str, item_desc: str, context: str, bargain_count: int=0) -> str:
        """
        生成技术回复
        
        Args:
            user_msg: 用户消息
            item_desc: 商品描述
            context: 对话上下文
            bargain_count: 议价次数（对技术专家无影响）
            
        Returns:
            str: 生成的回复
        """
        # 构建消息，技术性回复使用较低温度
        messages = self._build_messages(user_msg, item_desc, context)
        
        # 技术回复使用较低的温度，确保一致性和准确性
        def _execute_llm_call():
            try:
                response = self.client.chat.completions.create(
                    model="qwen-max",
                    messages=messages,
                    temperature=0.2,  # 低温度，更确定性的回答
                    max_tokens=800,  # 技术回复可能需要更长的内容
                    top_p=0.8
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"技术Agent调用失败: {e}")
                return "抱歉，系统繁忙，请稍后再试。"
                
        # 使用线程池执行
        from .base import llm_executor
        future = llm_executor.submit(_execute_llm_call)
        result = future.result()
        
        return self.safety_filter(result)


class ClassifyAgent(BaseAgent):
    """意图分类Agent"""
    
    def generate(self, **args) -> str:
        """
        生成意图分类
        
        Returns:
            str: 分类结果，如"price"、"tech"或"default"
        """
        # 修改消息以明确要求分类
        user_msg = args.get('user_msg', '')
        item_desc = args.get('item_desc', '')
        context = args.get('context', '')
        
        # 构建专门用于分类的消息
        messages = [
            {"role": "system", "content": f"【商品信息】{item_desc}\n【你与客户对话历史】{context}\n{self.system_prompt}\n\n请判断以下用户消息的意图类别：\n1. 如果是询问价格、议价、优惠、降价等，返回'price'\n2. 如果是询问商品技术细节、参数、功能、使用方法等，返回'tech'\n3. 其他情况返回'default'\n只需要返回对应的分类标签，不要返回其他内容。"},
            {"role": "user", "content": user_msg}
        ]
        
        # 调用LLM进行分类
        def _execute_llm_call():
            try:
                response = self.client.chat.completions.create(
                    model="qwen-max",
                    messages=messages,
                    temperature=0.1,  # 很低的温度，确保一致性
                    max_tokens=10,  # 分类只需要很短的输出
                    top_p=0.8
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"分类Agent调用失败: {e}")
                return "default"  # 出错时返回默认分类
        
        # 使用线程池执行
        from .base import llm_executor
        future = llm_executor.submit(_execute_llm_call)
        intent = future.result()
        
        # 清理并规范化输出
        intent = intent.strip().lower()
        
        # 尝试从输出中提取意图标签
        if "price" in intent or "价格" in intent:
            return "price"
        elif "tech" in intent or "技术" in intent:
            return "tech"
        else:
            return "default"


class DefaultAgent(BaseAgent):
    """默认回复Agent"""
    
    def _call_llm(self, messages: List[Dict], *args) -> str:
        """
        调用LLM生成默认回复
        
        Args:
            messages: 消息链
            
        Returns:
            str: 生成的文本
        """
        # 定义执行函数
        def _execute_llm_call():
            try:
                response = self.client.chat.completions.create(
                    model="qwen-max",
                    messages=messages,
                    temperature=0.7,  # 默认回复使用较高温度，增加多样性
                    max_tokens=400,
                    top_p=0.9
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"默认Agent调用失败: {e}")
                return "您好，有什么我可以帮您的吗？"
                
        # 使用线程池执行
        from .base import llm_executor
        future = llm_executor.submit(_execute_llm_call)
        return future.result()


class XianyuReplyBot:
    """闲鱼回复机器人，整合多个专家Agent"""
    
    def __init__(self):
        """初始化闲鱼回复机器人"""
        # 创建OpenAI客户端
        from openai import OpenAI
        import os
        import time
        
        # 获取API设置
        api_key = os.getenv("OPENAI_API_KEY")
        api_base = os.getenv("OPENAI_BASE_URL")
        
        # 创建OpenAI客户端
        client = OpenAI(
            api_key=api_key,
            base_url=api_base
        )
        
        # 定义安全过滤函数
        def safety_filter(text):
            """简单的安全过滤函数，可以根据需要扩展"""
            blocked_phrases = ["微信", "QQ", "支付宝", "银行卡", "线下"]
            return "[安全提醒]请通过平台沟通" if any(p in text for p in blocked_phrases) else text
        
        # 加载统一提示词
        try:
            prompt_path = os.path.join("xianyubot", "prompts", "unified_prompt.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                unified_prompt = f.read()
                logger.info(f"已加载统一提示词，长度: {len(unified_prompt)} 字符")
        except Exception as e:
            logger.error(f"加载统一提示词时出错: {e}")
            try:
                # 尝试另一个路径
                prompt_path = os.path.join("prompts", "unified_prompt.txt")
                with open(prompt_path, "r", encoding="utf-8") as f:
                    unified_prompt = f.read()
                    logger.info(f"已加载统一提示词，长度: {len(unified_prompt)} 字符")
            except Exception as e2:
                logger.error(f"备用路径加载统一提示词时出错: {e2}")
                # 提供一个后备提示词
                unified_prompt = "你是闲鱼平台上卖家的智能助手，请帮助卖家回复买家的询问，保持礼貌和专业。"
        
        # 初始化Agent
        self.agent = BaseAgent(client, unified_prompt, safety_filter)
        
        # 兼容性处理，保留last_intent属性但始终设为'default'
        self.last_intent = 'default'
        
        # 添加消息去重机制
        self.last_messages = {}  # 格式: {user_id: {"msg": "上一条消息", "time": 时间戳, "reply": "回复内容"}}
        self.duplication_window = 20  # 20秒内相同消息视为重复
        self.system_notices = [
            "你已发货", "发来一条新消息", "已付款", "准备发货", "已下单", 
            "已经付款", "买家留言", "快递信息", "物流更新", "发货提醒", 
            "系统通知", "已收货", "已评价", "已退款", "订单更新"
        ]
    
    def generate_reply(self, user_msg: str, item_desc: str, context: Optional[str] = None, bargain_count: int = 0) -> str:
        """
        生成回复
        
        Args:
            user_msg: 用户消息
            item_desc: 商品描述
            context: 对话上下文
            bargain_count: 议价次数
            
        Returns:
            str: 生成的回复
        """
        # 消息内容和环境处理
        if user_msg is None or user_msg.strip() == "":
            logger.warning("收到空消息，返回默认回复")
            return "您好，有什么我可以帮您的吗？"
            
        # 如果未提供上下文，则创建一个空上下文
        if context is None or not isinstance(context, str):
            context = ""
        
        # 消息去重检查
        import time
        current_time = time.time()
        user_id = self._extract_user_id_from_context(context)
        
        # 检查是否为系统通知类消息或可能在短时间内出现的重复消息
        is_system_notice = any(notice in user_msg for notice in self.system_notices)
        
        # 检查10秒内是否有重复消息（对所有消息都检查）
        if user_id in self.last_messages:
            last_record = self.last_messages[user_id]
            time_diff = current_time - last_record.get("time", 0)
            
            # 条件1: 完全相同的消息在短时间内重复
            if last_record.get("msg") == user_msg and time_diff < self.duplication_window:
                logger.info(f"检测到{time_diff:.2f}秒内的完全相同消息，复用上一次回复")
                return last_record.get("reply", "收到您的消息，请问还有什么可以帮您的吗？")
            
            # 条件2: 系统通知类消息在短时间内出现
            if is_system_notice and time_diff < self.duplication_window:
                logger.info(f"检测到{time_diff:.2f}秒内的系统通知类消息，使用简短回复")
                reply = "好的，收到！如有问题随时联系我~"
                self.last_messages[user_id] = {
                    "msg": user_msg,
                    "time": current_time,
                    "reply": reply
                }
                return reply
        
        # 使用统一的Agent处理所有消息
        messages = [
            {"role": "system", "content": f"【商品信息】{item_desc if item_desc else 'unknown_item'}\n【你与客户对话历史】{context}\n【议价次数】{bargain_count}\n{self.agent.system_prompt}"},
            {"role": "user", "content": user_msg}
        ]
        
        # 调用模型生成回复
        def _execute_llm_call():
            try:
                response = self.agent.client.chat.completions.create(
                    model="qwen-max",
                    messages=messages,
                    temperature=0.4 + min(bargain_count * 0.05, 0.3),  # 随议价次数略微增加温度
                    max_tokens=500,
                    top_p=0.8
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"模型调用失败: {e}")
                return "抱歉，系统繁忙，请稍后再试。"
        
        try:
            # 使用线程池执行
            from .base import llm_executor
            future = llm_executor.submit(_execute_llm_call)
            reply = future.result()
            
            # 安全过滤
            reply = self.agent.safety_filter(reply)
        except Exception as e:
            logger.error(f"生成回复过程中出错: {e}")
            reply = "您好，有什么我可以帮您的吗？"
        
        # 判断是否为价格相关回复，用于保持议价次数增加的逻辑
        price_keywords = ["价格", "优惠", "便宜", "贵", "元", "折扣", "价钱", "多少钱"]
        if any(keyword in user_msg for keyword in price_keywords) or any(keyword in reply for keyword in price_keywords):
            self.last_intent = 'price'
        else:
            self.last_intent = 'default'
        
        # 更新最后回复记录
        self.last_messages[user_id] = {
            "msg": user_msg,
            "time": current_time,
            "reply": reply
        }
        
        logger.debug(f"生成回复: {reply}")
        return reply
        
    def _extract_user_id_from_context(self, context: str) -> str:
        """从上下文中提取用户ID"""
        import re
        if not isinstance(context, str):
            return "unknown_user"
            
        # 尝试多种可能的格式匹配用户ID
        patterns = [
            r'user: (\d+)',
            r'user[:\s]+(\w+)',
            r'用户[:\s]+(\w+)',
            r'买家[:\s]+(\w+)',
            r'send_user_id[:\s]+(\w+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, context)
            if match:
                return match.group(1)
        
        # 如果找不到任何匹配，返回上下文的哈希值作为用户ID
        import hashlib
        context_hash = hashlib.md5(context.encode('utf-8')).hexdigest()[:8]
        return f"user_{context_hash}" 