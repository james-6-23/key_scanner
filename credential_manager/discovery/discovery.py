"""
凭证发现引擎 - 自动发现和导入凭证
"""

import os
import re
import json
import yaml
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import configparser
import ast
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredCredential:
    """发现的凭证"""
    value: str
    source: str
    source_type: str  # file, env, config, etc.
    service_type: Optional[str] = None
    confidence: float = 0.0  # 0-1 置信度
    metadata: Dict[str, Any] = field(default_factory=dict)
    discovered_at: datetime = field(default_factory=datetime.now)


class CredentialPattern:
    """凭证模式定义"""
    
    # GitHub Token模式
    GITHUB_PATTERNS = [
        (r'ghp_[a-zA-Z0-9]{36}', 'github_personal', 0.95),  # Personal access token
        (r'gho_[a-zA-Z0-9]{36}', 'github_oauth', 0.95),     # OAuth access token
        (r'ghu_[a-zA-Z0-9]{36}', 'github_user', 0.95),      # User-to-server token
        (r'ghs_[a-zA-Z0-9]{36}', 'github_server', 0.95),    # Server-to-server token
        (r'ghr_[a-zA-Z0-9]{36}', 'github_refresh', 0.95),   # Refresh token
        (r'github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}', 'github_fine_grained', 0.95),  # Fine-grained PAT
    ]
    
    # OpenAI API Key模式
    OPENAI_PATTERNS = [
        (r'sk-[a-zA-Z0-9]{48}', 'openai_api_key', 0.9),
        (r'sk-proj-[a-zA-Z0-9]{48}', 'openai_project_key', 0.95),
    ]
    
    # AWS模式
    AWS_PATTERNS = [
        (r'AKIA[0-9A-Z]{16}', 'aws_access_key', 0.85),
        (r'[a-zA-Z0-9/+=]{40}', 'aws_secret_key', 0.3),  # 低置信度，需要上下文
    ]
    
    # 通用API Key模式
    GENERIC_PATTERNS = [
        (r'[a-zA-Z0-9_-]{32,}', 'generic_api_key', 0.2),  # 非常低的置信度
        (r'Bearer [a-zA-Z0-9_.-]+', 'bearer_token', 0.7),
    ]
    
    @classmethod
    def get_all_patterns(cls) -> List[Tuple[str, str, float]]:
        """获取所有模式"""
        patterns = []
        patterns.extend(cls.GITHUB_PATTERNS)
        patterns.extend(cls.OPENAI_PATTERNS)
        patterns.extend(cls.AWS_PATTERNS)
        patterns.extend(cls.GENERIC_PATTERNS)
        return patterns


class CredentialScanner(ABC):
    """凭证扫描器基类"""
    
    @abstractmethod
    def scan(self) -> List[DiscoveredCredential]:
        """执行扫描"""
        pass
    
    def validate_credential(self, credential: str, service_type: str) -> bool:
        """验证凭证格式"""
        patterns = {
            'github': r'^(ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)',
            'openai': r'^sk-',
            'aws': r'^AKIA',
        }
        
        for service, pattern in patterns.items():
            if service in service_type.lower():
                return bool(re.match(pattern, credential))
        
        return True  # 默认认为有效


class FileScanner(CredentialScanner):
    """文件扫描器"""
    
    def __init__(self, 
                 paths: List[str],
                 extensions: Optional[List[str]] = None,
                 exclude_patterns: Optional[List[str]] = None):
        """
        初始化文件扫描器
        
        Args:
            paths: 要扫描的路径列表
            extensions: 要扫描的文件扩展名
            exclude_patterns: 要排除的文件模式
        """
        self.paths = paths
        self.extensions = extensions or [
            '.env', '.ini', '.cfg', '.conf', '.config',
            '.json', '.yaml', '.yml', '.toml',
            '.txt', '.key', '.pem', '.credentials'
        ]
        self.exclude_patterns = exclude_patterns or [
            '*.pyc', '__pycache__', '.git', 'node_modules',
            '*.log', '*.tmp', '*.bak'
        ]
        
    def scan(self) -> List[DiscoveredCredential]:
        """扫描文件系统"""
        discovered = []
        
        for path_str in self.paths:
            path = Path(path_str)
            if not path.exists():
                logger.warning(f"Path does not exist: {path}")
                continue
                
            if path.is_file():
                discovered.extend(self._scan_file(path))
            else:
                discovered.extend(self._scan_directory(path))
                
        return discovered
        
    def _scan_directory(self, directory: Path) -> List[DiscoveredCredential]:
        """扫描目录"""
        discovered = []
        
        for file_path in directory.rglob('*'):
            # 检查是否应该排除
            if self._should_exclude(file_path):
                continue
                
            # 检查扩展名
            if not any(str(file_path).endswith(ext) for ext in self.extensions):
                continue
                
            if file_path.is_file():
                discovered.extend(self._scan_file(file_path))
                
        return discovered
        
    def _scan_file(self, file_path: Path) -> List[DiscoveredCredential]:
        """扫描单个文件"""
        discovered = []
        
        try:
            # 根据文件类型选择解析方法
            if file_path.suffix in ['.json']:
                discovered.extend(self._scan_json_file(file_path))
            elif file_path.suffix in ['.yaml', '.yml']:
                discovered.extend(self._scan_yaml_file(file_path))
            elif file_path.suffix in ['.ini', '.cfg', '.conf']:
                discovered.extend(self._scan_ini_file(file_path))
            elif file_path.name.startswith('.env'):
                discovered.extend(self._scan_env_file(file_path))
            else:
                discovered.extend(self._scan_text_file(file_path))
                
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {e}")
            
        return discovered
        
    def _scan_text_file(self, file_path: Path) -> List[DiscoveredCredential]:
        """扫描文本文件"""
        discovered = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # 使用所有模式扫描
            for pattern, service_type, confidence in CredentialPattern.get_all_patterns():
                matches = re.findall(pattern, content)
                for match in matches:
                    if self.validate_credential(match, service_type):
                        discovered.append(DiscoveredCredential(
                            value=match,
                            source=str(file_path),
                            source_type='file',
                            service_type=service_type,
                            confidence=confidence,
                            metadata={'line': self._find_line_number(content, match)}
                        ))
                        
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            
        return discovered
        
    def _scan_json_file(self, file_path: Path) -> List[DiscoveredCredential]:
        """扫描JSON文件"""
        discovered = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 递归搜索JSON结构
            discovered.extend(self._search_dict(data, str(file_path), 'json'))
            
        except Exception as e:
            logger.error(f"Error parsing JSON file {file_path}: {e}")
            
        return discovered
        
    def _scan_yaml_file(self, file_path: Path) -> List[DiscoveredCredential]:
        """扫描YAML文件"""
        discovered = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            if data:
                discovered.extend(self._search_dict(data, str(file_path), 'yaml'))
                
        except Exception as e:
            logger.error(f"Error parsing YAML file {file_path}: {e}")
            
        return discovered
        
    def _scan_ini_file(self, file_path: Path) -> List[DiscoveredCredential]:
        """扫描INI配置文件"""
        discovered = []
        
        try:
            config = configparser.ConfigParser()
            config.read(file_path)
            
            for section in config.sections():
                for key, value in config.items(section):
                    # 检查键名是否包含凭证相关关键词
                    if any(keyword in key.lower() for keyword in 
                           ['token', 'key', 'secret', 'password', 'api', 'credential']):
                        
                        # 检查值是否匹配凭证模式
                        for pattern, service_type, confidence in CredentialPattern.get_all_patterns():
                            if re.match(pattern, value):
                                discovered.append(DiscoveredCredential(
                                    value=value,
                                    source=str(file_path),
                                    source_type='config',
                                    service_type=service_type,
                                    confidence=confidence * 1.2,  # 配置文件中的置信度更高
                                    metadata={'section': section, 'key': key}
                                ))
                                
        except Exception as e:
            logger.error(f"Error parsing INI file {file_path}: {e}")
            
        return discovered
        
    def _scan_env_file(self, file_path: Path) -> List[DiscoveredCredential]:
        """扫描.env文件"""
        discovered = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        
                        # 检查环境变量名
                        if any(keyword in key.upper() for keyword in 
                               ['TOKEN', 'KEY', 'SECRET', 'API', 'CREDENTIAL']):
                            
                            # 检查值
                            for pattern, service_type, confidence in CredentialPattern.get_all_patterns():
                                if re.match(pattern, value):
                                    discovered.append(DiscoveredCredential(
                                        value=value,
                                        source=str(file_path),
                                        source_type='env',
                                        service_type=service_type,
                                        confidence=confidence * 1.3,  # .env文件置信度更高
                                        metadata={'variable': key, 'line': line_num}
                                    ))
                                    
        except Exception as e:
            logger.error(f"Error parsing env file {file_path}: {e}")
            
        return discovered
        
    def _search_dict(self, data: Any, source: str, source_type: str) -> List[DiscoveredCredential]:
        """递归搜索字典/列表结构"""
        discovered = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                # 检查键名
                if any(keyword in str(key).lower() for keyword in 
                       ['token', 'key', 'secret', 'api', 'credential']):
                    
                    if isinstance(value, str):
                        # 检查值
                        for pattern, service_type, confidence in CredentialPattern.get_all_patterns():
                            if re.match(pattern, value):
                                discovered.append(DiscoveredCredential(
                                    value=value,
                                    source=source,
                                    source_type=source_type,
                                    service_type=service_type,
                                    confidence=confidence,
                                    metadata={'key': key}
                                ))
                                
                # 递归搜索
                discovered.extend(self._search_dict(value, source, source_type))
                
        elif isinstance(data, list):
            for item in data:
                discovered.extend(self._search_dict(item, source, source_type))
                
        return discovered
        
    def _should_exclude(self, path: Path) -> bool:
        """检查是否应该排除路径"""
        path_str = str(path)
        for pattern in self.exclude_patterns:
            if pattern in path_str:
                return True
        return False
        
    def _find_line_number(self, content: str, match: str) -> int:
        """查找匹配内容的行号"""
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if match in line:
                return i
        return 0


class EnvironmentScanner(CredentialScanner):
    """环境变量扫描器"""
    
    def scan(self) -> List[DiscoveredCredential]:
        """扫描环境变量"""
        discovered = []
        
        # 要检查的环境变量名称模式
        env_patterns = [
            'TOKEN', 'KEY', 'SECRET', 'API', 'CREDENTIAL',
            'PASSWORD', 'AUTH', 'ACCESS'
        ]
        
        for env_name, env_value in os.environ.items():
            # 检查环境变量名
            if any(pattern in env_name.upper() for pattern in env_patterns):
                # 检查值
                for pattern, service_type, confidence in CredentialPattern.get_all_patterns():
                    if re.match(pattern, env_value):
                        discovered.append(DiscoveredCredential(
                            value=env_value,
                            source='environment',
                            source_type='env_var',
                            service_type=service_type,
                            confidence=confidence * 1.1,  # 环境变量置信度略高
                            metadata={'variable': env_name}
                        ))
                        
        return discovered


class CodeScanner(CredentialScanner):
    """代码扫描器 - 扫描源代码中的硬编码凭证"""
    
    def __init__(self, paths: List[str], languages: Optional[List[str]] = None):
        """
        初始化代码扫描器
        
        Args:
            paths: 要扫描的代码路径
            languages: 要扫描的编程语言
        """
        self.paths = paths
        self.languages = languages or ['python', 'javascript', 'java', 'go', 'ruby']
        self.file_extensions = {
            'python': ['.py'],
            'javascript': ['.js', '.ts', '.jsx', '.tsx'],
            'java': ['.java'],
            'go': ['.go'],
            'ruby': ['.rb']
        }
        
    def scan(self) -> List[DiscoveredCredential]:
        """扫描代码文件"""
        discovered = []
        
        for path_str in self.paths:
            path = Path(path_str)
            if not path.exists():
                continue
                
            if path.is_file():
                discovered.extend(self._scan_code_file(path))
            else:
                for lang in self.languages:
                    for ext in self.file_extensions.get(lang, []):
                        for file_path in path.rglob(f'*{ext}'):
                            discovered.extend(self._scan_code_file(file_path))
                            
        return discovered
        
    def _scan_code_file(self, file_path: Path) -> List[DiscoveredCredential]:
        """扫描单个代码文件"""
        discovered = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # 查找字符串字面量
            string_patterns = [
                r'"([^"]*)"',  # 双引号字符串
                r"'([^']*)'",  # 单引号字符串
                r'`([^`]*)`',  # 模板字符串
            ]
            
            for string_pattern in string_patterns:
                matches = re.findall(string_pattern, content)
                for match in matches:
                    # 检查是否匹配凭证模式
                    for pattern, service_type, confidence in CredentialPattern.get_all_patterns():
                        if re.match(pattern, match):
                            discovered.append(DiscoveredCredential(
                                value=match,
                                source=str(file_path),
                                source_type='code',
                                service_type=service_type,
                                confidence=confidence * 0.8,  # 代码中的置信度较低
                                metadata={'line': self._find_line_number(content, match)}
                            ))
                            
        except Exception as e:
            logger.error(f"Error scanning code file {file_path}: {e}")
            
        return discovered
        
    def _find_line_number(self, content: str, match: str) -> int:
        """查找匹配内容的行号"""
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if match in line:
                return i
        return 0


class CredentialDiscoveryEngine:
    """凭证发现引擎主类"""
    
    def __init__(self):
        """初始化发现引擎"""
        self.scanners: List[CredentialScanner] = []
        self.discovered_credentials: List[DiscoveredCredential] = []
        self.filters: List[callable] = []
        
    def add_scanner(self, scanner: CredentialScanner):
        """添加扫描器"""
        self.scanners.append(scanner)
        logger.info(f"Added scanner: {scanner.__class__.__name__}")
        
    def add_filter(self, filter_func: callable):
        """添加过滤器"""
        self.filters.append(filter_func)
        
    def discover(self) -> List[DiscoveredCredential]:
        """执行发现过程"""
        all_discovered = []
        
        # 执行所有扫描器
        for scanner in self.scanners:
            try:
                discovered = scanner.scan()
                all_discovered.extend(discovered)
                logger.info(f"{scanner.__class__.__name__} found {len(discovered)} credentials")
            except Exception as e:
                logger.error(f"Scanner {scanner.__class__.__name__} failed: {e}")
                
        # 去重
        unique_credentials = self._deduplicate(all_discovered)
        
        # 应用过滤器
        filtered_credentials = self._apply_filters(unique_credentials)
        
        # 按置信度排序
        filtered_credentials.sort(key=lambda x: x.confidence, reverse=True)
        
        self.discovered_credentials = filtered_credentials
        
        logger.info(f"Total discovered: {len(filtered_credentials)} unique credentials")
        
        return filtered_credentials
        
    def _deduplicate(self, credentials: List[DiscoveredCredential]) -> List[DiscoveredCredential]:
        """去重"""
        seen = set()
        unique = []
        
        for cred in credentials:
            if cred.value not in seen:
                seen.add(cred.value)
                unique.append(cred)
            else:
                # 如果已存在，更新置信度
                for existing in unique:
                    if existing.value == cred.value:
                        existing.confidence = max(existing.confidence, cred.confidence)
                        
        return unique
        
    def _apply_filters(self, credentials: List[DiscoveredCredential]) -> List[DiscoveredCredential]:
        """应用过滤器"""
        filtered = credentials
        
        for filter_func in self.filters:
            filtered = [c for c in filtered if filter_func(c)]
            
        return filtered
        
    def export_report(self, output_path: str):
        """导出发现报告"""
        report = {
            'discovery_time': datetime.now().isoformat(),
            'total_discovered': len(self.discovered_credentials),
            'credentials': []
        }
        
        for cred in self.discovered_credentials:
            report['credentials'].append({
                'masked_value': self._mask_credential(cred.value),
                'source': cred.source,
                'source_type': cred.source_type,
                'service_type': cred.service_type,
                'confidence': cred.confidence,
                'metadata': cred.metadata
            })
            
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info(f"Discovery report exported to {output_path}")
        
    def _mask_credential(self, value: str) -> str:
        """掩码凭证值"""
        if len(value) <= 8:
            return '*' * len(value)
        return value[:4] + '*' * (len(value) - 8) + value[-4:]
        
    def get_high_confidence_credentials(self, threshold: float = 0.8) -> List[DiscoveredCredential]:
        """获取高置信度凭证"""
        return [c for c in self.discovered_credentials if c.confidence >= threshold]
        
    def get_by_service_type(self, service_type: str) -> List[DiscoveredCredential]:
        """按服务类型获取凭证"""
        return [c for c in self.discovered_credentials 
                if c.service_type and service_type in c.service_type]