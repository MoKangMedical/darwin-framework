#!/bin/bash

# darwin-framework 部署脚本
# 用于自动化部署到生产环境

set -e

# 配置
PROJECT_NAME="darwin-framework"
DEPLOY_DIR="/opt/$PROJECT_NAME"
BACKUP_DIR="/opt/backups/$PROJECT_NAME"
LOG_FILE="/var/log/$PROJECT_NAME/deploy.log"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

error() {
    echo -e "${RED}[ERROR] $1${NC}" | tee -a $LOG_FILE
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}" | tee -a $LOG_FILE
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}" | tee -a $LOG_FILE
}

# 检查依赖
check_dependencies() {
    log "检查依赖..."
    
    if ! command -v git &> /dev/null; then
        error "git未安装"
    fi
    
    if ! command -v docker &> /dev/null; then
        error "docker未安装"
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        error "docker-compose未安装"
    fi
    
    success "依赖检查通过"
}

# 备份当前版本
backup_current() {
    log "备份当前版本..."
    
    if [ -d "$DEPLOY_DIR" ]; then
        BACKUP_NAME="$PROJECT_NAME-$(date '+%Y%m%d-%H%M%S')"
        mkdir -p $BACKUP_DIR
        cp -r $DEPLOY_DIR "$BACKUP_DIR/$BACKUP_NAME"
        success "备份完成: $BACKUP_DIR/$BACKUP_NAME"
    else
        warning "部署目录不存在，跳过备份"
    fi
}

# 拉取最新代码
pull_latest() {
    log "拉取最新代码..."
    
    if [ -d "$DEPLOY_DIR/.git" ]; then
        cd $DEPLOY_DIR
        git fetch origin
        git reset --hard origin/main
        success "代码更新完成"
    else
        log "克隆仓库..."
        git clone https://github.com/MoKangMedical/$PROJECT_NAME.git $DEPLOY_DIR
        cd $DEPLOY_DIR
        success "仓库克隆完成"
    fi
}

# 构建和启动服务
build_and_start() {
    log "构建和启动服务..."
    
    cd $DEPLOY_DIR
    
    # 停止现有服务
    if [ -f "docker-compose.yml" ]; then
        docker-compose down
    fi
    
    # 构建镜像
    docker-compose build
    
    # 启动服务
    docker-compose up -d
    
    # 等待服务启动
    log "等待服务启动..."
    sleep 30
    
    # 检查服务状态
    if docker-compose ps | grep -q "Up"; then
        success "服务启动成功"
    else
        error "服务启动失败"
    fi
}

# 健康检查
health_check() {
    log "执行健康检查..."
    
    # 等待服务完全启动
    sleep 10
    
    # 检查健康端点
    for i in {1..10}; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            success "健康检查通过"
            return 0
        fi
        log "等待服务响应... (尝试 $i/10)"
        sleep 5
    done
    
    error "健康检查失败"
}

# 清理旧备份
cleanup_old_backups() {
    log "清理旧备份..."
    
    if [ -d "$BACKUP_DIR" ]; then
        # 保留最近5个备份
        cd $BACKUP_DIR
        ls -t | tail -n +6 | xargs -r rm -r
        success "旧备份清理完成"
    fi
}

# 显示部署信息
show_info() {
    echo ""
    echo "========================================="
    echo "  部署完成！"
    echo "========================================="
    echo "  项目: $PROJECT_NAME"
    echo "  目录: $DEPLOY_DIR"
    echo "  备份: $BACKUP_DIR"
    echo "  日志: $LOG_FILE"
    echo "  访问: http://localhost:8000"
    echo "========================================="
    echo ""
}

# 主函数
main() {
    log "开始部署 $PROJECT_NAME..."
    
    # 检查依赖
    check_dependencies
    
    # 备份当前版本
    backup_current
    
    # 拉取最新代码
    pull_latest
    
    # 构建和启动服务
    build_and_start
    
    # 健康检查
    health_check
    
    # 清理旧备份
    cleanup_old_backups
    
    # 显示信息
    show_info
    
    success "部署完成！"
}

# 执行主函数
main "$@"
