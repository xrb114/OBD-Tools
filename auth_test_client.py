#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OBD 0x29认证测试客户端
该脚本用于测试OBD模拟器的0x29认证功能
"""

import socket
import time
import logging
import argparse
import sys

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("OBD认证测试客户端")

class OBDAuthClient:
    def __init__(self, host='localhost', port=35000, timeout=10):
        """初始化OBD客户端
        
        Args:
            host: OBD模拟器主机
            port: OBD模拟器端口
            timeout: 连接超时时间(秒)
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket = None
        self.connected = False
        self.auth_responses = {
            # 知道的正确认证响应
            'AA BB CC DD': 'DD CC BB AA',  # 01子功能的挑战和响应
            'EE FF 00 11': '11 00 FF EE',  # 02子功能的挑战和响应
            '22 33 44 55': '55 44 33 22'   # 03子功能的挑战和响应
        }
        
    def connect(self):
        """连接到OBD模拟器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info(f"已连接到OBD模拟器 {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"连接到OBD模拟器失败: {e}")
            self.connected = False
            return False
            
    def disconnect(self):
        """断开与OBD模拟器的连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.connected = False
        logger.info("已断开与OBD模拟器的连接")
        
    def send_command(self, command, wait_time=0.5):
        """发送命令并获取响应"""
        if not self.connected:
            logger.error("未连接到OBD模拟器")
            return None
            
        try:
            # 发送命令
            logger.debug(f"发送命令: {command}")
            self.socket.sendall(f"{command}\r".encode('ascii'))
            
            # 等待响应
            time.sleep(wait_time)
            
            # 读取响应
            response = b''
            while True:
                try:
                    self.socket.settimeout(0.5)
                    data = self.socket.recv(1024)
                    if not data:
                        break
                    response += data
                    # 检查是否响应结束
                    if response.endswith(b'>'):
                        break
                except socket.timeout:
                    break
                    
            # 解码响应
            response_text = response.decode('ascii', errors='replace')
            logger.debug(f"收到响应: {response_text}")
            return response_text
        except Exception as e:
            logger.error(f"发送命令时出错: {e}")
            return None
    
    def initialize(self):
        """初始化ELM327"""
        logger.info("初始化OBD连接...")
        
        # 复位
        response = self.send_command("ATZ")
        if not response or "ELM327" not in response:
            logger.error("ELM327复位失败")
            return False
            
        # 关闭回显
        self.send_command("ATE0")
        
        # 关闭换行
        self.send_command("ATL0")
        
        # 关闭头部信息
        self.send_command("ATH0")
        
        # 设置协议
        self.send_command("ATSP0")
        
        logger.info("OBD连接初始化完成")
        return True
    
    def test_auth(self, sub_func='01', invalid_test=False):
        """测试0x29认证
        
        Args:
            sub_func: 子功能代码 ('01', '02', '03')
            invalid_test: 是否测试无效认证
            
        Returns:
            bool: 认证是否成功
        """
        # 发送认证请求
        auth_cmd = f"29{sub_func}"
        logger.info(f"发送认证请求: {auth_cmd}")
        response = self.send_command(auth_cmd)
        
        if not response:
            logger.error("发送认证请求失败")
            return False
        
        logger.info(f"认证请求响应: {response}")
            
        # 检查响应格式
        if f"69 {sub_func}" not in response:
            logger.error(f"认证请求响应格式错误: {response}")
            return False
            
        # 解析挑战
        challenge = None
        for known_challenge in self.auth_responses.keys():
            if known_challenge in response:
                challenge = known_challenge
                break
                
        if not challenge:
            logger.error(f"未识别的认证挑战: {response}")
            return False
            
        logger.info(f"收到认证挑战: {challenge}")
        
        # 准备认证响应
        if invalid_test:
            # 使用无效响应进行测试
            auth_response = "INVALID RESPONSE"
            logger.info(f"发送无效认证响应: {auth_response}")
        else:
            # 使用有效响应
            auth_response = self.auth_responses[challenge]
            logger.info(f"发送认证响应: {auth_response}")
            
        # 发送认证响应
        response = self.send_command(f"29{sub_func} {auth_response}")
        
        if not response:
            logger.error("发送认证响应失败")
            return False
            
        # 检查认证结果
        if f"69 {sub_func}" in response:
            logger.info("认证成功!")
            return True
        elif "7F 29 35" in response:
            logger.warning("认证失败: 无效密钥")
            return False
        elif "7F 29 36" in response:
            logger.warning("认证失败: 超过尝试次数")
            return False
        elif "7F 29 37" in response:
            logger.warning("认证失败: 超时未过期")
            return False
        else:
            logger.error(f"未知的认证响应: {response}")
            return False

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='OBD 0x29认证测试客户端')
    parser.add_argument('-a', '--address', default='localhost',
                      help='OBD模拟器地址 (默认: localhost)')
    parser.add_argument('-p', '--port', type=int, default=35000,
                      help='OBD模拟器端口 (默认: 35000)')
    parser.add_argument('-f', '--func', default='01', choices=['01', '02', '03'],
                      help='认证子功能 (默认: 01)')
    parser.add_argument('-i', '--invalid', action='store_true',
                      help='测试无效认证')
    parser.add_argument('-v', '--verbose', action='store_true',
                      help='启用详细日志输出')
    return parser.parse_args()

if __name__ == "__main__":
    # 解析命令行参数
    args = parse_args()
    
    # 设置日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # 创建客户端
    client = OBDAuthClient(args.address, args.port)
    
    # 连接到OBD模拟器
    if not client.connect():
        sys.exit(1)
        
    # 初始化
    if not client.initialize():
        client.disconnect()
        sys.exit(1)
        
    # 测试认证
    success = client.test_auth(args.func, args.invalid)
    
    # 断开连接
    client.disconnect()
    
    # 退出
    sys.exit(0 if success else 1) 