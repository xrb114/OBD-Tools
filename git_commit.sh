#!/bin/bash
# Git提交脚本
# 用于自动提交OBD模拟器项目代码

# 显示当前状态
echo "当前Git状态:"
git status

# 询问用户是否继续
read -p "是否添加所有更改并提交? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo "操作已取消"
    exit 0
fi

# 添加所有文件
git add .

# 询问提交信息
read -p "请输入提交信息: " commit_message

# 如果没有输入提交信息，使用默认信息
if [ -z "$commit_message" ]; then
    commit_message="更新OBD-II模拟器代码 $(date '+%Y-%m-%d %H:%M')"
fi

# 提交代码
git commit -m "$commit_message"

# 询问是否推送到远程仓库
read -p "是否推送到远程仓库? (y/n): " push_confirm
if [ "$push_confirm" = "y" ]; then
    # 询问分支名称
    read -p "请输入要推送的分支名称 (默认: main): " branch_name
    
    # 如果没有输入分支名称，使用默认分支
    if [ -z "$branch_name" ]; then
        branch_name="main"
    fi
    
    # 推送到远程仓库
    git push origin $branch_name
    
    echo "代码已成功推送到远程仓库的 $branch_name 分支"
else
    echo "代码已提交但未推送到远程仓库"
fi

echo "完成!" 