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

from utils.xianyu_utils import generate_mid, generate_uuid, trans_cookies, generate_device_id, decrypt
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
            if not token_info or 'data' not in token_info or 'accessToken' not in token_info['data']:
                logger.error(f"获取token失败: {token_info}")
                raise ValueError("获取token失败")
                
            token = token_info['data']['accessToken']
            
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
            
            # 构建处理任务数据
            task_data = {
                "message": message,  # 原始消息
                "send_user_name": send_user_name,
                "send_user_id": send_user_id,
                "send_message": send_message,
                "item_id": item_id,
                "item_description": item_description,
                "cid": cid,
                "message_id": message_id
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
            async with websockets.connect(self.base_url, extra_headers=headers) as ws:
                self.ws = ws
                logger.info("WebSocket连接已建立")
                
                # 初始化连接
                await self.init(ws)
                
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
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket连接已关闭")
            if self.heartbeat_task:
                self.heartbeat_task.cancel()
                try:
                    await self.heartbeat_task
                except asyncio.CancelledError:
                    pass
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
            
    async def run(self):
        """运行WebSocket客户端，自动重连"""
        while True:
            try:
                await self.connect()
            except Exception as e:
                logger.error(f"运行WebSocket客户端时出错: {e}")
            
            # 重连延迟
            logger.info("5秒后尝试重新连接...")
            await asyncio.sleep(5)

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
    
    def _message_worker(self):
        """
        消息处理工作线程函数
        从队列中获取消息并处理
        """
        while True:
            try:
                # 从队列中获取消息
                message_data = self.message_queue.get()
                if message_data is None:  # 结束信号
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
                
                logger.info(f"处理用户 {send_user_name} 的消息: {send_message}")
                
                # 添加用户消息到上下文
                self.context_manager.add_message(send_user_id, item_id, "user", send_message)
                
                # 获取完整的对话上下文
                context = self.context_manager.get_context(send_user_id, item_id)
                
                # 生成回复
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
                # 标记任务完成
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