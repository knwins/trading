#!/bin/bash
# -*- coding: utf-8 -*-
"""
CentOS7 交易系统部署脚本
自动安装依赖、配置环境、启动服务
"""

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查是否为root用户
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限运行"
        exit 1
    fi
}

# 检查系统版本
check_system() {
    log_step "检查系统版本..."
    
    if [[ -f /etc/redhat-release ]]; then
        OS_VERSION=$(cat /etc/redhat-release)
        log_info "检测到系统: $OS_VERSION"
        
        if [[ $OS_VERSION == *"CentOS Linux release 7"* ]]; then
            log_info "✅ CentOS 7 系统确认"
        else
            log_warn "⚠️ 未检测到CentOS 7，但继续安装"
        fi
    else
        log_warn "⚠️ 无法确定系统版本，但继续安装"
    fi
}

# 更新系统包
update_system() {
    log_step "更新系统包..."
    
    yum update -y
    log_info "✅ 系统包更新完成"
}

# 安装基础依赖
install_basic_deps() {
    log_step "安装基础依赖..."
    
    # 安装EPEL仓库
    yum install -y epel-release
    
    # 安装基础工具
    yum install -y wget curl git vim htop tree
    
    # 安装开发工具
    yum groupinstall -y "Development Tools"
    
    # 安装Python相关
    yum install -y python3 python3-pip python3-devel
    
    # 安装系统库
    yum install -y openssl-devel libffi-devel bzip2-devel
    
    log_info "✅ 基础依赖安装完成"
}

# 安装Python依赖
install_python_deps() {
    log_step "安装Python依赖..."
    
    # 升级pip
    python3 -m pip install --upgrade pip
    
    # 安装Python包
    pip3 install -r requirements.txt
    
    log_info "✅ Python依赖安装完成"
}

# 创建系统用户
create_user() {
    log_step "创建系统用户..."
    
    # 检查用户是否存在
    if id "trading" &>/dev/null; then
        log_info "用户 'trading' 已存在"
    else
        # 创建用户和组
        useradd -r -s /bin/bash -d /opt/trading trading
        log_info "✅ 用户 'trading' 创建完成"
    fi
    
    # 创建目录
    mkdir -p /opt/trading
    chown -R trading:trading /opt/trading
    
    log_info "✅ 用户配置完成"
}

# 配置防火墙
configure_firewall() {
    log_step "配置防火墙..."
    
    # 检查firewalld状态
    if systemctl is-active --quiet firewalld; then
        # 开放必要端口
        firewall-cmd --permanent --add-port=22/tcp
        firewall-cmd --permanent --add-port=80/tcp
        firewall-cmd --permanent --add-port=443/tcp
        
        # 重新加载防火墙
        firewall-cmd --reload
        log_info "✅ 防火墙配置完成"
    else
        log_warn "⚠️ firewalld未运行，跳过防火墙配置"
    fi
}

# 配置SELinux
configure_selinux() {
    log_step "配置SELinux..."
    
    # 检查SELinux状态
    if command -v sestatus &> /dev/null; then
        SELINUX_STATUS=$(sestatus | grep "SELinux status" | awk '{print $3}')
        
        if [[ $SELINUX_STATUS == "enabled" ]]; then
            log_warn "⚠️ SELinux已启用，建议设置为permissive模式"
            log_info "运行以下命令设置SELinux: setenforce 0"
        else
            log_info "✅ SELinux已禁用"
        fi
    else
        log_info "✅ SELinux未安装"
    fi
}

# 配置系统限制
configure_limits() {
    log_step "配置系统限制..."
    
    # 创建limits配置文件
    cat > /etc/security/limits.d/trading.conf << EOF
# 交易系统用户限制
trading soft nofile 65536
trading hard nofile 65536
trading soft nproc 4096
trading hard nproc 4096
EOF
    
    log_info "✅ 系统限制配置完成"
}

# 配置日志轮转
configure_logrotate() {
    log_step "配置日志轮转..."
    
    # 创建logrotate配置
    cat > /etc/logrotate.d/trading << EOF
/opt/trading/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 trading trading
    postrotate
        systemctl reload trading-system
    endscript
}
EOF
    
    log_info "✅ 日志轮转配置完成"
}

# 安装和配置服务
install_service() {
    log_step "安装系统服务..."
    
    # 复制项目文件到系统目录
    cp -r . /opt/trading/
    chown -R trading:trading /opt/trading
    
    # 切换到项目目录
    cd /opt/trading
    
    # 安装服务
    python3 service.py install --service-name trading-system
    
    log_info "✅ 系统服务安装完成"
}

# 配置环境变量
configure_environment() {
    log_step "配置环境变量..."
    
    # 创建环境变量文件
    cat > /opt/trading/.env.example << EOF
# 交易所API配置
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET=your_binance_secret

# Telegram通知配置
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# 系统配置
TRADING_ENABLED=true
SANDBOX_MODE=true
LOG_LEVEL=INFO
EOF
    
    log_info "✅ 环境变量配置完成"
    log_warn "⚠️ 请编辑 /opt/trading/.env 文件配置您的API密钥"
}

# 启动服务
start_service() {
    log_step "启动交易系统服务..."
    
    # 启动服务
    systemctl start trading-system
    systemctl enable trading-system
    
    # 检查服务状态
    sleep 3
    if systemctl is-active --quiet trading-system; then
        log_info "✅ 交易系统服务启动成功"
    else
        log_error "❌ 交易系统服务启动失败"
        systemctl status trading-system
        exit 1
    fi
}

# 安装监控服务
install_monitor_service() {
    log_step "安装监控服务..."
    
    # 创建监控服务文件
    cat > /etc/systemd/system/trading-monitor.service << EOF
[Unit]
Description=Trading System Monitor
After=trading-system.service

[Service]
Type=simple
User=trading
WorkingDirectory=/opt/trading
ExecStart=/usr/bin/python3 /opt/trading/monitor.py monitor --interval 60
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # 重新加载systemd
    systemctl daemon-reload
    
    # 启用监控服务
    systemctl enable trading-monitor
    
    log_info "✅ 监控服务安装完成"
}

# 创建管理脚本
create_management_scripts() {
    log_step "创建管理脚本..."
    
    # 创建启动脚本
    cat > /opt/trading/start.sh << 'EOF'
#!/bin/bash
systemctl start trading-system
systemctl start trading-monitor
echo "交易系统已启动"
EOF
    
    # 创建停止脚本
    cat > /opt/trading/stop.sh << 'EOF'
#!/bin/bash
systemctl stop trading-monitor
systemctl stop trading-system
echo "交易系统已停止"
EOF
    
    # 创建状态检查脚本
    cat > /opt/trading/status.sh << 'EOF'
#!/bin/bash
echo "=== 交易系统状态 ==="
systemctl status trading-system --no-pager
echo ""
echo "=== 监控服务状态 ==="
systemctl status trading-monitor --no-pager
echo ""
echo "=== 系统健康检查 ==="
python3 /opt/trading/monitor.py health-check
EOF
    
    # 创建日志查看脚本
    cat > /opt/trading/logs.sh << 'EOF'
#!/bin/bash
echo "=== 交易系统日志 ==="
journalctl -u trading-system -n 50 --no-pager
echo ""
echo "=== 监控服务日志 ==="
journalctl -u trading-monitor -n 20 --no-pager
EOF
    
    # 设置执行权限
    chmod +x /opt/trading/*.sh
    chown trading:trading /opt/trading/*.sh
    
    log_info "✅ 管理脚本创建完成"
}

# 显示安装完成信息
show_completion_info() {
    echo ""
    echo "=========================================="
    echo "🎉 交易系统安装完成！"
    echo "=========================================="
    echo ""
    echo "📁 安装目录: /opt/trading"
    echo "👤 运行用户: trading"
    echo ""
    echo "🔧 管理命令:"
    echo "  启动系统: /opt/trading/start.sh"
    echo "  停止系统: /opt/trading/stop.sh"
    echo "  查看状态: /opt/trading/status.sh"
    echo "  查看日志: /opt/trading/logs.sh"
    echo ""
    echo "📋 下一步操作:"
    echo "1. 编辑 /opt/trading/.env 配置API密钥"
    echo "2. 运行 /opt/trading/start.sh 启动系统"
    echo "3. 运行 /opt/trading/status.sh 检查状态"
    echo ""
    echo "📊 监控地址:"
    echo "  系统日志: journalctl -u trading-system -f"
    echo "  监控日志: journalctl -u trading-monitor -f"
    echo ""
    echo "🔗 相关文件:"
    echo "  配置文件: /opt/trading/config.py"
    echo "  环境变量: /opt/trading/.env"
    echo "  服务文件: /etc/systemd/system/trading-system.service"
    echo ""
}

# 主函数
main() {
    echo "🚀 开始安装交易系统..."
    echo ""
    
    # 检查root权限
    check_root
    
    # 执行安装步骤
    check_system
    update_system
    install_basic_deps
    install_python_deps
    create_user
    configure_firewall
    configure_selinux
    configure_limits
    configure_logrotate
    install_service
    configure_environment
    install_monitor_service
    create_management_scripts
    start_service
    
    # 显示完成信息
    show_completion_info
}

# 运行主函数
main "$@" 