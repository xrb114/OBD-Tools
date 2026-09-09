@echo off
REM Git选择性提交脚本
REM 用于选择性提交OBD模拟器项目代码

REM 显示当前状态
echo 当前Git状态:
git status

echo.
echo 请选择提交模式:
echo 1. 提交所有更改
echo 2. 选择性提交文件
echo 3. 仅提交特定扩展名文件
echo 4. 退出
echo.

set /p choice=请输入选项 (1-4): 

if "%choice%"=="1" (
    REM 提交所有更改
    git add .
    echo 已添加所有文件到暂存区
) else if "%choice%"=="2" (
    REM 选择性提交文件
    echo.
    echo 修改的文件列表:
    git diff --name-only
    
    echo.
    echo 请输入要提交的文件，多个文件用空格分隔
    echo 例如: file1.py file2.py 或 *.py 以添加所有Python文件
    echo.
    
    set /p files=文件列表: 
    
    git add %files%
    echo 已添加选定文件到暂存区
) else if "%choice%"=="3" (
    REM 提交特定扩展名文件
    echo.
    echo 请输入要提交的文件扩展名（不含点，如 py 表示所有.py文件）
    set /p ext=文件扩展名: 
    
    git add *.%ext%
    echo 已添加所有 .%ext% 文件到暂存区
) else if "%choice%"=="4" (
    echo 操作已取消
    goto :EOF
) else (
    echo 无效选项，操作已取消
    goto :EOF
)

REM 显示已暂存的文件
echo.
echo 已暂存的更改:
git diff --cached --name-only

REM 询问提交信息
echo.
set /p commit_message=请输入提交信息: 

REM 如果没有输入提交信息，使用默认信息
if "%commit_message%"=="" (
    for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
    set commit_message=更新OBD-II模拟器代码 %datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2% %datetime:~8,2%:%datetime:~10,2%
)

REM 确认提交
echo.
echo 即将提交以下更改，使用提交信息: "%commit_message%"
git diff --cached --name-only
echo.

set /p confirm=确认提交? (y/n): 
if not "%confirm%"=="y" (
    echo 提交已取消
    goto :EOF
)

REM 提交代码
git commit -m "%commit_message%"

REM 询问是否推送到远程仓库
echo.
set /p push_confirm=是否推送到远程仓库? (y/n): 
if "%push_confirm%"=="y" (
    REM 显示可用分支
    echo.
    echo 可用的本地分支:
    git branch
    
    REM 询问分支名称
    echo.
    set /p branch_name=请输入要推送的分支名称 (默认: main): 
    
    REM 如果没有输入分支名称，使用默认分支
    if "%branch_name%"=="" (
        set branch_name=main
    )
    
    REM 推送到远程仓库
    git push origin %branch_name%
    
    echo 代码已成功推送到远程仓库的 %branch_name% 分支
) else (
    echo 代码已提交但未推送到远程仓库
)

echo.
echo 完成!
pause