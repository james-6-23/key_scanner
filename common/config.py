import os
import random
from typing import Dict, Optional, List

from dotenv import load_dotenv

from common.Logger import logger

# 只在环境变量不存在时才从.env加载值
load_dotenv(override=False)


class Config:
    # Token配置模式
    USE_EXTERNAL_TOKEN_FILE = os.getenv("USE_EXTERNAL_TOKEN_FILE", "false").lower() in ("true", "1", "yes", "on")
    GITHUB_TOKENS_FILE = os.getenv("GITHUB_TOKENS_FILE", "github_tokens.txt")
    
    # Token管理配置
    TOKEN_AUTO_REMOVE_EXHAUSTED = os.getenv("TOKEN_AUTO_REMOVE_EXHAUSTED", "true").lower() in ("true", "1", "yes", "on")
    TOKEN_MIN_REMAINING_CALLS = int(os.getenv("TOKEN_MIN_REMAINING_CALLS", "10"))
    TOKEN_ARCHIVE_DIR = os.getenv("TOKEN_ARCHIVE_DIR", "./data/archived_tokens")
    
    # 原有的token配置（用于向后兼容）
    GITHUB_TOKENS_STR = os.getenv("GITHUB_TOKENS", "")
    
    @classmethod
    def get_github_tokens(cls) -> List[str]:
        """
        获取GitHub tokens列表
        根据配置自动选择从环境变量或外部文件加载
        """
        tokens = []
        
        if cls.USE_EXTERNAL_TOKEN_FILE:
            # 模式1：从外部文件加载
            if os.path.exists(cls.GITHUB_TOKENS_FILE):
                logger.info(f"📂 Loading tokens from external file: {cls.GITHUB_TOKENS_FILE}")
                try:
                    with open(cls.GITHUB_TOKENS_FILE, 'r', encoding='utf-8') as f:
                        for line in f:
                            token = line.strip()
                            if token and not token.startswith('#'):
                                tokens.append(token)
                    logger.info(f"✅ Loaded {len(tokens)} tokens from file")
                except Exception as e:
                    logger.error(f"❌ Failed to load tokens from file: {e}")
                    # 回退到环境变量
                    if cls.GITHUB_TOKENS_STR:
                        tokens = [token.strip() for token in cls.GITHUB_TOKENS_STR.split(',') if token.strip()]
                        logger.info(f"⚠️ Fallback to env tokens: {len(tokens)} tokens")
            else:
                logger.warning(f"⚠️ Token file not found: {cls.GITHUB_TOKENS_FILE}")
                # 回退到环境变量
                if cls.GITHUB_TOKENS_STR:
                    tokens = [token.strip() for token in cls.GITHUB_TOKENS_STR.split(',') if token.strip()]
                    logger.info(f"⚠️ Fallback to env tokens: {len(tokens)} tokens")
        else:
            # 模式2：从环境变量加载（逗号分隔）
            if cls.GITHUB_TOKENS_STR:
                tokens = [token.strip() for token in cls.GITHUB_TOKENS_STR.split(',') if token.strip()]
                logger.info(f"🔧 Loaded {len(tokens)} tokens from environment variable")
        
        return tokens
    
    # 保持向后兼容
    GITHUB_TOKENS = property(lambda self: Config.get_github_tokens())
    DATA_PATH = os.getenv('DATA_PATH', '/app/data')
    PROXY_LIST_STR = os.getenv("PROXY", "")
    
    # 解析代理列表，支持格式：http://user:pass@host:port,http://host:port,socks5://user:pass@host:port
    PROXY_LIST = []
    if PROXY_LIST_STR:
        for proxy_str in PROXY_LIST_STR.split(','):
            proxy_str = proxy_str.strip()
            if proxy_str:
                PROXY_LIST.append(proxy_str)
    
    # Gemini Balancer配置
    GEMINI_BALANCER_SYNC_ENABLED = os.getenv("GEMINI_BALANCER_SYNC_ENABLED", "false")
    GEMINI_BALANCER_URL = os.getenv("GEMINI_BALANCER_URL", "")
    GEMINI_BALANCER_AUTH = os.getenv("GEMINI_BALANCER_AUTH", "")

    # GPT Load Balancer Configuration
    GPT_LOAD_SYNC_ENABLED = os.getenv("GPT_LOAD_SYNC_ENABLED", "false")
    GPT_LOAD_URL = os.getenv('GPT_LOAD_URL', '')
    GPT_LOAD_AUTH = os.getenv('GPT_LOAD_AUTH', '')
    GPT_LOAD_GROUP_NAME = os.getenv('GPT_LOAD_GROUP_NAME', '')

    # 文件前缀配置
    VALID_KEY_PREFIX = os.getenv("VALID_KEY_PREFIX", "keys/keys_valid_")
    RATE_LIMITED_KEY_PREFIX = os.getenv("RATE_LIMITED_KEY_PREFIX", "keys/key_429_")
    KEYS_SEND_PREFIX = os.getenv("KEYS_SEND_PREFIX", "keys/keys_send_")

    VALID_KEY_DETAIL_PREFIX = os.getenv("VALID_KEY_DETAIL_PREFIX", "logs/keys_valid_detail_")
    RATE_LIMITED_KEY_DETAIL_PREFIX = os.getenv("RATE_LIMITED_KEY_DETAIL_PREFIX", "logs/key_429_detail_")
    KEYS_SEND_DETAIL_PREFIX = os.getenv("KEYS_SEND_DETAIL_PREFIX", "logs/keys_send_detail_")
    
    # 日期范围过滤器配置 (单位：天)
    DATE_RANGE_DAYS = int(os.getenv("DATE_RANGE_DAYS", "730"))  # 默认730天 (约2年)

    # 查询文件路径配置
    QUERIES_FILE = os.getenv("QUERIES_FILE", "queries.txt")

    # 已扫描SHA文件配置
    SCANNED_SHAS_FILE = os.getenv("SCANNED_SHAS_FILE", "scanned_shas.txt")

    # Gemini模型配置
    HAJIMI_CHECK_MODEL = os.getenv("HAJIMI_CHECK_MODEL", "gemini-2.5-flash")

    # 文件路径黑名单配置
    FILE_PATH_BLACKLIST_STR = os.getenv("FILE_PATH_BLACKLIST", "readme,docs,doc/,.md,sample,tutorial")
    FILE_PATH_BLACKLIST = [token.strip().lower() for token in FILE_PATH_BLACKLIST_STR.split(',') if token.strip()]

    @classmethod
    def parse_bool(cls, value: str) -> bool:
        """
        解析布尔值配置，支持多种格式
        
        Args:
            value: 配置值字符串
            
        Returns:
            bool: 解析后的布尔值
        """
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            value = value.strip().lower()
            return value in ('true', '1', 'yes', 'on', 'enabled')
        
        if isinstance(value, int):
            return bool(value)
        
        return False

    @classmethod
    def get_random_proxy(cls) -> Optional[Dict[str, str]]:
        """
        随机获取一个代理配置
        
        Returns:
            Optional[Dict[str, str]]: requests格式的proxies字典，如果未配置则返回None
        """
        if not cls.PROXY_LIST:
            return None
        
        # 随机选择一个代理
        proxy_url = random.choice(cls.PROXY_LIST).strip()
        
        # 返回requests格式的proxies字典
        return {
            'http': proxy_url,
            'https': proxy_url
        }

    @classmethod
    def check(cls) -> bool:
        """
        检查必要的配置是否完整
        
        Returns:
            bool: 配置是否完整
        """
        logger.info("🔍 Checking required configurations...")
        
        errors = []
        
        # 检查GitHub tokens
        tokens = cls.get_github_tokens()
        if not tokens:
            if cls.USE_EXTERNAL_TOKEN_FILE:
                errors.append(f"GitHub tokens not found in file: {cls.GITHUB_TOKENS_FILE}")
            else:
                errors.append("GitHub tokens not found. Please set GITHUB_TOKENS environment variable.")
            logger.error("❌ GitHub tokens: Missing")
        else:
            logger.info(f"✅ GitHub tokens: {len(tokens)} configured")
            if cls.USE_EXTERNAL_TOKEN_FILE:
                logger.info(f"   Source: External file ({cls.GITHUB_TOKENS_FILE})")
            else:
                logger.info(f"   Source: Environment variable")
        
        # 检查Gemini Balancer配置
        if cls.GEMINI_BALANCER_SYNC_ENABLED:
            logger.info(f"✅ Gemini Balancer enabled, URL: {cls.GEMINI_BALANCER_URL}")
            if not cls.GEMINI_BALANCER_AUTH or not cls.GEMINI_BALANCER_URL:
                logger.warning("⚠️ Gemini Balancer Auth or URL Missing (Balancer功能将被禁用)")
            else:
                logger.info(f"✅ Gemini Balancer Auth: ****")
        else:
            logger.info("ℹ️ Gemini Balancer URL: Not configured (Balancer功能将被禁用)")

        # 检查GPT Load Balancer配置
        if cls.parse_bool(cls.GPT_LOAD_SYNC_ENABLED):
            logger.info(f"✅ GPT Load Balancer enabled, URL: {cls.GPT_LOAD_URL}")
            if not cls.GPT_LOAD_AUTH or not cls.GPT_LOAD_URL or not cls.GPT_LOAD_GROUP_NAME:
                logger.warning("⚠️ GPT Load Balancer Auth, URL or Group Name Missing (Load Balancer功能将被禁用)")
            else:
                logger.info(f"✅ GPT Load Balancer Auth: ****")
                logger.info(f"✅ GPT Load Balancer Group Name: {cls.GPT_LOAD_GROUP_NAME}")
        else:
            logger.info("ℹ️ GPT Load Balancer: Not configured (Load Balancer功能将被禁用)")

        if errors:
            logger.error("❌ Configuration check failed:")
            logger.info("Please check your .env file and configuration.")
            return False
        
        logger.info("✅ All required configurations are valid")
        return True


logger.info(f"*" * 30 + " CONFIG START " + "*" * 30)
logger.info(f"TOKEN_MODE: {'External File' if Config.USE_EXTERNAL_TOKEN_FILE else 'Environment Variable'}")
if Config.USE_EXTERNAL_TOKEN_FILE:
    logger.info(f"TOKEN_FILE: {Config.GITHUB_TOKENS_FILE}")
logger.info(f"GITHUB_TOKENS: {len(Config.get_github_tokens())} tokens")
logger.info(f"TOKEN_AUTO_REMOVE: {Config.TOKEN_AUTO_REMOVE_EXHAUSTED}")
logger.info(f"TOKEN_MIN_CALLS: {Config.TOKEN_MIN_REMAINING_CALLS}")
logger.info(f"DATA_PATH: {Config.DATA_PATH}")
logger.info(f"PROXY_LIST: {len(Config.PROXY_LIST)} proxies configured")
logger.info(f"GEMINI_BALANCER_URL: {Config.GEMINI_BALANCER_URL or 'Not configured'}")
logger.info(f"GEMINI_BALANCER_AUTH: {'Configured' if Config.GEMINI_BALANCER_AUTH else 'Not configured'}")
logger.info(f"GEMINI_BALANCER_SYNC_ENABLED: {Config.parse_bool(Config.GEMINI_BALANCER_SYNC_ENABLED)}")
logger.info(f"GPT_LOAD_SYNC_ENABLED: {Config.parse_bool(Config.GPT_LOAD_SYNC_ENABLED)}")
logger.info(f"GPT_LOAD_URL: {Config.GPT_LOAD_URL or 'Not configured'}")
logger.info(f"GPT_LOAD_AUTH: {'Configured' if Config.GPT_LOAD_AUTH else 'Not configured'}")
logger.info(f"GPT_LOAD_GROUP_NAME: {Config.GPT_LOAD_GROUP_NAME or 'Not configured'}")
logger.info(f"VALID_KEY_PREFIX: {Config.VALID_KEY_PREFIX}")
logger.info(f"RATE_LIMITED_KEY_PREFIX: {Config.RATE_LIMITED_KEY_PREFIX}")
logger.info(f"KEYS_SEND_PREFIX: {Config.KEYS_SEND_PREFIX}")
logger.info(f"VALID_KEY_DETAIL_PREFIX: {Config.VALID_KEY_DETAIL_PREFIX}")
logger.info(f"RATE_LIMITED_KEY_DETAIL_PREFIX: {Config.RATE_LIMITED_KEY_DETAIL_PREFIX}")
logger.info(f"KEYS_SEND_DETAIL_PREFIX: {Config.KEYS_SEND_DETAIL_PREFIX}")
logger.info(f"DATE_RANGE_DAYS: {Config.DATE_RANGE_DAYS} days")
logger.info(f"QUERIES_FILE: {Config.QUERIES_FILE}")
logger.info(f"SCANNED_SHAS_FILE: {Config.SCANNED_SHAS_FILE}")
logger.info(f"HAJIMI_CHECK_MODEL: {Config.HAJIMI_CHECK_MODEL}")
logger.info(f"FILE_PATH_BLACKLIST: {len(Config.FILE_PATH_BLACKLIST)} items")
logger.info(f"*" * 30 + " CONFIG END " + "*" * 30)

# 创建全局配置实例
config = Config()
