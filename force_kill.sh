#!/bin/bash
# 强制关闭所有Python进程

echo "🔍 查找运行中的扫描器进程..."
ps aux | grep -E "python.*scanner|python.*clean_and_restart" | grep -v grep

echo ""
echo "⚠️  强制终止所有相关进程..."
pkill -9 -f "python.*scanner"
pkill -9 -f "python.*clean_and_restart"
pkill -9 -f "python.*run_scanner"

echo "✅ 所有进程已终止"

echo ""
echo "🧹 清理锁文件..."
rm -f *.lock
rm -f data/*.lock

echo "✅ 清理完成"