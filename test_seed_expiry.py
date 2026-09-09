#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试0x27安全访问种子过期功能
"""

import socket
import time
import sys

def main():
    print("测试种子过期...")
    try:
        # 连接OBD模拟器
        s = socket.socket()
        s.connect(('localhost', 35000))
        
        # 初始化ELM327
        send_recv(s, 'ATZ')
        send_recv(s, 'ATE0')
        send_recv(s, 'ATL0')
        send_recv(s, 'ATH0')
        send_recv(s, 'ATSP0')
        
        # 请求种子
        print("\n=== 请求种子 ===")
        response = send_recv(s, '2701')
        print(f"请求种子响应: {response}")
        
        # 等待6秒（超过种子有效期）
        print("\n=== 等待6秒（种子过期） ===")
        time.sleep(6)
        
        # 发送密钥
        print("\n=== 发送密钥 ===")
        response = send_recv(s, '2702 A5 A5 00 00')
        print(f"发送密钥响应: {response}")
        
        # 关闭连接
        s.close()
        
    except Exception as e:
        print(f"发生错误: {e}")
        sys.exit(1)

def send_recv(sock, command, wait_time=0.5):
    """发送命令并接收响应"""
    print(f"发送命令: {command}")
    sock.sendall(f"{command}\r".encode('ascii'))
    time.sleep(wait_time)
    
    # 接收响应
    response = b''
    while True:
        try:
            sock.settimeout(0.5)
            data = sock.recv(1024)
            if not data:
                break
            response += data
            # 检查是否响应结束
            if response.endswith(b'>'):
                break
        except socket.timeout:
            break
            
    return response.decode('ascii', errors='ignore')

if __name__ == "__main__":
    main() 