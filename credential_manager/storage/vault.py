"""
凭证加密存储实现
"""

import os
import json
import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import base64
import logging

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logging.warning("cryptography library not available, encryption disabled")

logger = logging.getLogger(__name__)


class CredentialVault:
    """
    凭证安全存储库
    支持加密存储和持久化
    """
    
    def __init__(self, 
                 db_path: str = "./data/credentials.db",
                 encryption_enabled: bool = True,
                 encryption_key: str = None):
        """
        初始化存储库
        
        Args:
            db_path: 数据库路径
            encryption_enabled: 是否启用加密
            encryption_key: 加密密钥
        """
        self.db_path = db_path
        self.encryption_enabled = encryption_enabled and CRYPTO_AVAILABLE
        
        # 确保数据目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化加密器
        self.cipher = None
        if self.encryption_enabled:
            self.cipher = self._init_cipher(encryption_key)
        
        # 初始化数据库
        self._init_database()
        
        # 归档目录
        self.archive_dir = Path(db_path).parent / "archived_credentials"
        self.archive_dir.mkdir(exist_ok=True)
        
        logger.info(f"CredentialVault initialized (encryption: {self.encryption_enabled})")
    
    def _init_cipher(self, encryption_key: str = None) -> Optional[Fernet]:
        """初始化加密器"""
        if not CRYPTO_AVAILABLE:
            return None
        
        if encryption_key:
            # 使用提供的密钥
            key = self._derive_key(encryption_key)
        else:
            # 生成或加载密钥
            key = self._get_or_create_key()
        
        return Fernet(key)
    
    def _derive_key(self, password: str) -> bytes:
        """从密码派生密钥"""
        salt = b'credential_manager_salt_v1'  # 固定盐值（生产环境应随机生成）
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def _get_or_create_key(self) -> bytes:
        """获取或创建加密密钥"""
        key_file = Path(self.db_path).parent / ".encryption_key"
        
        if key_file.exists():
            # 加载现有密钥
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # 生成新密钥
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # 设置文件权限（仅限所有者读写）
            os.chmod(key_file, 0o600)
            logger.info(f"Generated new encryption key: {key_file}")
            return key
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建凭证表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS credentials (
                id TEXT PRIMARY KEY,
                service_type TEXT NOT NULL,
                encrypted_value TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                remaining_quota INTEGER DEFAULT 0,
                total_quota INTEGER DEFAULT 0,
                reset_time TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_used TEXT,
                expires_at TEXT,
                source TEXT DEFAULT 'unknown',
                metadata TEXT,
                health_score REAL DEFAULT 0.0
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_service_type 
            ON credentials(service_type)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_status 
            ON credentials(status)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_health_score 
            ON credentials(health_score DESC)
        ''')
        
        # 创建使用历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                credential_id TEXT NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN,
                response_time REAL,
                error_message TEXT,
                FOREIGN KEY (credential_id) REFERENCES credentials(id)
            )
        ''')
        
        # 创建归档表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS archived_credentials (
                id TEXT PRIMARY KEY,
                service_type TEXT NOT NULL,
                masked_value TEXT NOT NULL,
                status TEXT,
                archive_reason TEXT,
                archive_time TEXT DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info(f"Database initialized: {self.db_path}")
    
    def _encrypt(self, data: str) -> str:
        """加密数据"""
        if not self.cipher:
            return data
        
        try:
            encrypted = self.cipher.encrypt(data.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return data
    
    def _decrypt(self, data: str) -> str:
        """解密数据"""
        if not self.cipher:
            return data
        
        try:
            encrypted = base64.b64decode(data.encode())
            decrypted = self.cipher.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return data
    
    def save(self, credential: Any) -> bool:
        """
        保存凭证
        
        Args:
            credential: 凭证对象
            
        Returns:
            是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 加密凭证值
            encrypted_value = self._encrypt(credential.value)
            
            # 序列化元数据
            metadata_json = json.dumps(credential.metadata)
            
            # 插入或更新
            cursor.execute('''
                INSERT OR REPLACE INTO credentials (
                    id, service_type, encrypted_value, status,
                    remaining_quota, total_quota, reset_time,
                    created_at, updated_at, last_used, expires_at,
                    source, metadata, health_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                credential.id,
                credential.service_type.value,
                encrypted_value,
                credential.status.value,
                credential.remaining_quota,
                credential.total_quota,
                credential.reset_time.isoformat() if credential.reset_time else None,
                credential.created_at.isoformat(),
                datetime.now().isoformat(),
                credential.last_used.isoformat() if credential.last_used else None,
                credential.expires_at.isoformat() if credential.expires_at else None,
                credential.source,
                metadata_json,
                credential.calculate_health_score()
            ))
            
            # 记录使用历史
            if credential.metrics.total_requests > 0:
                cursor.execute('''
                    INSERT INTO usage_history (
                        credential_id, success, response_time
                    ) VALUES (?, ?, ?)
                ''', (
                    credential.id,
                    credential.metrics.successful_requests > 0,
                    credential.metrics.last_response_time
                ))
            
            conn.commit()
            conn.close()
            
            logger.debug(f"Saved credential: {credential.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save credential: {e}")
            return False
    
    def load(self, credential_id: str) -> Optional[Dict[str, Any]]:
        """
        加载单个凭证
        
        Args:
            credential_id: 凭证ID
            
        Returns:
            凭证数据字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM credentials WHERE id = ?
            ''', (credential_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return self._row_to_dict(row)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load credential: {e}")
            return None
    
    def load_all(self, service_type: str = None) -> List[Dict[str, Any]]:
        """
        加载所有凭证
        
        Args:
            service_type: 可选的服务类型过滤
            
        Returns:
            凭证数据列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if service_type:
                cursor.execute('''
                    SELECT * FROM credentials 
                    WHERE service_type = ? AND status != 'archived'
                    ORDER BY health_score DESC
                ''', (service_type,))
            else:
                cursor.execute('''
                    SELECT * FROM credentials 
                    WHERE status != 'archived'
                    ORDER BY health_score DESC
                ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            return [self._row_to_dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Failed to load credentials: {e}")
            return []
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        data = dict(row)
        
        # 解密凭证值
        if 'encrypted_value' in data:
            data['value'] = self._decrypt(data['encrypted_value'])
            del data['encrypted_value']
        
        # 解析元数据
        if 'metadata' in data and data['metadata']:
            try:
                data['metadata'] = json.loads(data['metadata'])
            except:
                data['metadata'] = {}
        
        return data
    
    def delete(self, credential_id: str) -> bool:
        """
        删除凭证
        
        Args:
            credential_id: 凭证ID
            
        Returns:
            是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM credentials WHERE id = ?
            ''', (credential_id,))
            
            affected = cursor.rowcount
            conn.commit()
            conn.close()
            
            if affected > 0:
                logger.info(f"Deleted credential: {credential_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete credential: {e}")
            return False
    
    def archive(self, credential: Any) -> bool:
        """
        归档凭证
        
        Args:
            credential: 凭证对象
            
        Returns:
            是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 插入归档记录
            cursor.execute('''
                INSERT INTO archived_credentials (
                    id, service_type, masked_value, status,
                    archive_reason, metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                credential.id,
                credential.service_type.value,
                credential.masked_value,
                credential.status.value,
                credential.metadata.get("archive_reason", "unknown"),
                json.dumps(credential.metadata)
            ))
            
            conn.commit()
            conn.close()
            
            # 保存到归档文件
            archive_file = self.archive_dir / f"archived_{datetime.now().strftime('%Y%m%d')}.jsonl"
            with open(archive_file, 'a', encoding='utf-8') as f:
                archive_data = {
                    "id": credential.id,
                    "service_type": credential.service_type.value,
                    "masked_value": credential.masked_value,
                    "status": credential.status.value,
                    "archive_time": datetime.now().isoformat(),
                    "metadata": credential.metadata
                }
                f.write(json.dumps(archive_data) + '\n')
            
            logger.info(f"Archived credential: {credential.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to archive credential: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 总数统计
            cursor.execute('SELECT COUNT(*) FROM credentials')
            total = cursor.fetchone()[0]
            
            # 按状态统计
            cursor.execute('''
                SELECT status, COUNT(*) 
                FROM credentials 
                GROUP BY status
            ''')
            status_counts = dict(cursor.fetchall())
            
            # 按服务类型统计
            cursor.execute('''
                SELECT service_type, COUNT(*) 
                FROM credentials 
                GROUP BY service_type
            ''')
            service_counts = dict(cursor.fetchall())
            
            # 归档统计
            cursor.execute('SELECT COUNT(*) FROM archived_credentials')
            archived = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "total": total,
                "archived": archived,
                "by_status": status_counts,
                "by_service": service_counts,
                "database_size": os.path.getsize(self.db_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    def cleanup_expired(self) -> int:
        """清理过期凭证"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查找过期凭证
            cursor.execute('''
                SELECT id FROM credentials 
                WHERE expires_at IS NOT NULL 
                AND expires_at < ?
            ''', (datetime.now().isoformat(),))
            
            expired_ids = [row[0] for row in cursor.fetchall()]
            
            if expired_ids:
                # 更新状态为过期
                cursor.executemany('''
                    UPDATE credentials 
                    SET status = 'expired' 
                    WHERE id = ?
                ''', [(id,) for id in expired_ids])
                
                conn.commit()
                logger.info(f"Marked {len(expired_ids)} credentials as expired")
            
            conn.close()
            return len(expired_ids)
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired credentials: {e}")
            return 0