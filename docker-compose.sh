#!/bin/bash

# MemoryCare Docker Compose 启动脚本

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null
then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查并确定 Docker Compose 命令
if command -v docker compose &> /dev/null
then
    COMPOSE_CMD="docker compose"
    echo "✅ 检测到 docker compose 命令"
elif command -v docker-compose &> /dev/null
then
    COMPOSE_CMD="docker-compose"
    echo "✅ 检测到 docker-compose 命令"
else
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

echo "✅ Docker 已安装"

echo "📦 构建 Docker 镜像..."
$COMPOSE_CMD build

echo "🚀 启动服务..."
$COMPOSE_CMD up -d

echo "✅ 服务启动成功！"
echo ""
echo "🔗 访问地址："
echo "   - 前端应用：http://localhost:8501"
echo "   - 后端 API：http://localhost:8000"
echo "   - API 文档：http://localhost:8000/docs"
echo ""
echo "📋 服务状态："
$COMPOSE_CMD ps

echo ""
echo "💡 提示："
echo "   - 如果遇到 Docker 权限错误，请将用户添加到 docker 组或使用 sudo 运行："
echo "       sudo groupadd docker 2>/dev/null; sudo usermod -aG docker \$USER"
echo "   - 查看服务日志：$COMPOSE_CMD logs -f"
echo "   - 停止服务：$COMPOSE_CMD down"
echo "   - 重启服务：$COMPOSE_CMD restart"