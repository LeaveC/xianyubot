"""
闲鱼WebSocket连接模块
提供与闲鱼WebSocket服务器的连接和消息处理功能
"""

import asyncio
import base64
import json
import time
from typing import Callable, Dict, Optional
import websockets
from loguru import logger
import concurrent.futures
from queue import Queue
from threading import Thread
import os

from utils.xianyu_utils import generate_mid, generate_uuid, trans_cookies, generate_device_id, decrypt, get_login_cookies, cookies_dict_to_str
from utils.xianyu_apis import XianyuApis
from core.context_manager import ChatContextManager


class XianyuWebSocket:
    """闲鱼WebSocket客户端类"""
    
    def __init__(self, cookies_str: str, message_handler: Callable):
        """
        初始化WebSocket客户端
        
        Args:
            cookies_str (str): Cookies字符串
            message_handler (Callable): 消息处理回调函数，接收消息数据和WebSocket连接对象
        """
        self.base_url = 'wss://wss-goofish.dingtalk.com/'
        self.cookies_str = cookies_str
        self.cookies = trans_cookies(cookies_str)
        self.message_handler = message_handler
        
        # 从cookies中获取用户ID
        if 'unb' not in self.cookies:
            # 尝试从其他字段中提取unb
            if 'havana_lgc2_77' in self.cookies:
                try:
                    havana_data = json.loads(self.cookies['havana_lgc2_77'])
                    if 'hid' in havana_data:
                        self.myid = str(havana_data['hid'])
                        logger.info(f"从havana_lgc2_77中提取到unb: {self.myid}")
                    else:
                        raise ValueError("havana_lgc2_77中不包含hid字段")
                except Exception as e:
                    logger.error(f"从havana_lgc2_77解析unb失败: {str(e)}")
                    raise ValueError("cookies中缺少unb字段，且无法从havana_lgc2_77提取")
            else:
                raise ValueError("cookies中缺少unb字段，无法初始化")
        else:
            self.myid = self.cookies['unb']
            
        # 生成设备ID
        self.device_id = generate_device_id(self.myid)
        
        # 心跳相关配置
        self.heartbeat_interval = 15  # 心跳间隔15秒
        self.heartbeat_timeout = 5    # 心跳超时5秒
        self.last_heartbeat_time = 0
        self.last_heartbeat_response = 0
        self.heartbeat_task = None
        self.ws = None
        
        # 消息ID相关
        self.latest_message_id = None  # 最新消息ID
        self.found_pnm_id_flag = False # 是否找到过带PNM后缀的消息ID
    
    async def init(self, ws):
        """
        初始化WebSocket连接
        
        Args:
            ws: WebSocket连接对象
        """
        try:
            xianyu_apis = XianyuApis()
            token_info = xianyu_apis.get_token(self.cookies, self.device_id)
            
            # 首先检查是否有accessToken，有则代表成功
            if token_info and 'data' in token_info and 'accessToken' in token_info['data']:
                token = token_info['data']['accessToken']
                logger.info("成功获取token，准备初始化连接")
            else:
                # 检查是否返回错误信息
                error_message = "获取token失败: 未知错误"
                if "ret" in token_info and isinstance(token_info["ret"], list) and len(token_info["ret"]) > 0:
                    error_msg = token_info["ret"][0]
                    logger.error(f"获取token失败: {error_msg}")
                    
                    # 检查是否是令牌过期或为空的错误
                    if "令牌过期" in error_msg or "TOKEN_EMPTY" in error_msg or "TOKEN_EXPIRED" in error_msg:
                        error_message = f"获取token失败: {token_info} ::令牌过期"
                    else:
                        error_message = f"获取token失败: {token_info}"
                
                # 如果没有token，则抛出异常
                logger.error(f"获取token失败，返回数据格式不正确或无token: {token_info}")
                raise ValueError(error_message)
            
            msg = {
                "lwp": "/reg",
                "headers": {
                    "cache-header": "app-key token ua wv",
                    "app-key": "444e9908a51d1cb236a27862abc769c9",
                    "token": token,
                    "ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 DingTalk(2.1.5) OS(Windows/10) Browser(Chrome/133.0.0.0) DingWeb/2.1.5 IMPaaS DingWeb/2.1.5",
                    "dt": "j",
                    "wv": "im:3,au:3,sy:6",
                    "sync": "0,0;0;0;",
                    "did": self.device_id,
                    "mid": generate_mid()
                }
            }
            await ws.send(json.dumps(msg))
            logger.info("已发送WebSocket注册消息")
            
            # 等待一段时间，确保连接注册完成
            await asyncio.sleep(1)
            
            # 发送同步状态确认消息，这是原始项目中的关键步骤
            sync_msg = {
                "lwp": "/r/SyncStatus/ackDiff", 
                "headers": {
                    "mid": generate_mid()
                }, 
                "body": [
                    {
                        "pipeline": "sync", 
                        "tooLong2Tag": "PNM,1", 
                        "channel": "sync", 
                        "topic": "sync", 
                        "highPts": 0,
                        "pts": int(time.time() * 1000) * 1000, 
                        "seq": 0, 
                        "timestamp": int(time.time() * 1000)
                    }
                ]
            }
            await ws.send(json.dumps(sync_msg))
            logger.info('连接注册完成')
            
        except Exception as e:
            logger.error(f"初始化WebSocket连接失败: {e}")
            raise
    
    async def send_msg(self, ws, cid, toid, text, reply_to_message_id=None):
        """
        发送消息
        
        Args:
            ws: WebSocket连接对象
            cid (str): 会话ID
            toid (str): 接收者ID
            text (str): 消息文本
            reply_to_message_id (str, optional): 引用回复的消息ID
        """
        text_obj = {
            "contentType": 1,
            "text": {
                "text": text
            }
        }
        text_base64 = str(base64.b64encode(json.dumps(text_obj).encode('utf-8')), 'utf-8')
        
        # 准备extension字段
        ext_json = "{}"
        if reply_to_message_id:
            # 检查消息ID格式
            if ".PNM" not in reply_to_message_id:
                logger.warning(f"【警告】引用的消息ID {reply_to_message_id} 不包含.PNM后缀，可能导致引用回复失败")
                
            # 构建引用回复的extension
            ext_json = "{\"replyMessageId\":\"" + reply_to_message_id + "\"}"
            logger.info(f"构建引用回复，引用消息ID: {reply_to_message_id}")
            
        msg = {
            "lwp": "/r/MessageSend/sendByReceiverScope",
            "headers": {
                "mid": generate_mid()
            },
            "body": [
                {
                    "uuid": generate_uuid(),
                    "cid": f"{cid}@goofish",
                    "conversationType": 1,
                    "content": {
                        "contentType": 101,
                        "custom": {
                            "type": 1,
                            "data": text_base64
                        }
                    },
                    "redPointPolicy": 0,
                    "extension": {
                        "extJson": ext_json
                    },
                    "ctx": {
                        "appVersion": "1.0",
                        "platform": "web"
                    },
                    "mtags": {},
                    "msgReadStatusSetting": 1
                },
                {
                    "actualReceivers": [
                        f"{toid}@goofish",
                        f"{self.myid}@goofish"
                    ]
                }
            ]
        }
        
        # 记录完整的发送消息 - 添加更详细的日志记录
        logger.info("====================【开始-发送消息日志】====================")
        logger.info(f"发送WebSocket消息 -> 回复用户: {toid}")
        logger.info(f"消息内容: {text}")
        logger.info(f"是否引用回复: {reply_to_message_id is not None}")
        if reply_to_message_id:
            logger.info(f"引用消息ID: {reply_to_message_id}")
        logger.info(f"完整消息结构: {json.dumps(msg, ensure_ascii=False, indent=2)}")
        logger.info("====================【结束-发送消息日志】====================")
        
        # 发送消息
        await ws.send(json.dumps(msg))
        logger.info("消息发送完成")
    
    @staticmethod
    async def send_msg_static(ws, cid, toid, text, cookies, reply_to_message_id=None):
        """
        静态方法版本的发送消息，供外部调用
        
        Args:
            ws: WebSocket连接对象
            cid (str): 会话ID
            toid (str): 接收者ID
            text (str): 消息文本
            cookies (dict): Cookies字典
            reply_to_message_id (str, optional): 引用回复的消息ID
        """
        # 提取用户ID
        myid = cookies['unb']
        
        # 构建消息对象
        text_obj = {
            "contentType": 1,
            "text": {
                "text": text
            }
        }
        text_base64 = str(base64.b64encode(json.dumps(text_obj).encode('utf-8')), 'utf-8')
        
        # 准备extension字段
        ext_json = "{}"
        if reply_to_message_id:
            # 检查消息ID格式
            if ".PNM" not in reply_to_message_id:
                logger.warning(f"【警告】引用的消息ID {reply_to_message_id} 不包含.PNM后缀，可能导致引用回复失败")
                
            # 构建引用回复的extension
            ext_json = "{\"replyMessageId\":\"" + reply_to_message_id + "\"}"
            logger.info(f"构建引用回复，引用消息ID: {reply_to_message_id}")
            
        msg = {
            "lwp": "/r/MessageSend/sendByReceiverScope",
            "headers": {
                "mid": generate_mid()
            },
            "body": [
                {
                    "uuid": generate_uuid(),
                    "cid": f"{cid}@goofish",
                    "conversationType": 1,
                    "content": {
                        "contentType": 101,
                        "custom": {
                            "type": 1,
                            "data": text_base64
                        }
                    },
                    "redPointPolicy": 0,
                    "extension": {
                        "extJson": ext_json
                    },
                    "ctx": {
                        "appVersion": "1.0",
                        "platform": "web"
                    },
                    "mtags": {},
                    "msgReadStatusSetting": 1
                },
                {
                    "actualReceivers": [
                        f"{toid}@goofish",
                        f"{myid}@goofish"
                    ]
                }
            ]
        }
        
        # 发送消息
        logger.info(f"发送消息 -> 回复用户: {toid}, 内容: {text[:20]}...")
        await ws.send(json.dumps(msg))
        logger.info("消息发送完成")
    
    def is_chat_message(self, message):
        """
        判断是否为聊天消息
        
        Args:
            message: 消息对象
            
        Returns:
            bool: 是否为聊天消息
        """
        try:
            # 检查是否为有效的聊天消息
            return (
                isinstance(message, dict) 
                and "1" in message 
                and isinstance(message["1"], dict)  # 确保是字典类型
                and "10" in message["1"]
                and isinstance(message["1"]["10"], dict)  # 确保是字典类型
                and "reminderContent" in message["1"]["10"]
            )
        except Exception:
            return False
    
    def is_sync_package(self, message_data):
        """
        判断是否为同步包
        
        Args:
            message_data: 消息数据
            
        Returns:
            bool: 是否为同步包
        """
        try:
            return (
                isinstance(message_data, dict)
                and "body" in message_data
                and "syncPushPackage" in message_data["body"]
                and "data" in message_data["body"]["syncPushPackage"]
                and len(message_data["body"]["syncPushPackage"]["data"]) > 0
            )
        except Exception:
            return False
    
    def is_typing_status(self, message):
        """
        判断是否为输入状态消息
        
        Args:
            message: 消息对象
            
        Returns:
            bool: 是否为输入状态消息
        """
        try:
            # 检查原始方法的判断条件
            if (isinstance(message, dict) and 
                    "1" in message and 
                    isinstance(message["1"], dict) and 
                    "4" in message["1"] and 
                    message["1"]["4"] == 2):
                return True
                
            # 增加原始项目中的判断条件
            if (isinstance(message, dict) and 
                "1" in message and 
                isinstance(message["1"], list) and 
                len(message["1"]) > 0 and 
                isinstance(message["1"][0], dict) and 
                "1" in message["1"][0] and 
                isinstance(message["1"][0]["1"], str) and 
                "@goofish" in message["1"][0]["1"]):
                return True
                
            return False
        except Exception:
            return False
            
    def extract_message_id_from_non_chat(self, message):
        """从非聊天消息中提取消息ID，优先返回带.PNM后缀的ID"""
        try:
            pnm_ids = []  # 存储所有找到的PNM格式ID
            
            # 1. 直接检查message["1"]字段是否为带PNM的字符串
            if "1" in message and isinstance(message["1"], str) and ".PNM" in message["1"]:
                pnm_ids.append(message["1"])
                
            # 2. 检查message["1"]是否为列表，且包含PNM字符串
            elif "1" in message and isinstance(message["1"], list):
                for item in message["1"]:
                    if isinstance(item, str) and ".PNM" in item:
                        pnm_ids.append(item)
                        
            # 3. 检查其他顶级字段
            for key, value in message.items():
                if isinstance(value, str) and ".PNM" in value:
                    pnm_ids.append(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str) and ".PNM" in item:
                            pnm_ids.append(item)
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, str) and ".PNM" in sub_value:
                            pnm_ids.append(sub_value)
            
            # 如果找到多个ID，记录在日志中
            if len(pnm_ids) > 1:
                logger.info(f"从非聊天消息中找到多个带PNM后缀的ID: {pnm_ids}，使用第一个")
                
            # 返回第一个找到的ID，没有则返回None
            return pnm_ids[0] if pnm_ids else None
            
        except Exception as e:
            logger.error(f"从非聊天消息提取ID时出错: {e}")
            return None
            
    async def handle_message(self, message_data, websocket):
        """
        处理收到的消息
        
        Args:
            message_data: 消息数据
            websocket: WebSocket连接对象
        """
        try:
            # 记录接收到的原始消息
            if self.is_sync_package(message_data):
                logger.info("====================【开始-接收消息日志】====================")
                logger.info(f"接收到WebSocket消息: {type(message_data).__name__}")
                logger.info(f"消息头部: {json.dumps(message_data.get('headers', {}), ensure_ascii=False)}")
                
                # 尝试记录同步包数据
                try:
                    sync_data = message_data["body"]["syncPushPackage"]["data"][0]
                    logger.info(f"同步包数据类型: {type(sync_data).__name__}")
                    if "data" in sync_data:
                        logger.info(f"同步包数据长度: {len(str(sync_data['data']))}")
                        # 添加数据哈希值记录，方便判断数据是否有变化
                        data_hash = hash(str(sync_data['data']))
                        logger.info(f"同步包数据哈希值: {data_hash}")
                except Exception as e:
                    logger.debug(f"记录同步包数据时出错: {e}")
                
                logger.info("====================【结束-接收消息日志】====================")
            
            # 发送ACK响应 - 从XianyuAutoAgent添加
            try:
                message = message_data
                ack = {
                    "code": 200,
                    "headers": {
                        "mid": message["headers"]["mid"] if "mid" in message["headers"] else generate_mid(),
                        "sid": message["headers"]["sid"] if "sid" in message["headers"] else '',
                    }
                }
                if 'app-key' in message["headers"]:
                    ack["headers"]["app-key"] = message["headers"]["app-key"]
                if 'ua' in message["headers"]:
                    ack["headers"]["ua"] = message["headers"]["ua"]
                if 'dt' in message["headers"]:
                    ack["headers"]["dt"] = message["headers"]["dt"]
                await websocket.send(json.dumps(ack))
            except Exception as e:
                pass
            
            # 如果不是同步包消息，直接返回
            if not self.is_sync_package(message_data):
                # 如果有消息处理函数，调用它处理非同步包消息
                if self.message_handler and self.message_handler != self.handle_message:
                    await self.message_handler(message_data, websocket)
                return

            # 获取并解密数据
            sync_data = message_data["body"]["syncPushPackage"]["data"][0]
            
            # 检查是否有必要的字段
            if "data" not in sync_data:
                logger.debug("同步包中无data字段")
                return

            # 解密数据
            data = sync_data["data"]
            
            # 先尝试base64解码，如果成功则是未加密消息
            try:
                decoded_data = base64.b64decode(data).decode("utf-8")
                json_data = json.loads(decoded_data)
                logger.debug("无需解密的消息")
                # 记录未加密消息的内容
                message_str = json.dumps(json_data, ensure_ascii=False)
                if len(message_str) > 1000:
                    logger.info(f"未加密消息内容(截取): {message_str[:1000]}...（内容过长已截断）")
                else:
                    logger.info(f"未加密消息内容: {message_str}")
                
                # 如果有消息处理函数，调用它处理解密后的消息
                if self.message_handler and self.message_handler != self.handle_message:
                    await self.message_handler(message_data, websocket)
                return
            except Exception as e:
                # 解码失败，说明需要解密
                logger.debug(f"需要解密的消息: {e}")
            
            # 尝试解密消息
            try:
                decrypted_data = decrypt(data)
                message = json.loads(decrypted_data)
                
                # 记录解密后的消息内容
                logger.info("====================【开始-解密消息日志】====================")
                logger.info(f"解密后的消息类型: {type(message).__name__}")
                # 限制输出长度，避免日志过大
                message_str = json.dumps(message, ensure_ascii=False)
                if len(message_str) > 1000:
                    logger.info(f"解密后的消息(截取): {message_str[:1000]}...（内容过长已截断）")
                else:
                    logger.info(f"解密后的消息: {message_str}")
                logger.info("====================【结束-解密消息日志】====================")
            except Exception as e:
                logger.error(f"消息解密失败: {e}")
                return
            
            # 检查是否为订单相关消息
            try:
                # 判断是否为订单消息
                if '3' in message and 'redReminder' in message['3']:
                    if message['3']['redReminder'] == '等待买家付款':
                        user_id = message['1'].split('@')[0]
                        user_url = f'https://www.goofish.com/personal?userId={user_id}'
                        logger.info(f'等待买家 {user_url} 付款')
                        return
                    elif message['3']['redReminder'] == '交易关闭':
                        user_id = message['1'].split('@')[0]
                        user_url = f'https://www.goofish.com/personal?userId={user_id}'
                        logger.info(f'卖家 {user_url} 交易关闭')
                        return
                    elif message['3']['redReminder'] == '等待卖家发货':
                        user_id = message['1'].split('@')[0]
                        user_url = f'https://www.goofish.com/personal?userId={user_id}'
                        logger.info(f'交易成功 {user_url} 等待卖家发货')
                        return
            except Exception:
                pass

            # 判断消息类型
            if self.is_typing_status(message):
                logger.debug("用户正在输入")
                return
            elif not self.is_chat_message(message):
                logger.debug("其他非聊天消息")
                logger.debug(f"原始消息: {message}")
                
                # 尝试从非聊天消息中提取消息ID
                non_chat_message_id = self.extract_message_id_from_non_chat(message)
                if non_chat_message_id:
                    logger.info(f"从非聊天消息中提取到消息ID: {non_chat_message_id}（不缓存）")
                    
                    # 更新全局最新消息ID仅用于日志记录
                    old_latest = self.latest_message_id
                    self.latest_message_id = non_chat_message_id
                    logger.info(f"记录全局最新消息ID: {old_latest} -> {non_chat_message_id}（仅用于日志，不用于回复）")
                    
                    # 如果是带.PNM后缀的ID，设置标志
                    if ".PNM" in non_chat_message_id:
                        self.found_pnm_id_flag = True
                        logger.info("找到带PNM后缀的消息ID，设置found_pnm_id_flag=True")
                return
            
            # 处理聊天消息
            create_time = int(message["1"]["5"])
            send_user_name = message["1"]["10"]["reminderTitle"]
            send_user_id = message["1"]["10"]["senderUserId"]
            send_message = message["1"]["10"]["reminderContent"]
            
            # 提取消息ID
            message_id = None
            logger.info("====================【开始-消息ID提取日志】====================")
            logger.info(f"尝试提取消息ID，用户: {send_user_name}，消息: {send_message}")
            
            # 记录原始消息的关键字段，方便分析
            important_fields = {}
            for field in ["1", "2", "3", "4", "5", "6", "10", "11", "20", "24"]:
                if field in message and field != "1":  # 排除1字段，因为它是整个消息的主体
                    important_fields[field] = message[field]
                elif field in message["1"] and not isinstance(message["1"], list):
                    important_fields[field] = message["1"][field]
            
            logger.info(f"消息关键字段: {json.dumps(important_fields, ensure_ascii=False)}")
            
            # 优先查找带.PNM后缀的消息ID
            if "3" in message["1"] and isinstance(message["1"]["3"], str) and ".PNM" in message["1"]["3"]:
                message_id = message["1"]["3"]
                logger.info(f"优先从消息的1[3]字段提取到带PNM后缀的消息ID: {message_id}")
                # 设置标志，表示找到了带PNM后缀的消息ID
                self.found_pnm_id_flag = True
                self.latest_message_id = message_id
                logger.info("在聊天消息中找到带PNM后缀的消息ID，设置found_pnm_id_flag=True")
            
            # 记录用户消息
            logger.info(f"收到用户 {send_user_name}({send_user_id}) 的消息: {send_message}")
            
            # 获取商品信息 - 从消息字段中提取
            item_id = "unknown_item"
            item_description = "未知商品"
            
            # 尝试从扩展字段提取商品信息
            try:
                if "bizTag" in message["1"]["10"]:
                    biz_tag = message["1"]["10"].get("bizTag", "")
                    if biz_tag:
                        try:
                            biz_tag_json = json.loads(biz_tag)
                            item_id = biz_tag_json.get("itemId", item_id)
                            item_description = biz_tag_json.get("itemTitle", item_description)
                        except Exception:
                            pass
            except Exception:
                pass
            
            # 提取会话ID
            cid = None
            if "2" in message["1"]:
                cid = message["1"]["2"].split('@')[0] if '@' in message["1"]["2"] else message["1"]["2"]
            
            # 消息去重检查 - 计算消息指纹
            import hashlib
            import time
            fingerprint = hashlib.md5(f"{send_user_id}:{send_message}:{item_id}".encode()).hexdigest()
            current_time = time.time()
            
            # 检查是否为最近处理过的相同消息
            if hasattr(self, 'processed_messages') and fingerprint in self.processed_messages:
                time_diff = current_time - self.processed_messages[fingerprint]
                window = self.processed_window if hasattr(self, 'processed_window') else 30
                if time_diff < window:
                    logger.warning(f"handle_message检测到短时间内({time_diff:.1f}秒)的重复消息，跳过处理: {send_message}")
                    return
            
            # 更新消息指纹缓存
            if hasattr(self, 'processed_messages'):
                self.processed_messages[fingerprint] = current_time
            
            # 构建处理任务数据
            task_data = {
                "message": message,  # 原始消息
                "send_user_name": send_user_name,
                "send_user_id": send_user_id,
                "send_message": send_message,
                "item_id": item_id,
                "item_description": item_description,
                "cid": cid,
                "message_id": message_id,
                "fingerprint": fingerprint  # 添加指纹用于消息唯一性跟踪
            }
            
            # 加入消息队列处理
            self.message_queue.put({
                "task_data": task_data,
                "websocket": websocket
            })
            
            # 如果有消息处理函数且不是自己，调用它
            if self.message_handler and self.message_handler != self.handle_message:
                await self.message_handler(message_data, websocket)
                
        except Exception as e:
            logger.error(f"消息处理总体出错: {e}")
            logger.exception("消息处理异常详情")
    
    async def send_heartbeat(self, ws):
        """
        发送心跳包
        
        Args:
            ws: WebSocket连接对象
        """
        heartbeat_mid = generate_mid()
        heartbeat_msg = {
            "lwp": "/!",
            "headers": {
                "mid": heartbeat_mid
            }
        }
        await ws.send(json.dumps(heartbeat_msg))
        self.last_heartbeat_time = time.time()
        logger.debug("发送心跳包")
        return heartbeat_mid
    
    async def heartbeat_loop(self, ws):
        """
        心跳循环
        
        Args:
            ws: WebSocket连接对象
        """
        while True:
            try:
                current_time = time.time()
                
                # 检查是否需要发送心跳
                if current_time - self.last_heartbeat_time >= self.heartbeat_interval:
                    await self.send_heartbeat(ws)
                
                # 检查上次心跳响应时间，如果超时则认为连接已断开
                if (current_time - self.last_heartbeat_response) > (self.heartbeat_interval + self.heartbeat_timeout):
                    logger.warning("心跳响应超时，可能连接已断开")
                    break
                
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"心跳循环出错: {e}")
                await asyncio.sleep(5)
    
    async def handle_heartbeat_response(self, message_data):
        """
        处理心跳响应
        
        Args:
            message_data: 消息数据
        
        Returns:
            bool: 是否是心跳响应
        """
        try:
            # 标准格式的心跳响应检测
            if (
                isinstance(message_data, dict)
                and "headers" in message_data
                and "mid" in message_data["headers"]
                and "code" in message_data
                and message_data["code"] == 200
            ):
                self.last_heartbeat_response = time.time()
                logger.debug("收到标准格式的心跳响应")
                return True
                
            # 加入对其他可能格式的心跳响应的检测
            # 1. 检查是否为简单的确认响应
            elif (
                isinstance(message_data, dict)
                and "code" in message_data
                and message_data["code"] == 200
                and "body" not in message_data  # 确认响应通常没有body字段
            ):
                self.last_heartbeat_response = time.time()
                logger.debug("收到简单确认格式的心跳响应")
                return True
                
            # 2. 检查是否为特殊格式的心跳响应
            elif (
                isinstance(message_data, dict)
                and "headers" in message_data
                and message_data.get("lwp", "") == "/!"  # 心跳请求路径
            ):
                self.last_heartbeat_response = time.time()
                logger.debug("收到心跳请求确认")
                return True
                
            # 记录不匹配任何心跳模式的消息
            logger.debug(f"不是心跳响应的消息: {message_data.get('lwp', '') if isinstance(message_data, dict) else type(message_data).__name__}")
            
        except Exception as e:
            logger.error(f"处理心跳响应时出错: {e}")
        return False
    
    async def connect(self):
        """
        建立WebSocket连接并处理消息
        """
        # 记录token获取失败次数
        token_failure_count = 0
        max_token_failures = 3  # 最大允许的连续失败次数
        
        # 记录WebSocket连接失败次数
        ws_connection_attempts = 0
        max_ws_connection_attempts = 3  # 最大WebSocket重连尝试次数
        
        try:
            # 设置WebSocket连接的headers
            headers = {
                "Cookie": self.cookies_str,
                "Host": "wss-goofish.dingtalk.com",
                "Connection": "Upgrade",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                "Origin": "https://www.goofish.com",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
            
            logger.info("正在连接到闲鱼WebSocket服务器...")
            try:
                # 增加WebSocket连接尝试次数
                ws_connection_attempts += 1
                
                async with websockets.connect(self.base_url, extra_headers=headers) as ws:
                    self.ws = ws
                    logger.info("WebSocket连接已建立")
                    
                    # 初始化连接
                    try:
                        await self.init(ws)
                        # 如果成功，重置失败计数
                        token_failure_count = 0
                        ws_connection_attempts = 0  # 重置WebSocket连接尝试次数
                    except ValueError as e:
                        # 如果是token错误，增加失败计数
                        if "令牌过期" in str(e) or "令牌为空" in str(e):
                            token_failure_count += 1
                            logger.warning(f"token获取失败次数: {token_failure_count}/{max_token_failures}")
                        raise  # 继续抛出异常，让外层处理
                    
                    # 初始化心跳时间
                    self.last_heartbeat_time = time.time()
                    self.last_heartbeat_response = time.time()
                    
                    # 启动心跳任务
                    self.heartbeat_task = asyncio.create_task(self.heartbeat_loop(ws))
                    
                    # 使用与原始项目相同的消息处理循环
                    async for message in ws:
                        try:
                            message_data = json.loads(message)
                            
                            # 处理心跳响应
                            if await self.handle_heartbeat_response(message_data):
                                continue
                            
                            # 处理其他消息
                            await self.handle_message(message_data, ws)
                                
                        except json.JSONDecodeError:
                            logger.error("消息解析失败")
                        except Exception as e:
                            logger.error(f"处理消息时发生错误: {str(e)}")
                            logger.debug(f"原始消息: {message}")
                    
                    # 取消心跳任务
                    if self.heartbeat_task:
                        self.heartbeat_task.cancel()
                        try:
                            await self.heartbeat_task
                        except asyncio.CancelledError:
                            pass
            except websockets.exceptions.ConnectionClosed as ws_closed:
                logger.warning(f"WebSocket连接已关闭: {ws_closed}")
                # 只在WebSocket连接关闭时增加计数
                if self.heartbeat_task:
                    self.heartbeat_task.cancel()
                    try:
                        await self.heartbeat_task
                    except asyncio.CancelledError:
                        pass
                
                # 检查是否达到最大WebSocket重连尝试次数
                if ws_connection_attempts >= max_ws_connection_attempts:
                    logger.error(f"WebSocket连接失败次数达到上限({max_ws_connection_attempts}次)，将尝试重新获取cookies")
                    # 强制重新获取cookies
                    force_manual_login = token_failure_count >= max_token_failures
                    await self._handle_token_failure(force_manual_login)
                    # 等待5秒后重试
                    await asyncio.sleep(5)
                    return
                else:
                    # 等待5秒后重连
                    logger.info(f"将进行第 {ws_connection_attempts+1}/{max_ws_connection_attempts} 次WebSocket重连尝试")
                    await asyncio.sleep(5)
                    return
                    
        except ValueError as e:
            error_msg = str(e)
            if "获取token失败" in error_msg and ("令牌过期" in error_msg or "TOKEN_EMPTY" in error_msg or "TOKEN_EXPIRED" in error_msg):
                logger.warning("检测到token过期或为空，尝试重新获取cookies...")
                await self._handle_token_failure(token_failure_count >= max_token_failures)
            else:
                logger.error(f"WebSocket连接出错: {e}")
            # 等待5秒后重连
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"WebSocket连接出错: {e}")
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass
            # 等待5秒后重连
            await asyncio.sleep(5)
        finally:
            logger.info("WebSocket连接已关闭，将尝试重新连接")
    
    async def _handle_token_failure(self, force_manual_login):
        """处理token获取失败的情况"""
        # 检查是否需要强制手动登录
        if force_manual_login:
            # 删除保存的浏览器状态，强制用户重新登录
            data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data'))
            state_path = os.path.join(data_dir, 'playwright_state.json')
            
            if os.path.exists(state_path):
                try:
                    os.remove(state_path)
                    logger.warning("已删除浏览器状态文件，将使用强制手动登录模式")
                except Exception as e:
                    logger.error(f"删除浏览器状态文件失败: {e}")
        
        # 清晰地指示将启动浏览器
        if force_manual_login:
            logger.info("=================================================")
            logger.info("       由于多次自动登录失败，将使用强制手动登录模式")
            logger.info("       请在打开的浏览器中手动操作完成登录")
            logger.info("       需要确保在浏览器中完全退出后重新登录")
            logger.info("=================================================")
        else:
            logger.info("即将打开浏览器窗口，请完成登录操作...")
        
        # 使用playwright获取新的cookies
        try:
            new_cookies_data = await get_login_cookies(force_login=force_manual_login)
            
            if new_cookies_data and "cookies" in new_cookies_data:
                # 更新cookies
                new_cookies_str = cookies_dict_to_str(new_cookies_data["cookies"])
                self.cookies_str = new_cookies_str
                self.cookies = new_cookies_data["cookies"]
                
                # 从cookies中更新用户ID
                if "unb" in self.cookies:
                    self.myid = self.cookies["unb"]
                    logger.info(f"使用新的用户ID: {self.myid}")
                else:
                    logger.warning("新获取的cookies中未找到unb字段")
                
                # 更新设备ID
                self.device_id = generate_device_id(self.myid)
                logger.info(f"更新设备ID: {self.device_id}")
                
                logger.info("成功更新cookies，准备重新连接...")
                return True
            else:
                logger.error("自动获取新cookies失败，可能需要手动操作")
                if new_cookies_data is None:
                    logger.error("get_login_cookies返回值为None，浏览器可能被关闭或登录超时")
                else:
                    logger.error(f"返回的数据格式不正确: {new_cookies_data}")
                return False
        except Exception as login_error:
            logger.error(f"自动登录过程中发生错误: {login_error}")
            return False
    
    async def run(self):
        """运行WebSocket客户端，自动重连"""
        # 记录连续运行失败次数
        consecutive_failures = 0
        max_consecutive_failures = 10  # 最大连续失败次数

        while True:
            try:
                # 尝试建立连接
                await self.connect()
                # 如果连接成功完成并返回，则重置失败计数
                consecutive_failures = 0
            except Exception as e:
                # 增加失败计数
                consecutive_failures += 1
                logger.error(f"运行WebSocket客户端时出错 (第{consecutive_failures}次): {e}")
                
                # 如果连续失败次数过多，则尝试强制重新登录
                if consecutive_failures >= max_consecutive_failures:
                    logger.critical(f"连续失败次数达到{max_consecutive_failures}次，将尝试强制重新登录")
                    try:
                        # 强制重新登录
                        await self._handle_token_failure(force_manual_login=True)
                        # 重置失败计数
                        consecutive_failures = 0
                    except Exception as login_error:
                        logger.critical(f"强制重新登录失败: {login_error}")
            
            # 重连延迟
            delay = min(30, 5 * consecutive_failures)  # 随着失败次数增加延迟时间，但最多30秒
            logger.info(f"{delay}秒后尝试重新连接...")
            await asyncio.sleep(delay)

class XianyuLive(XianyuWebSocket):
    """
    闲鱼直播类，继承自XianyuWebSocket
    处理闲鱼消息并生成回复
    """
    
    def __init__(self, cookies_str: str, bot):
        """
        初始化闲鱼直播对象
        
        Args:
            cookies_str (str): Cookies字符串
            bot: 回复机器人实例
        """
        # 先创建需要的属性
        self.bot = bot
        self.context_manager = ChatContextManager()
        self.message_queue = Queue()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        
        # 添加全局系统通知消息缓存
        self.recent_responses = {}  # 格式: {user_id: {"message_type": str, "timestamp": float, "count": int}}
        self.system_notice_window = 60  # 系统通知60秒内不重复回复
        
        # 消息处理指纹缓存，用于检测重复消息
        self.processed_messages = {}  # 格式: {fingerprint: timestamp}
        self.processed_window = 30  # 30秒内相同指纹的消息视为重复
        
        # 系统通知关键词列表 - 扩展更全面的系统通知关键词
        self.system_notices = [
            # 发货相关通知
            "你已发货", "发来一条新消息", "已付款", "准备发货", "已下单", 
            "已经付款", "买家留言", "快递信息", "物流更新", "发货提醒",
            "等待卖家发货", "卖家已发货", "已发货", "发货成功", "订单发货",
            
            # 其他系统通知类型
            "系统通知", "已收货", "已评价", "已退款", "订单更新",
            "交易完成", "交易关闭", "退款申请", "退款成功", "申请售后",
            "订单变更", "支付成功", "等待付款", "超时未付款"
        ]
        
        # 专门用于识别发货相关通知的关键词
        self.shipping_keywords = [
            "发货", "已发货", "等待卖家发货", "发货通知", "物流", 
            "运单", "快递单", "包裹", "寄件", "配送", 
            "派送", "待发货", "已打包", "发货成功"
        ]
        
        # 最近通知缓存，用于极短时间内的系统通知去重
        self._last_system_notification = {
            "key": "",
            "time": 0,
            "message": ""
        }
        
        # 初始化父类，这里不传递消息处理函数，避免循环引用
        super().__init__(cookies_str, None)
        
        # 消息处理函数设置
        # 在父类初始化完成后，再设置消息处理函数为子类方法
        self.message_handler = self.handle_live_message
        
        # 启动工作线程
        self.worker_threads = []
        for _ in range(3):  # 启动3个工作线程
            worker = Thread(target=self._message_worker, args=())
            worker.daemon = True
            worker.start()
            self.worker_threads.append(worker)
            
        # 启动定期清理系统通知缓存的线程
        self.cache_cleaner = Thread(target=self._clean_system_notice_cache_worker, args=())
        self.cache_cleaner.daemon = True
        self.cache_cleaner.start()
        
        # 启动定期清理消息指纹缓存的线程
        self.fingerprint_cleaner = Thread(target=self._clean_message_fingerprints_worker, args=())
        self.fingerprint_cleaner.daemon = True
        self.fingerprint_cleaner.start()
    
    def _clean_system_notice_cache_worker(self):
        """定期清理过期的系统通知缓存"""
        import time
        
        while True:
            try:
                # 每5分钟清理一次
                time.sleep(300)
                
                # 清理过期的缓存
                current_time = time.time()
                users_to_clean = []
                notices_to_clean = {}
                
                for user_id, notices in self.recent_responses.items():
                    notices_to_clean[user_id] = []
                    all_expired = True
                    
                    for notice_type, notice_data in notices.items():
                        time_diff = current_time - notice_data["timestamp"]
                        # 检查是否具有扩展窗口标记（主要用于发货相关通知）
                        has_extended_window = notice_data.get("extended_window", False)
                        
                        # 根据是否有扩展窗口使用不同的过期时间
                        expiry_time = 7200 if has_extended_window else self.system_notice_window * 2  # 扩展窗口为2小时
                        
                        # 如果超过系统通知窗口时间，标记为需要清理
                        if time_diff > expiry_time:
                            notices_to_clean[user_id].append(notice_type)
                            logger.debug(f"标记清理: 用户 {user_id} 的 '{notice_type}' 通知已过期 {time_diff:.0f}秒 (限制: {expiry_time}秒)")
                        else:
                            all_expired = False
                            if has_extended_window:
                                logger.debug(f"保留扩展窗口通知: 用户 {user_id} 的 '{notice_type}' 通知存在 {time_diff:.0f}秒 (限制: {expiry_time}秒)")
                    
                    # 如果该用户的所有通知都已过期，可以清理整个用户记录
                    if all_expired and len(notices) > 0:
                        users_to_clean.append(user_id)
                
                # 执行清理
                for user_id in users_to_clean:
                    if user_id in self.recent_responses:
                        del self.recent_responses[user_id]
                        logger.debug(f"清理用户 {user_id} 的所有系统通知缓存")
                
                for user_id, notices in notices_to_clean.items():
                    if user_id in self.recent_responses:
                        for notice_type in notices:
                            if notice_type in self.recent_responses[user_id]:
                                del self.recent_responses[user_id][notice_type]
                                logger.debug(f"清理用户 {user_id} 的 '{notice_type}' 系统通知缓存")
                
                # 日志记录清理状态
                if users_to_clean or any(notices for notices in notices_to_clean.values()):
                    logger.info(f"系统通知缓存清理完成: 清理了 {len(users_to_clean)} 个用户记录")
            except Exception as e:
                logger.error(f"清理系统通知缓存时出错: {e}")
                # 异常后等待30秒再继续
                time.sleep(30)
    
    def _message_worker(self):
        """
        消息处理工作线程函数
        从队列中获取消息并处理
        """
        while True:
            task_completed = False  # 添加标记，避免重复调用task_done()
            try:
                # 从队列中获取消息
                message_data = self.message_queue.get()
                if message_data is None:  # 结束信号
                    self.message_queue.task_done()
                    break
                    
                task_data = message_data["task_data"]
                websocket = message_data["websocket"]
                
                # 解构任务数据
                message = task_data["message"]
                send_user_name = task_data["send_user_name"]
                send_user_id = task_data["send_user_id"]
                send_message = task_data["send_message"]
                item_id = task_data["item_id"]
                item_description = task_data["item_description"]
                cid = task_data["cid"]
                message_id = task_data.get("message_id")  # 获取消息ID，用于引用回复
                fingerprint = task_data.get("fingerprint", "")  # 获取消息指纹
                
                # 再次检查消息指纹，确保没有其他线程已经处理过相同的消息
                # 这是双重保险，防止短时间内相同消息通过不同渠道进入队列
                if fingerprint:
                    import time
                    current_time = time.time()
                    last_processed_time = self.processed_messages.get(fingerprint, 0)
                    
                    # 只有当指纹匹配且时间差在窗口内时才认为是重复
                    time_diff = current_time - last_processed_time
                    if (last_processed_time > 0 and 
                        time_diff < self.processed_window and
                        time_diff > 0.001):  # 添加最小时间差阈值，防止误判
                        logger.warning(f"工作线程检测到短时间内({time_diff:.2f}秒)的重复消息，跳过处理: {send_message}")
                        # 标记任务为完成 - 只有当消息确实是重复时才标记
                        self.message_queue.task_done()
                        task_completed = True
                        continue
                    
                    # 更新处理时间戳，表示正在处理该消息
                    if not fingerprint in self.processed_messages or time_diff > self.processed_window:
                        # 只有新消息或超过窗口的旧消息才更新时间戳
                        self.processed_messages[fingerprint] = current_time
                
                logger.info(f"处理用户 {send_user_name} 的消息: {send_message}")
                
                # 消息分析日志 - 仅对可能的系统通知进行详细日志
                if send_message in ["发来一条新消息", "新消息", "系统通知"] or any(notice in send_message for notice in self.system_notices):
                    logger.info("----------- 系统通知分析开始 -----------")
                    
                    # 提取关键字段
                    if isinstance(message, dict) and "1" in message and isinstance(message["1"], dict):
                        # 尝试提取消息各关键部分
                        if "10" in message["1"] and isinstance(message["1"]["10"], dict):
                            biz_tag = message["1"]["10"].get("bizTag", "")
                            ext_json = message["1"]["10"].get("extJson", "")
                            reminder_title = message["1"]["10"].get("reminderTitle", "")
                            reminder_content = message["1"]["10"].get("reminderContent", "")
                            reminder_url = message["1"]["10"].get("reminderUrl", "")
                            
                            logger.info(f"系统通知标题: {reminder_title}")
                            logger.info(f"系统通知内容: {reminder_content}")
                            logger.info(f"系统通知URL: {reminder_url}")
                            
                            # 尝试解析业务标签
                            if biz_tag:
                                try:
                                    biz_tag_obj = json.loads(biz_tag)
                                    task_name = biz_tag_obj.get("taskName", "")
                                    task_id = biz_tag_obj.get("taskId", "")
                                    logger.info(f"系统通知任务名称: {task_name}")
                                    logger.info(f"系统通知任务ID: {task_id}")
                                except Exception as e:
                                    logger.warning(f"解析bizTag失败: {e}")
                            
                            # 尝试解析扩展JSON
                            if ext_json:
                                try:
                                    ext_json_obj = json.loads(ext_json)
                                    msg_args = ext_json_obj.get("msgArgs", {})
                                    logger.info(f"系统通知参数: {msg_args}")
                                except Exception as e:
                                    logger.warning(f"解析extJson失败: {e}")
                    
                    logger.info("----------- 系统通知分析结束 -----------")
                
                # 检查系统通知的标志
                is_system_notice = False
                is_shipping_notice = False
                
                # 更详细的系统通知检查 - 消息内容匹配
                if any(notice in send_message for notice in self.system_notices):
                    is_system_notice = True
                    logger.info(f"检测到系统通知: '{send_message}'")
                
                # 检查消息中是否存在关键字段，这是系统通知的另一种特征
                if isinstance(message, dict) and "1" in message and isinstance(message["1"], dict):
                    if "10" in message["1"] and isinstance(message["1"]["10"], dict):
                        # 检查reminderContent字段
                        if "reminderContent" in message["1"]["10"] and message["1"]["10"]["reminderContent"] == "发来一条新消息":
                            is_system_notice = True
                            logger.info(f"从消息字段检测到系统通知: reminderContent='发来一条新消息'")
                        
                        # 检查消息类型是否为发货相关
                        if "extJson" in message["1"]["10"]:
                            try:
                                ext_json = json.loads(message["1"]["10"]["extJson"])
                                if "task_id" in ext_json.get("msgArgs", {}):
                                    # 记录任务ID，可能包含重要信息
                                    task_id = ext_json["msgArgs"]["task_id"]
                                    logger.info(f"系统通知任务ID: {task_id}")
                                    
                                    # 通过任务ID识别消息类型
                                    if "taskName" in message["1"]["10"].get("bizTag", ""):
                                        try:
                                            biz_tag = json.loads(message["1"]["10"]["bizTag"])
                                            task_name = biz_tag.get("taskName", "")
                                            if task_name:
                                                logger.info(f"系统通知任务名称: {task_name}")
                                                if any(keyword in task_name for keyword in ["发货", "付款", "订单", "退款"]):
                                                    is_system_notice = True
                                                    
                                                    # 特别标记发货相关通知
                                                    if "发货" in task_name:
                                                        is_shipping_notice = True
                                                        logger.info(f"检测到发货相关系统通知: {task_name}")
                                        except Exception:
                                            pass
                            except Exception:
                                pass
                
                # 临时收集所有可能与发货相关的关键词
                shipping_keywords = self.shipping_keywords
                if any(keyword in send_message for keyword in shipping_keywords):
                    is_shipping_notice = True
                    is_system_notice = True
                    logger.info(f"检测到包含发货关键词的消息: '{send_message}'")
                
                # 额外检查：消息是否为"发来一条新消息"
                if send_message == "发来一条新消息":
                    # 这是一个典型的系统通知而非用户消息
                    is_system_notice = True
                    logger.info("检测到系统标准通知: '发来一条新消息'")
                    
                    # 检查消息中的其他线索判断是否为发货相关
                    if isinstance(message, dict) and "1" in message and isinstance(message["1"], dict):
                        if "10" in message["1"] and isinstance(message["1"]["10"], dict):
                            reminder_url = message["1"]["10"].get("reminderUrl", "")
                            if "order_detail" in reminder_url:
                                is_shipping_notice = True
                                logger.info("通过URL检测到订单/发货相关通知")
                
                # 额外的系统通知去重检查
                if is_system_notice:
                    import time
                    current_time = time.time()
                    
                    # 确定消息类型 - 对于系统通知，我们根据其内容分类
                    message_type = None
                    for notice in self.system_notices:
                        if notice in send_message:
                            message_type = notice
                            break
                    
                    if not message_type:
                        if is_shipping_notice:
                            message_type = "发货通知"
                        else:
                            message_type = "系统通知"  # 默认类型
                    
                    # 对于"发来一条新消息"特殊处理，用item_id和user_id组合作为更精确的标识
                    if send_message == "发来一条新消息":
                        unique_key = f"{send_user_id}_{message_type}" 
                        
                        # 检查全局缓存是否最近有同类型的系统通知
                        if hasattr(self, '_last_system_notification'):
                            last_notif = getattr(self, '_last_system_notification')
                            if last_notif.get('key') == unique_key:
                                time_diff = current_time - last_notif.get('time', 0)
                                if time_diff < 10:  # 特别短的去重窗口(10秒)用于系统通知
                                    logger.warning(f"极短时间内({time_diff:.1f}秒)收到相同系统通知，忽略此消息: {send_message}")
                                    self.message_queue.task_done()
                                    task_completed = True
                                    continue
                        
                        # 更新最近系统通知记录
                        if not hasattr(self, '_last_system_notification'):
                            setattr(self, '_last_system_notification', {})
                        getattr(self, '_last_system_notification').update({
                            'key': unique_key,
                            'time': current_time,
                            'message': send_message
                        })
                    
                    # 检查是否在去重窗口内已经回复过此类型的消息
                    if send_user_id in self.recent_responses:
                        user_responses = self.recent_responses[send_user_id]
                        
                        # 如果该用户最近收到过此类型系统通知的回复
                        if message_type in user_responses:
                            response_info = user_responses[message_type]
                            time_diff = current_time - response_info["timestamp"]
                            
                            # 如果在系统通知去重窗口内且已经回复过相同类型的消息
                            if time_diff < self.system_notice_window:
                                # 记录被过滤的消息
                                logger.info(f"系统通知去重: 已在 {time_diff:.2f} 秒内对用户 {send_user_name} 回复过类似的 '{message_type}' 通知，跳过此消息")
                                # 递增计数
                                self.recent_responses[send_user_id][message_type]["count"] += 1
                                # 跳过本次消息处理
                                self.message_queue.task_done()
                                task_completed = True
                                continue
                    
                    # 如果不存在用户记录，创建一个新的
                    if send_user_id not in self.recent_responses:
                        self.recent_responses[send_user_id] = {}
                
                # 添加用户消息到上下文
                self.context_manager.add_message(send_user_id, item_id, "user", send_message)
                
                # 获取完整的对话上下文
                context = self.context_manager.get_context(send_user_id, item_id)
                
                # 对发货相关通知或系统通知使用固定回复
                if is_shipping_notice:
                    # 直接使用预设回复
                    bot_reply = "已为您发货，请注意查收物流信息。如有问题随时联系我哟~"
                    logger.info(f"发货通知: 使用固定回复: {bot_reply}")
                elif is_system_notice:
                    # 对一般系统通知使用简短统一回复
                    bot_reply = "收到通知，感谢您的支持！如有问题随时联系我哟~"
                    logger.info(f"系统通知: 使用统一回复: {bot_reply}")
                else:
                    # 对普通消息使用模型生成回复
                    bot_reply = self.bot.generate_reply(
                        send_message,
                        item_description,
                        context=context
                    )
                
                # 检查是否为价格意图
                if hasattr(self.bot, 'last_intent') and self.bot.last_intent == "price":
                    self.context_manager.increment_bargain_count(send_user_id, item_id)
                    bargain_count = self.context_manager.get_bargain_count(send_user_id, item_id)
                    logger.info(f"用户 {send_user_name} 对商品 {item_id} 的议价次数: {bargain_count}")
                
                # 添加机器人回复到上下文
                self.context_manager.add_message(send_user_id, item_id, "assistant", bot_reply)
                
                logger.info(f"机器人回复 {send_user_name}: {bot_reply}")
                
                # 如果是系统通知，更新最近回复记录
                if is_system_notice:
                    import time
                    current_time = time.time()
                    message_type = None
                    for notice in self.system_notices:
                        if notice in send_message:
                            message_type = notice
                            break
                    
                    if not message_type:
                        if is_shipping_notice:
                            message_type = "发货通知"
                        else:
                            message_type = "系统通知"
                    
                    # 更新回复记录
                    self.recent_responses[send_user_id][message_type] = {
                        "timestamp": current_time,
                        "count": 1,
                        "message": send_message[:50]  # 保存消息前50个字符用于日志
                    }
                    
                    # 为发货相关消息设置更长的去重窗口
                    if is_shipping_notice:
                        logger.info("设置发货相关通知的去重窗口为2小时")
                        # 将发货相关消息的去重窗口设为两小时
                        self.recent_responses[send_user_id][message_type]["extended_window"] = True
                
                # 消息ID处理 - 优先从消息中提取带.PNM后缀的消息ID
                reply_to_message_id = None
                
                # 检查是否之前有找到过带PNM后缀的消息ID
                if not self.found_pnm_id_flag:
                    logger.warning("当前会话中尚未找到过带PNM后缀的消息ID，引用回复可能无法正常工作")
                    
                # 直接从消息原始字段中尝试提取带.PNM后缀的消息ID
                if isinstance(message, dict) and "1" in message and isinstance(message["1"], dict):
                    # 尝试从message["1"]["3"]字段获取带PNM后缀的ID
                    if "3" in message["1"] and isinstance(message["1"]["3"], str) and ".PNM" in message["1"]["3"]:
                        reply_to_message_id = message["1"]["3"]
                        logger.info(f"从消息字段1[3]提取到带PNM后缀的消息ID: {reply_to_message_id}")
                
                # 如果从原始字段没有找到带PNM后缀的ID，尝试使用全局最新消息ID
                if not reply_to_message_id and self.latest_message_id:
                    if ".PNM" in self.latest_message_id:
                        reply_to_message_id = self.latest_message_id
                        logger.info(f"使用全局最新带PNM后缀的消息ID: {reply_to_message_id}")
                    else:
                        logger.warning(f"全局最新消息ID {self.latest_message_id} 无PNM后缀，不适合用于引用")
                
                # 如果还是找不到带PNM后缀的ID，则使用传入的message_id
                if not reply_to_message_id and message_id:
                    if ".PNM" in message_id:
                        reply_to_message_id = message_id
                        logger.info(f"使用传入的带PNM后缀消息ID: {reply_to_message_id}")
                    else:
                        logger.warning(f"传入的消息ID {message_id} 无PNM后缀，可能不适合用于引用")
                
                # 日志记录
                if reply_to_message_id:
                    logger.info(f"将使用消息ID: {reply_to_message_id} 进行引用回复")
                else:
                    logger.warning("无有效的带PNM后缀消息ID，将发送普通消息（不使用引用回复）")
                
                # 使用事件循环发送消息，如果有消息ID则使用引用回复
                asyncio.run(XianyuLive.send_msg_static(
                    websocket, 
                    cid, 
                    send_user_id, 
                    bot_reply, 
                    self.cookies,
                    reply_to_message_id=reply_to_message_id
                ))
                
            except Exception as e:
                logger.error(f"处理队列消息时发生错误: {str(e)}")
            finally:
                # 标记任务完成 - 只有当之前没有标记过时才调用
                if not task_completed:
                    self.message_queue.task_done()
    
    async def handle_live_message(self, message_data, websocket):
        """
        处理接收到的消息
        
        Args:
            message_data (dict): 消息数据
            websocket: WebSocket连接对象
        """
        # 日志记录
        logger.debug(f"XianyuLive处理消息: {message_data.get('lwp', '')}")
        
        # 尝试从同步包中提取消息ID
        if self.is_sync_package(message_data):
            try:
                logger.info("处理同步包消息")
                body = message_data.get("body", {})
                sync_package = body.get("syncPushPackage", {})
                sync_data = sync_package.get("data", [])
                
                if sync_data and len(sync_data) > 0:
                    # 尝试解析msgSync消息
                    msgs = sync_data[0].get("msgs", [])
                    if msgs:
                        logger.info(f"发现同步包中的msgs字段，包含 {len(msgs)} 条消息")
                        
                    for msg in msgs:
                        # 提取消息ID
                        msg_id = msg.get("uuid", "")
                        if msg_id and ".PNM" in msg_id:
                            self.latest_message_id = msg_id
                            self.found_pnm_id_flag = True
                            logger.info(f"从同步包中提取到带PNM后缀的消息ID: {msg_id}")
                            
                        # 处理消息内容
                        # 解密消息内容
                        content = msg.get("content", {})
                        if content and content.get("contentType") == 101:
                            custom_data = content.get("custom", {})
                            if custom_data:
                                try:
                                    decoded_data = base64.b64decode(custom_data.get("data", ""))
                                    decoded_content = json.loads(decoded_data)
                                    
                                    # 只处理文本消息
                                    if decoded_content.get("contentType") == 1:
                                        # 提取消息文本
                                        message_text = decoded_content.get("text", {}).get("text", "")
                                        
                                        # 获取发送者信息
                                        from_id = msg.get("fromId", "").split("@")[0]
                                        
                                        # 忽略自己发送的消息
                                        if from_id == self.myid:
                                            continue
                                        
                                        # 获取会话和商品信息
                                        cid = msg.get("cid", "").split("@")[0]
                                        
                                        # 尝试从扩展字段获取用户名和商品信息
                                        extension = msg.get("extension", {})
                                        ext_json_str = extension.get("extJson", "{}")
                                        
                                        try:
                                            ext_json = json.loads(ext_json_str) if ext_json_str else {}
                                        except Exception:
                                            ext_json = {}
                                        
                                        # 提取发送者名称和商品信息
                                        send_user_name = ext_json.get("senderName", "未知用户")
                                        item_id = ext_json.get("itemId", "")
                                        item_description = ext_json.get("itemDescription", "未知商品")
                                        
                                        # 如果消息不为空，处理消息
                                        if message_text:
                                            logger.info(f"收到用户 {send_user_name}({from_id}) 的消息: {message_text}")
                                            
                                            # 构建任务数据
                                            task_data = {
                                                "message": msg,  # 原始消息
                                                "send_user_name": send_user_name,
                                                "send_user_id": from_id,
                                                "send_message": message_text,
                                                "item_id": item_id,
                                                "item_description": item_description,
                                                "cid": cid,
                                                "message_id": msg_id if ".PNM" in msg_id else None
                                            }
                                            
                                            # 加入消息队列
                                            self.message_queue.put({
                                                "task_data": task_data,
                                                "websocket": websocket
                                            })
                                except Exception as e:
                                    logger.error(f"解析消息内容时出错: {str(e)}")
            except Exception as e:
                logger.error(f"处理同步包消息时出错: {str(e)}")
                
        # 处理心跳响应
        elif "lwp" in message_data and message_data["lwp"].startswith("/n/r/Heartbeat"):
            try:
                await self.handle_heartbeat_response(message_data)
            except Exception as e:
                logger.error(f"处理心跳响应出错: {str(e)}")
    
    async def main(self):
        """启动闲鱼直播连接主函数"""
        await self.run() 

    def _clean_message_fingerprints_worker(self):
        """定期清理过期的消息指纹缓存"""
        import time
        
        while True:
            try:
                # 每2分钟清理一次
                time.sleep(120)
                
                # 清理过期的缓存
                current_time = time.time()
                expired_fingerprints = []
                
                for fingerprint, timestamp in self.processed_messages.items():
                    if current_time - timestamp > self.processed_window * 3:  # 使用3倍的处理窗口作为过期时间
                        expired_fingerprints.append(fingerprint)
                
                # 删除过期的指纹
                for fingerprint in expired_fingerprints:
                    del self.processed_messages[fingerprint]
                
                if expired_fingerprints:
                    logger.debug(f"已清理 {len(expired_fingerprints)} 个过期消息指纹，当前缓存大小: {len(self.processed_messages)}")
                    
            except Exception as e:
                logger.error(f"清理消息指纹缓存时出错: {e}")
                # 异常后等待30秒再继续
                time.sleep(30) 