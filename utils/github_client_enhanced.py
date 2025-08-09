"""
增强版GitHub客户端 - 集成credential_manager
提供与原GitHubClient兼容的接口，同时支持新的智能凭证管理
"""

import base64
import random
import time
from typing import Dict, List, Optional, Any, Tuple

import requests
from common.Logger import logger
from common.config import Config

# 尝试导入credential_manager（如果可用）
try:
    from credential_manager.integration.credential_bridge import (
        CredentialBridge,
        GitHubTokenBridge
    )
    from credential_manager.core.models import ServiceType, CredentialStatus
    CREDENTIAL_MANAGER_AVAILABLE = True
except ImportError:
    CREDENTIAL_MANAGER_AVAILABLE = False
    logger.warning("⚠️ CredentialManager not available, falling back to TokenManager")


class EnhancedGitHubClient:
    """
    增强版GitHub客户端
    支持新的CredentialManager和旧的TokenManager
    """
    
    GITHUB_API_URL = "https://api.github.com/search/code"
    
    def __init__(self, use_credential_manager: bool = None):
        """
        初始化增强版GitHub客户端
        
        Args:
            use_credential_manager: 是否使用新的凭证管理系统
                                  None = 自动检测
                                  True = 强制使用（如果不可用会报错）
                                  False = 强制使用旧系统
        """
        # 自动检测
        if use_credential_manager is None:
            use_credential_manager = CREDENTIAL_MANAGER_AVAILABLE
        
        # 检查可用性
        if use_credential_manager and not CREDENTIAL_MANAGER_AVAILABLE:
            logger.error("❌ CredentialManager requested but not available!")
            logger.info("💡 Run: python fix_credential_manager.py")
            use_credential_manager = False
        
        self.use_credential_manager = use_credential_manager
        self._token_cache = None  # 缓存当前token
        
        if self.use_credential_manager:
            self._init_credential_manager()
        else:
            self._init_token_manager()
    
    def _init_credential_manager(self):
        """初始化CredentialManager"""
        logger.info("🚀 Initializing Enhanced GitHub Client with CredentialManager")
        
        try:
            # 检查是否有现有的github_tokens.txt文件
            tokens_file = Config.GITHUB_TOKENS_FILE if hasattr(Config, 'GITHUB_TOKENS_FILE') else 'github_tokens.txt'
            
            # 优先使用GitHub专用桥接器
            from pathlib import Path
            if Path(tokens_file).exists():
                logger.info(f"📁 Found tokens file: {tokens_file}")
                self.credential_bridge = GitHubTokenBridge(tokens_file=tokens_file)
                
                # 获取状态
                status = self.credential_bridge.get_status()
                logger.info(f"✅ GitHubTokenBridge initialized with {status['total_tokens']} tokens")
            else:
                # 使用通用桥接器
                logger.info("🔍 Using general CredentialBridge with auto-discovery")
                self.credential_bridge = CredentialBridge(
                    auto_discover=True,
                    enable_healing=True
                )
                
                # 如果有环境变量中的tokens，导入它们
                if hasattr(Config, 'GITHUB_TOKENS_STR') and Config.GITHUB_TOKENS_STR:
                    tokens = Config.GITHUB_TOKENS_STR.split(',')
                    for token in tokens:
                        if token.strip():
                            self.credential_bridge.manager.add_credential(
                                service_type=ServiceType.GITHUB,
                                value=token.strip(),
                                metadata={"source": "env"}
                            )
                    logger.info(f"📥 Imported {len(tokens)} tokens from environment")
            
            logger.info("✅ CredentialManager initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize CredentialManager: {e}")
            logger.info("⚠️ Falling back to TokenManager")
            self.use_credential_manager = False
            self._init_token_manager()
    
    def _init_token_manager(self):
        """初始化旧的TokenManager"""
        logger.info("📝 Using legacy TokenManager")
        
        try:
            from utils.token_manager import get_token_manager, init_token_manager
            
            try:
                self.token_manager = get_token_manager()
            except RuntimeError:
                # TokenManager未初始化
                logger.info("🔧 Initializing TokenManager...")
                self.token_manager = init_token_manager(
                    env_tokens=Config.GITHUB_TOKENS_STR if hasattr(Config, 'GITHUB_TOKENS_STR') else None,
                    tokens_file=Config.GITHUB_TOKENS_FILE if hasattr(Config, 'GITHUB_TOKENS_FILE') else 'github_tokens.txt'
                )
            
            token_count = len(self.token_manager.tokens) if hasattr(self.token_manager, 'tokens') else 0
            logger.info(f"✅ TokenManager initialized with {token_count} tokens")
            
        except ImportError:
            logger.error("❌ TokenManager not available!")
            # 最后的备选：直接从配置读取
            self.tokens = Config.get_github_tokens() if hasattr(Config, 'get_github_tokens') else []
            self._token_ptr = 0
            logger.warning(f"⚠️ Using direct token list with {len(self.tokens)} tokens")
    
    def _get_next_token(self) -> Tuple[Optional[str], Optional[Any]]:
        """
        获取下一个可用的token
        
        Returns:
            (token, metadata) - metadata用于状态更新
        """
        if self.use_credential_manager:
            # 使用CredentialManager
            if isinstance(self.credential_bridge, GitHubTokenBridge):
                # GitHub专用桥接器
                token = self.credential_bridge.get_next_token()
                if token:
                    logger.debug(f"🎯 Selected token from GitHubTokenBridge")
                    return token, {"source": "github_bridge"}
            else:
                # 通用桥接器
                cred = self.credential_bridge.get_credential(service_type='github')
                if cred:
                    logger.debug(f"🎯 Selected credential with health score: {cred['health_score']:.1f}")
                    return cred['value'], cred
            
            logger.error("❌ No available credentials from CredentialManager")
            return None, None
            
        else:
            # 使用旧系统
            if hasattr(self, 'token_manager'):
                result = self.token_manager.get_next_token()
                if result:
                    return result[0], {"source": "token_manager"}
            elif hasattr(self, 'tokens'):
                # 直接token列表
                if self.tokens:
                    token = self.tokens[self._token_ptr % len(self.tokens)]
                    self._token_ptr += 1
                    return token, {"source": "direct"}
            
            return None, None
    
    def _update_token_status(self, token: str, metadata: Any, headers: Dict, success: bool):
        """更新token状态"""
        if self.use_credential_manager:
            if isinstance(self.credential_bridge, GitHubTokenBridge):
                # GitHub专用桥接器
                if not success and headers.get('X-RateLimit-Remaining') == '0':
                    self.credential_bridge.mark_token_exhausted(token)
                    logger.warning(f"⚠️ Token marked as exhausted")
            else:
                # 通用桥接器
                self.credential_bridge.manager.update_credential_status(
                    credential_value=token,
                    headers=headers,
                    success=success
                )
        else:
            # 旧系统
            if hasattr(self, 'token_manager'):
                self.token_manager.update_token_status(token, headers, success)
    
    def search_for_keys(self, query: str, max_retries: int = 5) -> Dict[str, Any]:
        """
        搜索GitHub代码
        完全兼容原GitHubClient.search_for_keys接口
        """
        all_items = []
        total_count = 0
        expected_total = None
        pages_processed = 0
        
        for page in range(1, 11):  # 最多10页
            page_success = False
            page_result = None
            
            for attempt in range(1, max_retries + 1):
                # 获取token
                token, metadata = self._get_next_token()
                if not token:
                    logger.error("❌ No tokens available")
                    break
                
                headers = {
                    "Accept": "application/vnd.github.v3+json",
                    "Authorization": f"token {token}",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                }
                
                params = {
                    "q": query,
                    "per_page": 100,
                    "page": page
                }
                
                try:
                    # 获取proxy
                    proxies = Config.get_random_proxy() if hasattr(Config, 'get_random_proxy') else None
                    
                    response = requests.get(
                        self.GITHUB_API_URL,
                        headers=headers,
                        params=params,
                        timeout=30,
                        proxies=proxies
                    )
                    
                    # 更新token状态
                    self._update_token_status(
                        token,
                        metadata,
                        dict(response.headers),
                        success=response.status_code == 200
                    )
                    
                    # 检查速率限制
                    rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
                    if rate_limit_remaining and int(rate_limit_remaining) < 3:
                        logger.warning(f"⚠️ Rate limit low: {rate_limit_remaining} remaining")
                    
                    response.raise_for_status()
                    page_result = response.json()
                    page_success = True
                    break
                    
                except requests.exceptions.HTTPError as e:
                    status = e.response.status_code if e.response else None
                    
                    # 更新失败状态
                    self._update_token_status(
                        token,
                        metadata,
                        dict(e.response.headers) if e.response else {},
                        success=False
                    )
                    
                    if status in (403, 429):
                        # 速率限制
                        wait = min(2 ** attempt + random.uniform(0, 1), 60)
                        if attempt >= 3:
                            logger.warning(f"❌ Rate limit hit (attempt {attempt}/{max_retries})")
                        time.sleep(wait)
                        continue
                    else:
                        if attempt == max_retries:
                            logger.error(f"❌ HTTP {status} error on page {page}")
                        time.sleep(2 ** attempt)
                        
                except Exception as e:
                    logger.error(f"❌ Request failed: {e}")
                    self._update_token_status(token, metadata, {}, False)
                    time.sleep(min(2 ** attempt, 30))
            
            if not page_success or not page_result:
                if page == 1:
                    logger.error(f"❌ First page failed for query: {query[:50]}...")
                break
            
            pages_processed += 1
            
            if page == 1:
                total_count = page_result.get("total_count", 0)
                expected_total = min(total_count, 1000)
            
            items = page_result.get("items", [])
            if not items:
                break
            
            all_items.extend(items)
            
            if expected_total and len(all_items) >= expected_total:
                break
            
            # 页面间延迟
            if page < 10:
                time.sleep(random.uniform(0.5, 1.5))
        
        # 记录结果
        logger.info(f"🔍 Search complete: {query[:50]}... | Pages: {pages_processed} | Items: {len(all_items)}/{expected_total or '?'}")
        
        return {
            "total_count": total_count,
            "incomplete_results": len(all_items) < expected_total if expected_total else False,
            "items": all_items
        }
    
    async def search_repositories(self, query: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        搜索GitHub仓库
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            
        Returns:
            仓库列表
        """
        repositories = []
        per_page = min(100, max_results)
        pages = (max_results + per_page - 1) // per_page
        
        for page in range(1, pages + 1):
            # 获取token
            token, metadata = self._get_next_token()
            if not token:
                logger.error("❌ No tokens available for repository search")
                break
            
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {token}",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }
            
            params = {
                "q": query,
                "per_page": per_page,
                "page": page,
                "sort": "stars",
                "order": "desc"
            }
            
            try:
                proxies = Config.get_random_proxy() if hasattr(Config, 'get_random_proxy') else None
                
                response = requests.get(
                    "https://api.github.com/search/repositories",
                    headers=headers,
                    params=params,
                    timeout=30,
                    proxies=proxies
                )
                
                # 更新token状态
                self._update_token_status(
                    token,
                    metadata,
                    dict(response.headers),
                    success=response.status_code == 200
                )
                
                response.raise_for_status()
                data = response.json()
                
                items = data.get("items", [])
                repositories.extend(items)
                
                if len(repositories) >= max_results:
                    break
                
                # 页面间延迟
                if page < pages:
                    time.sleep(random.uniform(0.5, 1.5))
                    
            except Exception as e:
                logger.error(f"❌ Failed to search repositories: {e}")
                self._update_token_status(token, metadata, {}, False)
                break
        
        return repositories[:max_results]
    
    async def search_in_repository(self, repo_name: str, query: str,
                                  file_extensions: List[str] = None) -> List[Dict[str, Any]]:
        """
        在仓库中搜索文件
        
        Args:
            repo_name: 仓库全名 (owner/repo)
            query: 搜索查询
            file_extensions: 文件扩展名列表
            
        Returns:
            文件列表
        """
        files = []
        
        # 构建查询
        search_query = f"{query} repo:{repo_name}"
        
        # 添加文件扩展名过滤
        if file_extensions:
            ext_query = " OR ".join([f"extension:{ext.lstrip('.')}" for ext in file_extensions])
            search_query = f"{search_query} ({ext_query})"
        
        # 使用代码搜索API
        result = self.search_for_keys(search_query, max_retries=3)
        
        if result and "items" in result:
            for item in result["items"]:
                file_info = {
                    "path": item.get("path", ""),
                    "html_url": item.get("html_url", ""),
                    "repository": item.get("repository", {}),
                    "sha": item.get("sha", ""),
                    "score": item.get("score", 0)
                }
                files.append(file_info)
        
        return files
    
    def get_file_content(self, item: Dict[str, Any]) -> Optional[str]:
        """
        获取文件内容
        完全兼容原GitHubClient.get_file_content接口
        """
        repo_full_name = item["repository"]["full_name"]
        file_path = item["path"]
        
        metadata_url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}"
        
        # 获取token
        token, token_metadata = self._get_next_token()
        if not token:
            logger.error("❌ No tokens available for file content")
            return None
        
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {token}"
        }
        
        try:
            proxies = Config.get_random_proxy() if hasattr(Config, 'get_random_proxy') else None
            
            logger.info(f"🔍 Fetching: {metadata_url}")
            response = requests.get(metadata_url, headers=headers, proxies=proxies, timeout=30)
            
            # 更新token状态
            self._update_token_status(
                token,
                token_metadata,
                dict(response.headers),
                success=response.status_code == 200
            )
            
            response.raise_for_status()
            file_metadata = response.json()
            
            # 尝试base64解码
            encoding = file_metadata.get("encoding")
            content = file_metadata.get("content")
            
            if encoding == "base64" and content:
                try:
                    return base64.b64decode(content).decode('utf-8')
                except Exception as e:
                    logger.warning(f"⚠️ Failed to decode base64: {e}")
            
            # 使用download_url
            download_url = file_metadata.get("download_url")
            if download_url:
                content_response = requests.get(download_url, headers=headers, proxies=proxies, timeout=30)
                content_response.raise_for_status()
                return content_response.text
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch file content: {e}")
            self._update_token_status(token, token_metadata, {}, False)
            return None
    
    async def get_file_content(self, repo_name: str, file_path: str) -> Optional[str]:
        """
        获取文件内容（异步版本）
        
        Args:
            repo_name: 仓库全名
            file_path: 文件路径
            
        Returns:
            文件内容
        """
        # 构造item格式以复用现有方法
        item = {
            "repository": {"full_name": repo_name},
            "path": file_path
        }
        return self.get_file_content(item)
    
    def get_token_status(self) -> Dict[str, Any]:
        """获取token/凭证状态"""
        if self.use_credential_manager:
            if isinstance(self.credential_bridge, GitHubTokenBridge):
                return self.credential_bridge.get_status()
            else:
                health_report = self.credential_bridge.get_health_report()
                return {
                    "system": "CredentialManager",
                    "total_tokens": len(health_report.get('credentials', [])),
                    "summary": health_report.get('summary', {})
                }
        else:
            if hasattr(self, 'token_manager'):
                return self.token_manager.get_status_summary()
            else:
                return {
                    "system": "direct",
                    "total_tokens": len(self.tokens) if hasattr(self, 'tokens') else 0
                }
    
    @staticmethod
    def create_instance(tokens: Optional[List[str]] = None, 
                       use_token_manager: bool = True,
                       use_credential_manager: Optional[bool] = None) -> 'EnhancedGitHubClient':
        """
        创建实例（兼容原接口）
        
        Args:
            tokens: token列表（已废弃，保留用于兼容）
            use_token_manager: 是否使用TokenManager（已废弃）
            use_credential_manager: 是否使用CredentialManager
        """
        # 如果明确指定了use_credential_manager，使用它
        # 否则根据use_token_manager决定（False = 使用credential_manager）
        if use_credential_manager is None:
            use_credential_manager = None  # 自动检测
        
        return EnhancedGitHubClient(use_credential_manager)


# 向后兼容：如果原代码导入GitHubClient，重定向到EnhancedGitHubClient
GitHubClient = EnhancedGitHubClient