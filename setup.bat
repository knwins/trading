@echo off
REM Windows环境下的交易系统设置脚本

echo 🚀 交易系统设置脚本
echo.

REM 检查Python版本
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装，请先安装Python 3.8+
    pause
    exit /b 1
)

echo ✅ Python已安装

REM 安装依赖
echo 📦 安装Python依赖...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ 依赖安装失败
    pause
    exit /b 1
)

echo ✅ 依赖安装完成

REM 创建logs目录
if not exist logs mkdir logs
echo ✅ 日志目录创建完成

REM 创建.env文件
if not exist .env (
    echo # 交易所API配置 > .env
    echo BINANCE_API_KEY=your_binance_api_key >> .env
    echo BINANCE_SECRET=your_binance_secret >> .env
    echo. >> .env
    echo # Telegram通知配置 >> .env
    echo TELEGRAM_BOT_TOKEN=your_telegram_bot_token >> .env
    echo TELEGRAM_CHAT_ID=your_telegram_chat_id >> .env
    echo. >> .env
    echo # 系统配置 >> .env
    echo TRADING_ENABLED=true >> .env
    echo SANDBOX_MODE=true >> .env
    echo LOG_LEVEL=INFO >> .env
    echo ✅ 环境变量文件创建完成
)

echo.
echo ==========================================
echo 🎉 设置完成！
echo ==========================================
echo.
echo 📋 下一步操作：
echo 1. 编辑 .env 文件配置API密钥
echo 2. 运行 python trading.py 启动系统
echo 3. 运行 python monitor.py health-check 检查状态
echo.
echo 📊 监控命令：
echo   python monitor.py monitor --interval 30
echo   python monitor.py health-check
echo.
pause 