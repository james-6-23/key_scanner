#!/bin/bash

# Docker网络冲突修复脚本
# 解决: Pool overlaps with other one on this address space

echo "🔧 Docker Network Conflict Fix Script"
echo "====================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 停止当前的容器
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker-compose down 2>/dev/null || true

# 2. 列出所有Docker网络
echo -e "\n${YELLOW}Current Docker networks:${NC}"
docker network ls

# 3. 检查是否存在冲突的网络
NETWORK_NAME="key_scanner_scanner-network"
if docker network inspect $NETWORK_NAME >/dev/null 2>&1; then
    echo -e "${YELLOW}Found existing network: $NETWORK_NAME${NC}"
    echo "Removing it..."
    docker network rm $NETWORK_NAME
    echo -e "${GREEN}Network removed successfully${NC}"
else
    echo -e "${GREEN}No conflicting network found with name: $NETWORK_NAME${NC}"
fi

# 4. 检查其他可能冲突的网络
echo -e "\n${YELLOW}Checking for networks using similar IP ranges...${NC}"
docker network inspect $(docker network ls -q) 2>/dev/null | grep -E "Subnet|Name" | grep -B1 "172.20.0.0"

# 5. 清理未使用的网络
echo -e "\n${YELLOW}Cleaning up unused networks...${NC}"
docker network prune -f

# 6. 修改docker-compose.yml使用不同的子网
echo -e "\n${YELLOW}Creating docker-compose.override.yml with custom network configuration...${NC}"

cat > docker-compose.override.yml << 'EOF'
# Docker Compose Override File
# 解决网络冲突问题

networks:
  scanner-network:
    driver: bridge
    ipam:
      config:
        # 使用不同的子网避免冲突
        - subnet: 172.28.0.0/16
          gateway: 172.28.0.1
EOF

echo -e "${GREEN}Override file created${NC}"

# 7. 显示新的配置
echo -e "\n${YELLOW}New network configuration:${NC}"
cat docker-compose.override.yml

# 8. 尝试重新启动服务
echo -e "\n${YELLOW}Attempting to start services with new configuration...${NC}"
docker-compose up -d

# 检查启动状态
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Services started successfully!${NC}"
    echo -e "\n${YELLOW}Container status:${NC}"
    docker-compose ps
    echo -e "\n${YELLOW}View logs:${NC}"
    echo "docker-compose logs -f"
else
    echo -e "\n${RED}❌ Failed to start services${NC}"
    echo -e "${YELLOW}Alternative solutions:${NC}"
    echo "1. Try a different subnet in docker-compose.override.yml (e.g., 172.29.0.0/16)"
    echo "2. Remove all Docker networks: docker network prune -f"
    echo "3. Restart Docker daemon: sudo systemctl restart docker"
    echo "4. Use host network mode (modify docker-compose.yml)"
fi

echo -e "\n${GREEN}Script completed${NC}"