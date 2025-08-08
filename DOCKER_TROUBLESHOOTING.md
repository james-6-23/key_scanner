# Docker部署故障排除指南

## 常见问题及解决方案

### 1. 网络冲突错误
**错误信息：**
```
Error response from daemon: invalid pool request: Pool overlaps with other one on this address space
```

**原因：**
Docker网络地址池与现有网络冲突。

**解决方案：**

#### 方法1：使用快速修复脚本（推荐）
```bash
# 赋予执行权限
chmod +x quick_fix_docker.sh

# 运行修复脚本
./quick_fix_docker.sh
```

#### 方法2：使用完整修复脚本
```bash
# 赋予执行权限
chmod +x fix_docker_network.sh

# 运行修复脚本
./fix_docker_network.sh
```

#### 方法3：手动修复
```bash
# 1. 停止并删除现有容器
docker-compose down

# 2. 删除冲突的网络
docker network rm key_scanner_scanner-network

# 3. 清理未使用的网络
docker network prune -f

# 4. 使用新的项目名称启动
docker-compose -p keyscanner up -d
```

#### 方法4：使用自定义网络配置
创建 `docker-compose.override.yml`：
```yaml
networks:
  scanner-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.29.0.0/16
```

然后重新启动：
```bash
docker-compose up -d
```

### 2. 版本警告
**警告信息：**
```
the attribute `version` is obsolete, it will be ignored
```

**解决：**
这只是警告，不影响运行。新版Docker Compose不再需要version字段。

### 3. 容器无法启动

**检查步骤：**
```bash
# 查看容器状态
docker-compose ps

# 查看详细日志
docker-compose logs

# 查看特定服务日志
docker-compose logs scanner
docker-compose logs warp
```

### 4. WARP代理连接失败

**症状：**
- Scanner容器无法连接到WARP代理
- 网络请求超时

**解决方案：**
```bash
# 1. 检查WARP容器状态
docker-compose ps warp

# 2. 重启WARP容器
docker-compose restart warp

# 3. 查看WARP日志
docker-compose logs warp

# 4. 测试代理连接
docker-compose exec scanner curl -x http://warp:1080 https://api.github.com
```

### 5. 权限问题

**症状：**
- 无法创建或写入文件
- Permission denied错误

**解决方案：**
```bash
# 1. 确保data目录有正确权限
chmod -R 755 data/

# 2. 如果需要，更改所有者
sudo chown -R $USER:$USER data/
```

### 6. 端口冲突

**症状：**
- bind: address already in use

**解决方案：**
```bash
# 1. 查找占用端口的进程
lsof -i :1080

# 2. 停止占用的服务或更改端口
# 编辑docker-compose.yml，修改端口映射
```

## 诊断命令集

### 基础诊断
```bash
# 系统信息
docker version
docker-compose version

# 网络诊断
docker network ls
docker network inspect bridge

# 容器诊断
docker ps -a
docker-compose ps
docker-compose logs --tail=50
```

### 深度诊断
```bash
# 检查Docker守护进程
sudo systemctl status docker

# 检查磁盘空间
df -h

# 检查Docker使用的空间
docker system df

# 清理Docker资源
docker system prune -a
```

## 完全重置

如果问题持续，可以完全重置Docker环境：

```bash
#!/bin/bash
# 警告：这会删除所有Docker容器、镜像和网络！

# 1. 停止所有容器
docker stop $(docker ps -aq)

# 2. 删除所有容器
docker rm $(docker ps -aq)

# 3. 删除所有镜像
docker rmi $(docker images -q)

# 4. 删除所有网络
docker network prune -f

# 5. 删除所有卷
docker volume prune -f

# 6. 重新构建和启动
docker-compose build --no-cache
docker-compose up -d
```

## 最佳实践

1. **定期清理**
   ```bash
   # 每周运行一次
   docker system prune -f
   ```

2. **监控资源**
   ```bash
   # 查看容器资源使用
   docker stats
   ```

3. **备份配置**
   ```bash
   # 备份重要配置
   cp .env .env.backup
   cp docker-compose.yml docker-compose.yml.backup
   ```

4. **使用健康检查**
   ```bash
   # 检查服务健康状态
   docker-compose ps
   ```

## 获取帮助

如果问题仍未解决：

1. 收集诊断信息：
   ```bash
   docker-compose logs > docker_logs.txt
   docker network ls > network_list.txt
   docker ps -a > container_list.txt
   ```

2. 检查GitHub Issues：
   https://github.com/james-6-23/key_scanner/issues

3. 提供以下信息：
   - 操作系统版本
   - Docker版本
   - 错误日志
   - 执行的命令序列

---

**快速参考卡片**

| 问题 | 快速解决命令 |
|------|------------|
| 网络冲突 | `./quick_fix_docker.sh` |
| 容器未启动 | `docker-compose restart` |
| 查看日志 | `docker-compose logs -f` |
| 停止服务 | `docker-compose down` |
| 重新构建 | `docker-compose build --no-cache` |
| 清理资源 | `docker system prune -f` |