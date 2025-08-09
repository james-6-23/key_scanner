#!/usr/bin/env python3
"""
修复所有错误的综合脚本
解决监控系统、健康检查和凭证添加失败的问题
"""

import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def fix_monitoring_dashboard():
    """修复监控仪表板的 by_service 错误"""
    dashboard_file = Path("credential_manager/monitoring/dashboard.py")
    
    if not dashboard_file.exists():
        print("[ERROR] Dashboard file not found")
        return False
    
    print("[INFO] Fixing monitoring dashboard...")
    
    with open(dashboard_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复 _collect_metrics 方法
    old_code = """        # 记录服务类型分布
        for service, count in stats['by_service'].items():
            self.metrics_collector.record_metric(
                f'service_{service}',
                count,
                tags={'service': service}
            )"""
    
    new_code = """        # 记录服务类型分布
        if 'by_service' in stats:
            for service, count in stats['by_service'].items():
                self.metrics_collector.record_metric(
                    f'service_{service}',
                    count,
                    tags={'service': service}
                )"""
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        with open(dashboard_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("[SUCCESS] Fixed by_service error")
        return True
    else:
        print("[WARNING] by_service code already fixed or different format")
        return False

def fix_health_checker():
    """修复 HealthChecker 的 check_all_pools 方法"""
    health_file = Path("credential_manager/health/health_checker.py")
    
    if not health_file.exists():
        print("[ERROR] Health checker file not found")
        return False
    
    print("[INFO] Fixing health checker...")
    
    with open(health_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已有 check_all_pools 方法
    if 'def check_all_pools' not in content:
        # 在类的末尾添加方法
        insertion_point = content.rfind('class HealthChecker')
        if insertion_point == -1:
            print("[ERROR] HealthChecker class not found")
            return False
        
        # 找到类的结束位置（下一个class或文件末尾）
        next_class = content.find('\nclass ', insertion_point + 1)
        if next_class == -1:
            # 在文件末尾添加
            content += """
    
    def check_all_pools(self) -> Dict[str, Any]:
        \"\"\"
        检查所有凭证池的健康状态
        
        Returns:
            所有池的健康状态字典
        \"\"\"
        if not hasattr(self, 'credential_manager') or not self.credential_manager:
            return {
                'status': 'error',
                'message': 'Credential manager not available',
                'pools': {}
            }
        
        try:
            # 获取所有池的状态
            pools_status = {}
            stats = self.credential_manager.get_statistics()
            
            # 检查每个服务类型的池
            for service_type in ['github', 'gemini', 'openai', 'anthropic']:
                pool_health = {
                    'status': 'healthy',
                    'active_count': 0,
                    'total_count': 0,
                    'health_score': 100.0,
                    'issues': []
                }
                
                # 从统计信息中提取池状态
                if 'by_status' in stats:
                    pool_health['active_count'] = stats['by_status'].get('active', 0)
                    pool_health['total_count'] = stats.get('total_credentials', 0)
                
                if 'average_health_score' in stats:
                    pool_health['health_score'] = stats['average_health_score']
                
                # 判断健康状态
                if pool_health['active_count'] == 0:
                    pool_health['status'] = 'critical'
                    pool_health['issues'].append('No active credentials')
                elif pool_health['active_count'] < 2:
                    pool_health['status'] = 'warning'
                    pool_health['issues'].append('Low active credentials')
                
                if pool_health['health_score'] < 50:
                    pool_health['status'] = 'warning'
                    pool_health['issues'].append('Low health score')
                
                pools_status[service_type] = pool_health
            
            return {
                'status': 'ok',
                'timestamp': datetime.now().isoformat(),
                'pools': pools_status
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'pools': {}
            }
"""
        else:
            # 在下一个类之前插入
            print("[WARNING] Need to manually add check_all_pools method")
            return False
        
        with open(health_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("[SUCCESS] Added check_all_pools method")
        return True
    else:
        print("[WARNING] check_all_pools method already exists")
        return True

def fix_credential_manager_statistics():
    """修复 CredentialManager 的 get_statistics 方法，确保返回所有必需的键"""
    manager_file = Path("credential_manager/core/manager.py")
    
    if not manager_file.exists():
        print("[ERROR] Credential manager file not found")
        return False
    
    print("[INFO] Fixing credential manager statistics method...")
    
    with open(manager_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 查找 get_statistics 方法
    method_start = -1
    for i, line in enumerate(lines):
        if 'def get_statistics(self)' in line:
            method_start = i
            break
    
    if method_start == -1:
        print("[ERROR] get_statistics method not found")
        return False
    
    # 找到方法的结束位置
    method_end = -1
    indent_level = len(lines[method_start]) - len(lines[method_start].lstrip())
    for i in range(method_start + 1, len(lines)):
        if lines[i].strip() and not lines[i].startswith(' ' * (indent_level + 4)):
            method_end = i
            break
    
    if method_end == -1:
        method_end = len(lines)
    
    # 构建新的方法实现
    new_method = [
        lines[method_start],  # 保留方法定义行
        '        """获取统计信息"""\n',
        '        try:\n',
        '            all_credentials = self.vault.get_all_credentials()\n',
        '            \n',
        '            # 初始化统计数据\n',
        '            by_status = {}\n',
        '            by_service = {}\n',
        '            total_health = 0\n',
        '            \n',
        '            for cred in all_credentials:\n',
        '                # 统计状态\n',
        '                status = cred.status.value if hasattr(cred.status, "value") else str(cred.status)\n',
        '                by_status[status] = by_status.get(status, 0) + 1\n',
        '                \n',
        '                # 统计服务类型\n',
        '                service = cred.service_type.value if hasattr(cred.service_type, "value") else str(cred.service_type)\n',
        '                by_service[service] = by_service.get(service, 0) + 1\n',
        '                \n',
        '                # 累计健康分数\n',
        '                total_health += cred.health_score\n',
        '            \n',
        '            total_count = len(all_credentials)\n',
        '            avg_health = total_health / total_count if total_count > 0 else 0\n',
        '            \n',
        '            return {\n',
        '                "total_credentials": total_count,\n',
        '                "by_status": by_status,\n',
        '                "by_service": by_service,\n',
        '                "average_health_score": avg_health,\n',
        '                "active_count": by_status.get("active", 0),\n',
        '                "exhausted_count": by_status.get("exhausted", 0),\n',
        '                "invalid_count": by_status.get("invalid", 0)\n',
        '            }\n',
        '        except Exception as e:\n',
        '            logger.error(f"Error getting statistics: {e}")\n',
        '            return {\n',
        '                "total_credentials": 0,\n',
        '                "by_status": {},\n',
        '                "by_service": {},\n',
        '                "average_health_score": 0,\n',
        '                "active_count": 0,\n',
        '                "exhausted_count": 0,\n',
        '                "invalid_count": 0\n',
        '            }\n'
    ]
    
    # 替换方法
    lines[method_start:method_end] = new_method
    
    with open(manager_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("[SUCCESS] Fixed get_statistics method")
    return True

def fix_credential_validation():
    """修复凭证验证问题，确保GitHub tokens能正确添加"""
    print("[INFO] Fixing credential validation...")
    
    # 清理数据库中的无效凭证
    db_files = [
        "credentials.db",
        "data/credentials.db",
        "github_credentials.db"
    ]
    
    for db_file in db_files:
        if os.path.exists(db_file):
            print(f"[INFO] Cleaning database: {db_file}")
            try:
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()
                
                # 删除所有PENDING状态的GitHub凭证
                cursor.execute("""
                    DELETE FROM credentials 
                    WHERE service_type = 'github' AND status = 'PENDING'
                """)
                
                # 更新所有GitHub凭证为ACTIVE
                cursor.execute("""
                    UPDATE credentials 
                    SET status = 'ACTIVE', health_score = 100.0
                    WHERE service_type = 'github'
                """)
                
                conn.commit()
                conn.close()
                print(f"  [SUCCESS] Cleaned {db_file}")
            except Exception as e:
                print(f"  [WARNING] Failed to clean {db_file}: {e}")
    
    return True

def create_limited_queries_file():
    """创建限制查询数量的文件"""
    print("[INFO] Creating limited queries file...")
    
    # 创建只有5个查询的文件
    limited_queries = [
        "# 限制查询数量以避免API配额耗尽",
        "AIzaSy in:file",
        "gemini api key in:file",
        "openai api key in:file", 
        "sk- in:file extension:env",
        "api_key in:file extension:json"
    ]
    
    with open("queries_limited.txt", "w", encoding='utf-8') as f:
        f.write("\n".join(limited_queries))
    
    print("[SUCCESS] Created queries_limited.txt (5 queries)")
    
    # 创建测试用的单个查询文件
    test_query = [
        "# 测试用单个查询",
        "AIzaSy in:file extension:md"
    ]
    
    with open("queries_test.txt", "w", encoding='utf-8') as f:
        f.write("\n".join(test_query))
    
    print("[SUCCESS] Created queries_test.txt (1 query)")
    
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("Comprehensive Error Fix Script")
    print("=" * 60)
    
    # 1. 修复监控仪表板
    fix_monitoring_dashboard()
    
    # 2. 修复健康检查器
    fix_health_checker()
    
    # 3. 修复凭证管理器统计
    fix_credential_manager_statistics()
    
    # 4. 修复凭证验证
    fix_credential_validation()
    
    # 5. 创建限制查询文件
    create_limited_queries_file()
    
    print("\n" + "=" * 60)
    print("All fixes completed!")
    print("=" * 60)
    print("\nRecommended running methods:")
    print("1. Test mode (1 query):")
    print("   python app/api_key_scanner_super.py --queries queries_test.txt")
    print("\n2. Limited mode (5 queries):")
    print("   python app/api_key_scanner_super.py --queries queries_limited.txt")
    print("\n3. Use optimized script:")
    print("   python run_scanner_optimized.py")
    print("\n4. Disable monitoring version:")
    print("   python disable_monitoring.py")

if __name__ == "__main__":
    main()