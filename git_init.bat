@echo off
REM Git初始化脚本
REM 用于初始化OBD模拟器项目的Git仓库

echo OBD-II模拟器项目 - Git初始化脚本

REM 检查是否已经初始化
if exist .git (
    echo Git仓库已存在，无需初始化。
    goto :already_initialized
)

echo 正在初始化Git仓库...
git init

REM 创建.gitignore文件
echo 创建.gitignore文件...
echo # Python相关文件 > .gitignore
echo __pycache__/ >> .gitignore
echo *.py[cod] >> .gitignore
echo *$py.class >> .gitignore
echo *.so >> .gitignore
echo .Python >> .gitignore
echo venv/ >> .gitignore
echo env/ >> .gitignore
echo ENV/ >> .gitignore
echo # 项目特定文件 >> .gitignore
echo keys/**/client_keys.json >> .gitignore
echo # 临时文件 >> .gitignore
echo *.log >> .gitignore
echo .*.swp >> .gitignore
echo # IDE相关 >> .gitignore
echo .idea/ >> .gitignore
echo .vscode/ >> .gitignore
echo # 确保keys/clients目录被跟踪 >> .gitignore
echo !keys/clients/ >> .gitignore

REM 添加README.md和所有Python文件
echo 添加文件到Git仓库...
git add README.md
git add *.py
git add .gitignore

REM 初始提交
echo 正在创建初始提交...
git commit -m "初始化OBD-II模拟器项目"

:already_initialized

REM 配置远程仓库
echo.
echo 是否需要配置远程仓库? 
set /p configure_remote=请选择 (y/n): 

if not "%configure_remote%"=="y" goto :end

echo.
echo 请输入远程仓库URL (例如: https://github.com/username/repository.git)
set /p remote_url=远程仓库URL: 

if "%remote_url%"=="" (
    echo 未提供有效的URL，跳过远程仓库配置
    goto :end
)

REM 添加远程仓库
git remote add origin %remote_url%
echo 已添加远程仓库: origin -> %remote_url%

REM 询问是否推送
echo.
set /p push_now=是否立即推送到远程仓库? (y/n): 

if not "%push_now%"=="y" goto :end

echo.
set /p branch_name=请输入要推送的分支名 (默认: main): 

if "%branch_name%"=="" (
    set branch_name=main
)

REM 推送到远程仓库
git push -u origin %branch_name%

:end
echo.
echo Git初始化完成！
pause 