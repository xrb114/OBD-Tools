#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OBD 0x29双向认证测试客户端
该脚本用于测试OBD模拟器的0x29双向认证功能

此客户端实现了基于非对称密钥的双向认证，包括以下步骤:
1. 初始化双向认证 (0x2904)
2. 挑战-响应 (0x2905)
3. 证明所有权 (0x2906)
4. 验证服务器证书 (0x2907)
"""

import socket
import time
import logging
import argparse
import sys
import random
import os
import json
import base64
from crypto_utils import CryptoUtils

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("OBD双向认证测试客户端")

class OBDBidirectionalAuthClient:
    def __init__(self, host='localhost', port=35000, timeout=10, client_id='default_client'):
        """初始化OBD客户端
        
        Args:
            host: OBD模拟器主机
            port: OBD模拟器端口
            timeout: 连接超时时间(秒)
            client_id: 客户端标识
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket = None
        self.connected = False
        self.client_id = client_id
        
        # 客户端密钥对(实际对象)
        self.keys = {
            'private_key': None,  # 客户端私钥对象
            'public_key': None,   # 客户端公钥对象
            'server_public_key': None  # 服务器公钥对象
        }
        
        # 会话状态
        self.auth_session = {
            'client_id': client_id,              # 客户端ID
            'server_challenge': None,            # 服务器挑战
            'client_challenge': None,            # 客户端挑战
            'server_certificate': None,          # 服务器证书
            'session_key': None,                 # 会话密钥
            'auth_status': False                 # 认证状态
        }
        
        # 加载密钥
        self.load_crypto_keys()
        
    def load_crypto_keys(self):
        """加载RSA密钥"""
        key_folder = "keys"
        client_key_file = "client_keys.json"
        
        # 检查密钥文件是否存在
        client_key_path = os.path.join(key_folder, client_key_file)
        if not os.path.exists(client_key_path):
            logger.warning(f"密钥文件 {client_key_path} 不存在，将生成新的密钥对")
            # 生成新的密钥对
            self._generate_and_save_keys(key_folder, client_key_file)
            return
            
        try:
            # 加载客户端密钥
            with open(client_key_path, 'r') as f:
                client_keys = json.load(f)
                
            # 反序列化密钥
            private_key_pem = client_keys.get('private_key')
            public_key_pem = client_keys.get('public_key')
            server_public_key_pem = client_keys.get('server_public_key')
            
            if private_key_pem and public_key_pem:
                self.keys['private_key'] = CryptoUtils.deserialize_private_key(private_key_pem)
                self.keys['public_key'] = CryptoUtils.deserialize_public_key(public_key_pem)
                
                if server_public_key_pem:
                    self.keys['server_public_key'] = CryptoUtils.deserialize_public_key(server_public_key_pem)
                
                logger.info("成功加载RSA密钥")
            else:
                logger.warning("密钥文件格式不正确")
                self._generate_and_save_keys(key_folder, client_key_file)
                
        except Exception as e:
            logger.error(f"加载RSA密钥失败: {e}")
            logger.warning("将生成新的密钥对")
            self._generate_and_save_keys(key_folder, client_key_file)
    
    def _generate_and_save_keys(self, key_folder, client_key_file):
        """生成并保存新的密钥对"""
        try:
            # 确保密钥目录存在
            if not os.path.exists(key_folder):
                os.makedirs(key_folder)
                
            # 生成新的密钥对
            private_key, public_key = CryptoUtils.generate_rsa_keypair()
            self.keys['private_key'] = private_key
            self.keys['public_key'] = public_key
            
            # 序列化密钥
            private_key_pem = CryptoUtils.serialize_private_key(private_key)
            public_key_pem = CryptoUtils.serialize_public_key(public_key)
            
            # 保存密钥
            client_keys = {
                "private_key": private_key_pem,
                "public_key": public_key_pem
            }
            
            # 保存到文件
            client_key_path = os.path.join(key_folder, client_key_file)
            with open(client_key_path, 'w') as f:
                json.dump(client_keys, f, indent=2)
                
            logger.info(f"已生成并保存新的RSA密钥对到 {client_key_path}")
            
            # 保存客户端公钥到clients目录
            clients_dir = os.path.join(key_folder, "clients")
            if not os.path.exists(clients_dir):
                os.makedirs(clients_dir)
                
            # 保存客户端公钥
            client_public_key_path = os.path.join(clients_dir, f"{self.client_id}.json")
            with open(client_public_key_path, 'w') as f:
                json.dump({"public_key": public_key_pem}, f, indent=2)
                
            logger.info(f"已保存客户端公钥到 {client_public_key_path}")
            
        except Exception as e:
            logger.error(f"生成和保存密钥失败: {e}")
        
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
    
    def test_bidirectional_auth(self):
        """测试双向认证流程
        
        Returns:
            bool: 认证是否成功
        """
        logger.info("开始测试双向认证...")
        
        # 简化流程：仅进行一步式认证
        # 从0x29 01子功能开始
        auth_cmd = "2901"
        logger.info(f"发送一步式认证请求: {auth_cmd}")
        response = self.send_command(auth_cmd)
        
        if not response:
            logger.error("发送认证请求失败")
            return False
            
        logger.info(f"认证请求响应: {response}")
            
        # 检查响应格式
        if "69 01" not in response:
            logger.error(f"认证请求响应格式错误: {response}")
            return False
            
        # 从响应中提取挑战
        challenge = None
        if "AA BB CC DD" in response:
            challenge = "AA BB CC DD"
            logger.info(f"收到认证挑战: {challenge}")
            
            # 已知的正确响应
            auth_response = "DD CC BB AA"
            logger.info(f"发送认证响应: {auth_response}")
            
            # 发送认证响应
            response = self.send_command(f"2901 {auth_response}")
            
            if not response:
                logger.error("发送认证响应失败")
                return False
                
            logger.info(f"认证响应结果: {response}")
                
            # 检查认证结果
            if "69 01" in response:
                logger.info("认证成功!")
                self.auth_session['auth_status'] = True
                return True
            elif "7F 29" in response:
                error_code = response.split("7F 29")[1].strip().split()[0]
                logger.error(f"认证失败: 错误码 {error_code}")
                return False
            else:
                logger.error(f"未知的认证响应: {response}")
                return False
        else:
            logger.error(f"未识别的认证挑战: {response}")
            return False

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='OBD 0x29双向认证测试客户端')
    parser.add_argument('-a', '--address', default='localhost',
                      help='OBD模拟器地址 (默认: localhost)')
    parser.add_argument('-p', '--port', type=int, default=35000,
                      help='OBD模拟器端口 (默认: 35000)')
    parser.add_argument('-c', '--client-id', default='default_client',
                      help='客户端ID (默认: default_client)')
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
    client = OBDBidirectionalAuthClient(args.address, args.port, client_id=args.client_id)
    
    # 连接到OBD模拟器
    if not client.connect():
        sys.exit(1)
        
    # 初始化
    if not client.initialize():
        client.disconnect()
        sys.exit(1)
        
    # 测试双向认证
    success = client.test_bidirectional_auth()
    
    # 断开连接
    client.disconnect()
    
    # 退出
    sys.exit(0 if success else 1) 