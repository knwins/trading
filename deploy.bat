@echo off
REM 实盘交易系统部署脚本 - Windows版本
REM 用于在Windows系统中部署和启动交易系统
REM 
REM 使用方法：
REM 1. 配置环境变量
REM 2. 运行: deploy.bat start|stop|restart|status

setlocal enabledelayedexpansion

REM 配置变量
set PROJECT_NAME=xniu-trading
set SERVICE_NAME=realtime-trading
set PYTHON_PATH=python
set PROJECT_DIR=%~dp0
set LOG_DIR=%PROJECT_DIR%logs
set PID_FILE=%PROJECT_DIR%%SERVICE_NAME%.pid
set LOCK_FILE=%PROJECT_DIR%%SERVICE_NAME%.lock

REM 颜色定义
set RED=[91m
set GREEN=[92m
set YELLOW=[93m
set BLUE=[94m
set NC=[0m

REM 日志函数
:log_info
echo %GREEN%[INFO]%NC% %date% %time% - %~1
goto :eof

:log_warn
echo %YELLOW%[WARN]%NC% %date% %time% - %~1
goto :eof

:log_error
echo %RED%[ERROR]%NC% %date% %time% - %~1
goto :eof

:log_debug
echo %BLUE%[DEBUG]%NC% %date% %time% - %~1
goto :eof

REM 检查环境
:check_environment
call :log_info "检查运行环境..."

REM 检查Python
%PYTHON_PATH% --version >nul 2>&1
if errorlevel 1 (
    call :log_error "Python未找到或未安装"
    exit /b 1
)

REM 检查项目目录
if not exist "%PROJECT_DIR%" (
    call :log_error "项目目录不存在: %PROJECT_DIR%"
    exit /b 1
)

REM 检查必需文件
set required_files=realtime_trading_system.py strategy.py feature_engineer.py config.py
for %%f in (%required_files%) do (
    if not exist "%PROJECT_DIR%%%f" (
        call :log_error "必需文件不存在: %%f"
        exit /b 1
    )
)

REM 创建日志目录
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM 检查环境变量
if "%BINANCE_API_KEY%"=="" (
    call :log_warn "Binance API 密钥未设置，将使用测试模式"
)

call :log_info "环境检查完成"
goto :eof

REM 获取PID
:get_pid
if exist "%PID_FILE%" (
    type "%PID_FILE%"
) else (
    echo ""
)
goto :eof

REM 检查服务状态
:is_running
call :get_pid
set pid=!errorlevel!
if "!pid!"=="" goto :not_running
tasklist /FI "PID eq !pid!" 2>nul | find /I "!pid!" >nul
if errorlevel 1 goto :not_running
goto :running

:running
exit /b 0

:not_running
exit /b 1

REM 启动服务
:start_service
call :log_info "启动 %SERVICE_NAME% 服务..."

call :is_running
if not errorlevel 1 (
    call :get_pid
    call :log_warn "服务已在运行中 (PID: !errorlevel!)"
    goto :eof
)

REM 检查锁文件
if exist "%LOCK_FILE%" (
    call :log_error "锁文件存在，可能上次启动异常退出"
    del "%LOCK_FILE%"
)

REM 创建锁文件
echo. > "%LOCK_FILE%"

REM 启动服务
cd /d "%PROJECT_DIR%"
start /B %PYTHON_PATH% oscent_service.py > "%LOG_DIR%\service.log" 2>&1

REM 等待服务启动
timeout /t 3 /nobreak >nul

REM 检查是否启动成功
call :is_running
if not errorlevel 1 (
    call :get_pid
    call :log_info "服务启动成功 (PID: !errorlevel!)"
    del "%LOCK_FILE%" 2>nul
    goto :eof
) else (
    call :log_error "服务启动失败"
    del "%PID_FILE%" 2>nul
    del "%LOCK_FILE%" 2>nul
    exit /b 1
)

REM 停止服务
:stop_service
call :log_info "停止 %SERVICE_NAME% 服务..."

call :is_running
if errorlevel 1 (
    call :log_warn "服务未运行"
    goto :eof
)

call :get_pid
set pid=!errorlevel!

REM 发送终止信号
taskkill /PID !pid! /F >nul 2>&1

REM 等待进程结束
set count=0
:wait_loop
call :is_running
if not errorlevel 1 (
    if !count! lss 30 (
        timeout /t 1 /nobreak >nul
        set /a count+=1
        goto :wait_loop
    )
)

REM 如果进程仍在运行，强制杀死
call :is_running
if not errorlevel 1 (
    call :log_warn "强制停止服务..."
    taskkill /PID !pid! /F >nul 2>&1
    timeout /t 2 /nobreak >nul
)

REM 清理文件
del "%PID_FILE%" 2>nul
del "%LOCK_FILE%" 2>nul

call :is_running
if errorlevel 1 (
    call :log_info "服务已停止"
    goto :eof
) else (
    call :log_error "停止服务失败"
    exit /b 1
)

REM 重启服务
:restart_service
call :log_info "重启 %SERVICE_NAME% 服务..."
call :stop_service
timeout /t 2 /nobreak >nul
call :start_service
goto :eof

REM 查看服务状态
:show_status
call :log_info "查看 %SERVICE_NAME% 服务状态..."

call :is_running
if not errorlevel 1 (
    call :get_pid
    set pid=!errorlevel!
    call :log_info "服务运行中 (PID: !pid!)"
    
    REM 显示进程信息
    tasklist /FI "PID eq !pid!" /FO TABLE
    
    REM 显示日志文件大小
    if exist "%LOG_DIR%\service.log" (
        for %%A in ("%LOG_DIR%\service.log") do set log_size=%%~zA
        call :log_info "日志文件大小: !log_size! bytes"
    )
    
    goto :eof
) else (
    call :log_warn "服务未运行"
    exit /b 1
)

REM 查看日志
:show_logs
call :log_info "查看服务日志..."

if exist "%LOG_DIR%\service.log" (
    type "%LOG_DIR%\service.log"
) else (
    call :log_warn "日志文件不存在"
)
goto :eof

REM 清理日志
:clean_logs
call :log_info "清理日志文件..."

if exist "%LOG_DIR%" (
    forfiles /p "%LOG_DIR%" /s /m *.log /d -7 /c "cmd /c del @path" 2>nul
    call :log_info "已清理7天前的日志文件"
)
goto :eof

REM 安装依赖
:install_dependencies
call :log_info "安装Python依赖..."

if exist "%PROJECT_DIR%\requirements.txt" (
    %PYTHON_PATH% -m pip install -r "%PROJECT_DIR%\requirements.txt"
    call :log_info "依赖安装完成"
) else (
    call :log_warn "requirements.txt 文件不存在"
)
goto :eof

REM 备份数据
:backup_data
call :log_info "备份交易数据..."

set backup_dir=%PROJECT_DIR%backup\%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set backup_dir=!backup_dir: =0!
mkdir "!backup_dir!" 2>nul

REM 备份交易历史
if exist "%PROJECT_DIR%\trade_history.json" (
    copy "%PROJECT_DIR%\trade_history.json" "!backup_dir!\" >nul
)

REM 备份配置文件
copy "%PROJECT_DIR%\config.py" "!backup_dir!\" >nul

REM 备份日志
if exist "%LOG_DIR%" (
    xcopy "%LOG_DIR%" "!backup_dir!\logs\" /E /I /Y >nul
)

call :log_info "数据备份完成: !backup_dir!"
goto :eof

REM 显示帮助信息
:show_help
echo 实盘交易系统部署脚本 - Windows版本
echo.
echo 使用方法: %~nx0 {start^|stop^|restart^|status^|logs^|clean^|install^|backup^|help}
echo.
echo 命令说明:
echo   start    启动服务
echo   stop     停止服务
echo   restart  重启服务
echo   status   查看服务状态
echo   logs     查看实时日志
echo   clean    清理旧日志
echo   install  安装依赖
echo   backup   备份数据
echo   help     显示帮助信息
echo.
echo 环境变量:
echo   BINANCE_API_KEY      Binance API密钥
echo   BINANCE_API_SECRET   Binance API密钥
echo   TELEGRAM_TOKEN       Telegram机器人令牌
echo   TELEGRAM_CHAT_ID     Telegram聊天ID
goto :eof

REM 主函数
:main
if "%1"=="start" (
    call :check_environment
    call :start_service
) else if "%1"=="stop" (
    call :stop_service
) else if "%1"=="restart" (
    call :check_environment
    call :restart_service
) else if "%1"=="status" (
    call :show_status
) else if "%1"=="logs" (
    call :show_logs
) else if "%1"=="clean" (
    call :clean_logs
) else if "%1"=="install" (
    call :install_dependencies
) else if "%1"=="backup" (
    call :backup_data
) else if "%1"=="help" (
    call :show_help
) else if "%1"=="--help" (
    call :show_help
) else if "%1"=="-h" (
    call :show_help
) else (
    call :log_error "未知命令: %1"
    call :show_help
    exit /b 1
)

goto :eof

REM 执行主函数
call :main %* 