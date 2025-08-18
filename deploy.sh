#!/bin/bash
# -*- coding: utf-8 -*-
"""
实盘交易系统部署脚本
用于在OSCent系统中部署和启动交易系统

使用方法：
1. 配置环境变量
2. 运行: ./deploy.sh start|stop|restart|status
"""

set -e

# 配置变量
PROJECT_NAME="xniu-trading"
SERVICE_NAME="realtime-trading"
PYTHON_PATH="/usr/bin/python3"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_DIR/logs"
PID_FILE="$PROJECT_DIR/$SERVICE_NAME.pid"
LOCK_FILE="$PROJECT_DIR/$SERVICE_NAME.lock"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 检查环境
check_environment() {
    log_info "检查运行环境..."
    
    # 检查Python
    if ! command -v $PYTHON_PATH &> /dev/null; then
        log_error "Python3 未找到: $PYTHON_PATH"
        exit 1
    fi
    
    # 检查项目目录
    if [ ! -d "$PROJECT_DIR" ]; then
        log_error "项目目录不存在: $PROJECT_DIR"
        exit 1
    fi
    
    # 检查必需文件
    required_files=("realtime_trading_system.py" "strategy.py" "feature_engineer.py" "config.py")
    for file in "${required_files[@]}"; do
        if [ ! -f "$PROJECT_DIR/$file" ]; then
            log_error "必需文件不存在: $file"
            exit 1
        fi
    done
    
    # 创建日志目录
    mkdir -p "$LOG_DIR"
    
    # 检查环境变量
    if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_API_SECRET" ]; then
        log_warn "Binance API 密钥未设置，将使用测试模式"
    fi
    
    log_info "环境检查完成"
}

# 获取PID
get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    else
        echo ""
    fi
}

# 检查服务状态
is_running() {
    local pid=$(get_pid)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# 启动服务
start_service() {
    log_info "启动 $SERVICE_NAME 服务..."
    
    if is_running; then
        log_warn "服务已在运行中 (PID: $(get_pid))"
        return 0
    fi
    
    # 检查锁文件
    if [ -f "$LOCK_FILE" ]; then
        log_error "锁文件存在，可能上次启动异常退出"
        rm -f "$LOCK_FILE"
    fi
    
    # 创建锁文件
    touch "$LOCK_FILE"
    
    # 启动服务
    cd "$PROJECT_DIR"
    nohup $PYTHON_PATH oscent_service.py > "$LOG_DIR/service.log" 2>&1 &
    local pid=$!
    
    # 保存PID
    echo $pid > "$PID_FILE"
    
    # 等待服务启动
    sleep 3
    
    # 检查是否启动成功
    if is_running; then
        log_info "服务启动成功 (PID: $pid)"
        rm -f "$LOCK_FILE"
        return 0
    else
        log_error "服务启动失败"
        rm -f "$PID_FILE" "$LOCK_FILE"
        return 1
    fi
}

# 停止服务
stop_service() {
    log_info "停止 $SERVICE_NAME 服务..."
    
    if ! is_running; then
        log_warn "服务未运行"
        return 0
    fi
    
    local pid=$(get_pid)
    
    # 发送SIGTERM信号
    kill -TERM "$pid" 2>/dev/null
    
    # 等待进程结束
    local count=0
    while [ $count -lt 30 ] && is_running; do
        sleep 1
        count=$((count + 1))
    done
    
    # 如果进程仍在运行，强制杀死
    if is_running; then
        log_warn "强制停止服务..."
        kill -KILL "$pid" 2>/dev/null
        sleep 2
    fi
    
    # 清理文件
    rm -f "$PID_FILE" "$LOCK_FILE"
    
    if ! is_running; then
        log_info "服务已停止"
        return 0
    else
        log_error "停止服务失败"
        return 1
    fi
}

# 重启服务
restart_service() {
    log_info "重启 $SERVICE_NAME 服务..."
    stop_service
    sleep 2
    start_service
}

# 查看服务状态
show_status() {
    log_info "查看 $SERVICE_NAME 服务状态..."
    
    if is_running; then
        local pid=$(get_pid)
        log_info "服务运行中 (PID: $pid)"
        
        # 显示进程信息
        if command -v ps &> /dev/null; then
            ps -p "$pid" -o pid,ppid,cmd,etime,pcpu,pmem 2>/dev/null || true
        fi
        
        # 显示日志文件大小
        if [ -f "$LOG_DIR/service.log" ]; then
            local log_size=$(du -h "$LOG_DIR/service.log" | cut -f1)
            log_info "日志文件大小: $log_size"
        fi
        
        return 0
    else
        log_warn "服务未运行"
        return 1
    fi
}

# 查看日志
show_logs() {
    log_info "查看服务日志..."
    
    if [ -f "$LOG_DIR/service.log" ]; then
        tail -f "$LOG_DIR/service.log"
    else
        log_warn "日志文件不存在"
    fi
}

# 清理日志
clean_logs() {
    log_info "清理日志文件..."
    
    if [ -d "$LOG_DIR" ]; then
        find "$LOG_DIR" -name "*.log" -mtime +7 -delete
        log_info "已清理7天前的日志文件"
    fi
}

# 安装依赖
install_dependencies() {
    log_info "安装Python依赖..."
    
    if [ -f "$PROJECT_DIR/requirements.txt" ]; then
        $PYTHON_PATH -m pip install -r "$PROJECT_DIR/requirements.txt"
        log_info "依赖安装完成"
    else
        log_warn "requirements.txt 文件不存在"
    fi
}

# 备份数据
backup_data() {
    log_info "备份交易数据..."
    
    local backup_dir="$PROJECT_DIR/backup/$(date '+%Y%m%d_%H%M%S')"
    mkdir -p "$backup_dir"
    
    # 备份交易历史
    if [ -f "$PROJECT_DIR/trade_history.json" ]; then
        cp "$PROJECT_DIR/trade_history.json" "$backup_dir/"
    fi
    
    # 备份配置文件
    cp "$PROJECT_DIR/config.py" "$backup_dir/"
    
    # 备份日志
    if [ -d "$LOG_DIR" ]; then
        cp -r "$LOG_DIR" "$backup_dir/"
    fi
    
    log_info "数据备份完成: $backup_dir"
}

# 显示帮助信息
show_help() {
    echo "实盘交易系统部署脚本"
    echo ""
    echo "使用方法: $0 {start|stop|restart|status|logs|clean|install|backup|help}"
    echo ""
    echo "命令说明:"
    echo "  start    启动服务"
    echo "  stop     停止服务"
    echo "  restart  重启服务"
    echo "  status   查看服务状态"
    echo "  logs     查看实时日志"
    echo "  clean    清理旧日志"
    echo "  install  安装依赖"
    echo "  backup   备份数据"
    echo "  help     显示帮助信息"
    echo ""
    echo "环境变量:"
    echo "  BINANCE_API_KEY      Binance API密钥"
    echo "  BINANCE_API_SECRET   Binance API密钥"
    echo "  TELEGRAM_TOKEN       Telegram机器人令牌"
    echo "  TELEGRAM_CHAT_ID     Telegram聊天ID"
}

# 主函数
main() {
    case "$1" in
        start)
            check_environment
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            check_environment
            restart_service
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        clean)
            clean_logs
            ;;
        install)
            install_dependencies
            ;;
        backup)
            backup_data
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@" 