"""
聊天上下文管理模块
负责存储和检索用户与商品之间的对话历史
"""

import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from loguru import logger


class ChatContextManager:
    """
    聊天上下文管理器
    
    负责存储和检索用户与商品之间的对话历史，使用SQLite数据库进行持久化存储。
    支持按用户ID和商品ID检索对话历史，以及清理过期的历史记录。
    """
    
    def __init__(self, max_history: int = 100, db_path: str = "data/chat_history.db"):
        """
        初始化聊天上下文管理器
        
        Args:
            max_history: 每个对话保留的最大消息数
            db_path: SQLite数据库文件路径
        """
        self.max_history = max_history
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self) -> None:
        """初始化数据库表结构"""
        # 确保数据库目录存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建消息表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建索引以加速查询
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_item ON messages (user_id, item_id)
        ''')
        
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp ON messages (timestamp)
        ''')
        
        # 创建议价次数表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS bargain_counts (
            user_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, item_id)
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"聊天历史数据库初始化完成: {self.db_path}")
        
    def add_message(self, user_id: str, item_id: str, role: str, content: str) -> None:
        """
        添加新消息到对话历史
        
        Args:
            user_id: 用户ID
            item_id: 商品ID
            role: 消息角色 (user/assistant)
            content: 消息内容
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 插入新消息
            cursor.execute(
                "INSERT INTO messages (user_id, item_id, role, content, timestamp) VALUES (?, ?, ?, ?, ?)",
                (user_id, item_id, role, content, datetime.now().isoformat())
            )
            
            # 检查是否需要清理旧消息
            cursor.execute(
                """
                SELECT id FROM messages 
                WHERE user_id = ? AND item_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?, 1
                """, 
                (user_id, item_id, self.max_history)
            )
            
            oldest_to_keep = cursor.fetchone()
            if oldest_to_keep:
                cursor.execute(
                    "DELETE FROM messages WHERE user_id = ? AND item_id = ? AND id < ?",
                    (user_id, item_id, oldest_to_keep[0])
                )
            
            conn.commit()
            logger.debug(f"已添加用户 {user_id} 商品 {item_id} 的{role}消息")
        except Exception as e:
            logger.error(f"添加消息到数据库时出错: {e}")
            conn.rollback()
        finally:
            conn.close()
        
    def increment_bargain_count(self, user_id: str, item_id: str) -> None:
        """
        增加用户对特定商品的议价次数
        
        Args:
            user_id: 用户ID
            item_id: 商品ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 使用UPSERT语法（SQLite 3.24.0及以上版本支持）
            cursor.execute(
                """
                INSERT INTO bargain_counts (user_id, item_id, count, last_updated)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(user_id, item_id) 
                DO UPDATE SET count = count + 1, last_updated = ?
                """,
                (user_id, item_id, datetime.now().isoformat(), datetime.now().isoformat())
            )
            
            conn.commit()
            logger.debug(f"用户 {user_id} 商品 {item_id} 议价次数已增加")
        except Exception as e:
            logger.error(f"增加议价次数时出错: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_bargain_count(self, user_id: str, item_id: str) -> int:
        """
        获取用户对特定商品的议价次数
        
        Args:
            user_id: 用户ID
            item_id: 商品ID
            
        Returns:
            int: 议价次数
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT count FROM bargain_counts WHERE user_id = ? AND item_id = ?",
                (user_id, item_id)
            )
            
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            logger.error(f"获取议价次数时出错: {e}")
            return 0
        finally:
            conn.close()
        
    def get_context(self, user_id: str, item_id: str) -> List[Dict[str, str]]:
        """
        获取特定用户和商品的对话历史
        
        Args:
            user_id: 用户ID
            item_id: 商品ID
            
        Returns:
            list: 包含对话历史的列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                SELECT role, content FROM messages 
                WHERE user_id = ? AND item_id = ? 
                ORDER BY timestamp ASC
                LIMIT ?
                """, 
                (user_id, item_id, self.max_history)
            )
            
            messages = [{"role": role, "content": content} for role, content in cursor.fetchall()]
            
            # 获取议价次数并添加到上下文中
            bargain_count = self.get_bargain_count(user_id, item_id)
            if bargain_count > 0:
                # 添加一条系统消息，包含议价次数信息
                messages.append({
                    "role": "system", 
                    "content": f"议价次数: {bargain_count}"
                })
            
            logger.debug(f"已获取用户 {user_id} 商品 {item_id} 的对话历史，共 {len(messages)} 条消息")
            return messages
        except Exception as e:
            logger.error(f"获取对话历史时出错: {e}")
            return []
        finally:
            conn.close()
    
    def get_user_items(self, user_id: str) -> List[str]:
        """
        获取用户交互过的所有商品ID
        
        Args:
            user_id: 用户ID
            
        Returns:
            list: 商品ID列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT DISTINCT item_id FROM messages WHERE user_id = ?", 
                (user_id,)
            )
            
            items = [item[0] for item in cursor.fetchall()]
            return items
        except Exception as e:
            logger.error(f"获取用户商品列表时出错: {e}")
            return []
        finally:
            conn.close()
    
    def get_recent_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取最近活跃的用户
        
        Args:
            limit: 返回的用户数量上限
            
        Returns:
            list: 包含用户信息的字典列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                """
                SELECT user_id, MAX(timestamp) as last_active
                FROM messages
                GROUP BY user_id
                ORDER BY last_active DESC
                LIMIT ?
                """,
                (limit,)
            )
            
            users = [
                {
                    "user_id": user_id,
                    "last_active": last_active
                } 
                for user_id, last_active in cursor.fetchall()
            ]
            return users
        except Exception as e:
            logger.error(f"获取最近用户列表时出错: {e}")
            return []
        finally:
            conn.close()
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        获取用户统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            dict: 用户统计信息字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {
            "user_id": user_id,
            "total_messages": 0,
            "first_interaction": None,
            "last_interaction": None,
            "items_count": 0,
            "bargain_items": 0,
            "max_bargain_count": 0
        }
        
        try:
            # 获取消息统计
            cursor.execute(
                """
                SELECT COUNT(*) as msg_count, 
                       MIN(timestamp) as first_time,
                       MAX(timestamp) as last_time
                FROM messages
                WHERE user_id = ?
                """,
                (user_id,)
            )
            
            row = cursor.fetchone()
            if row and row[0] > 0:
                stats["total_messages"] = row[0]
                stats["first_interaction"] = row[1]
                stats["last_interaction"] = row[2]
            
            # 获取交互商品数量
            cursor.execute(
                "SELECT COUNT(DISTINCT item_id) FROM messages WHERE user_id = ?",
                (user_id,)
            )
            
            stats["items_count"] = cursor.fetchone()[0]
            
            # 获取议价商品统计
            cursor.execute(
                """
                SELECT COUNT(*) as bargain_items, MAX(count) as max_count
                FROM bargain_counts
                WHERE user_id = ?
                """,
                (user_id,)
            )
            
            row = cursor.fetchone()
            if row:
                stats["bargain_items"] = row[0]
                stats["max_bargain_count"] = row[1]
            
            return stats
        except Exception as e:
            logger.error(f"获取用户统计信息时出错: {e}")
            return stats
        finally:
            conn.close()
    
    def clear_history(self, days_to_keep: int = 30) -> None:
        """
        清理旧的聊天记录
        
        Args:
            days_to_keep: 保留多少天内的消息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 计算截止日期
            cutoff_date = (datetime.now() - datetime.timedelta(days=days_to_keep)).isoformat()
            
            # 删除旧消息
            cursor.execute(
                "DELETE FROM messages WHERE timestamp < ?",
                (cutoff_date,)
            )
            
            deleted_count = cursor.rowcount
            
            # 删除没有对应消息的议价记录
            cursor.execute(
                """
                DELETE FROM bargain_counts 
                WHERE NOT EXISTS (
                    SELECT 1 FROM messages 
                    WHERE messages.user_id = bargain_counts.user_id 
                    AND messages.item_id = bargain_counts.item_id
                )
                """
            )
            
            deleted_bargains = cursor.rowcount
            
            conn.commit()
            logger.info(f"清理完成: 删除了 {deleted_count} 条旧消息和 {deleted_bargains} 条无效议价记录")
        except Exception as e:
            logger.error(f"清理历史记录时出错: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """
        备份数据库
        
        Args:
            backup_path: 备份文件路径，默认为原路径加上时间戳
            
        Returns:
            bool: 备份是否成功
        """
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_path}_{timestamp}.bak"
        
        conn = None
        backup_conn = None
        
        try:
            # 连接原数据库
            conn = sqlite3.connect(self.db_path)
            
            # 创建备份数据库
            backup_conn = sqlite3.connect(backup_path)
            
            # 执行备份
            conn.backup(backup_conn)
            
            logger.info(f"数据库备份成功: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"数据库备份失败: {e}")
            return False
        finally:
            if conn:
                conn.close()
            if backup_conn:
                backup_conn.close() 