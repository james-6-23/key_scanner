#!/bin/bash

# 快速修复Docker网络冲突

echo "🚀 Quick Docker Network Fix"
echo "=========================="

# 1. 停止并删除所有相关容器和网络
echo "Cleaning up existing resources..."
docker-compose down --remove-orphans
docker network rm key_scanner_scanner-network 2>/dev/null || true

# 2. 清理未使用的网络
echo "Pruning unused networks..."
docker network prune -f

# 3. 使用不同的项目名称启动（避免网络名称冲突）
echo "Starting with new project name..."
docker-compose -p keyscanner up -d

# 4. 检查状态
echo ""
echo "Status:"
docker-compose -p keyscanner ps

echo ""
echo "✅ Done! View logs with: docker-compose -p keyscanner logs -f"