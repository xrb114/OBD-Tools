@echo off
REM Git提交脚本
REM 用于自动提交OBD模拟器项目代码

REM 显示当前状态
echo 当前Git状态:
git status

REM 询问用户是否继续
set /p confirm=是否添加所有更改并提交? (y/n): 
if not "%confirm%"=="y" (
    echo 操作已取消
    goto :EOF
)

REM 添加所有文件
git add .

REM 询问提交信息
set /p commit_message=请输入提交信息: 

REM 如果没有输入提交信息，使用默认信息
if "%commit_message%"=="" (
    for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
    set commit_message=更新OBD-II模拟器代码 %datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2% %datetime:~8,2%:%datetime:~10,2%
)

REM 提交代码
git commit -m "%commit_message%"

REM 询问是否推送到远程仓库
set /p push_confirm=是否推送到远程仓库? (y/n): 
if "%push_confirm%"=="y" (
    REM 询问分支名称
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

echo 完成!
pause 