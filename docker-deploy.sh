#!/bin/bash

# Docker 快速部署脚本
# 用于一键启动智能教案助手 Docker 服务

set -e  # 遇到错误时退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[信息]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[成功]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

print_error() {
    echo -e "${RED}[错误]${NC} $1"
}

# 检查Docker是否安装
check_docker() {
    print_info "检查 Docker 环境..."

    if ! command -v docker &> /dev/null; then
        print_error "未检测到 Docker，请先安装 Docker"
        echo "安装指南: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "未检测到 Docker Compose，请先安装 Docker Compose"
        echo "安装指南: https://docs.docker.com/compose/install/"
        exit 1
    fi

    print_success "Docker 环境检查通过"
    docker --version
    docker-compose --version
}

# 检查.env文件
check_env() {
    print_info "检查环境配置..."

    if [ ! -f .env ]; then
        print_warning ".env 文件不存在，正在从 .env.example 创建..."

        if [ -f .env.example ]; then
            cp .env.example .env
            print_warning "请编辑 .env 文件并填入您的 API 密钥："
            echo "  nano .env  # Linux/Mac"
            echo "  或"
            echo "  notepad .env  # Windows"
            echo ""
            echo "必填项："
            echo "  - AI_PROVIDER=deepseek"
            echo "  - DEEPSEEK_API_KEY=sk-your-api-key"
            echo ""
            read -p "配置完成后按 Enter 继续..."
        else
            print_error ".env.example 文件不存在"
            exit 1
        fi
    fi

    # 检查必填的环境变量
    if ! grep -q "DEEPSEEK_API_KEY=sk-" .env && ! grep -q "ANTHROPIC_API_KEY=sk-" .env; then
        print_error "未检测到有效的 API 密钥，请在 .env 文件中配置"
        exit 1
    fi

    print_success "环境配置检查通过"
}

# 创建必要的目录
create_directories() {
    print_info "创建存储目录..."

    mkdir -p storage/uploads
    mkdir -p storage/outputs
    mkdir -p storage/exports

    print_success "存储目录创建完成"
}

# 构建并启动服务
start_services() {
    print_info "构建并启动 Docker 服务..."

    if [ "$1" = "--build" ]; then
        print_info "强制重新构建镜像..."
        docker-compose up -d --build
    else
        docker-compose up -d
    fi

    print_success "Docker 服务已启动"
}

# 等待服务就绪
wait_for_services() {
    print_info "等待服务启动..."

    max_attempts=30
    attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_success "后端服务已就绪"
            break
        fi

        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done

    echo ""

    if [ $attempt -eq $max_attempts ]; then
        print_warning "后端服务启动超时，请检查日志"
        print_info "查看日志命令: docker-compose logs -f backend"
    fi
}

# 显示访问信息
show_info() {
    echo ""
    echo "======================================"
    print_success "部署完成！"
    echo "======================================"
    echo ""
    echo "访问地址："
    echo "  前端界面: ${GREEN}http://localhost${NC}"
    echo "  后端API:  ${GREEN}http://localhost:8000${NC}"
    echo "  API文档:  ${GREEN}http://localhost:8000/docs${NC}"
    echo ""
    echo "常用命令："
    echo "  查看日志: ${BLUE}docker-compose logs -f${NC}"
    echo "  查看状态: ${BLUE}docker-compose ps${NC}"
    echo "  停止服务: ${BLUE}docker-compose stop${NC}"
    echo "  重启服务: ${BLUE}docker-compose restart${NC}"
    echo "  完全清理: ${BLUE}docker-compose down -v${NC}"
    echo ""
}

# 主函数
main() {
    echo "======================================"
    echo "  智能教案助手 Docker 快速部署"
    echo "======================================"
    echo ""

    check_docker
    check_env
    create_directories
    start_services "$@"
    wait_for_services
    show_info
}

# 执行主函数
main "$@"
