#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OBD 0x27安全访问测试客户端
该脚本用于测试OBD模拟器的0x27安全访问功能
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
logger = logging.getLogger("OBD安全访问测试客户端")

class OBDSecurityClient:
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
    
    def calculate_key(self, seed_str, level):
        """计算对应种子的密钥
        
        Args:
            seed_str: 十六进制种子字符串，例如"A5 B7 C9"
            level: 安全访问级别
            
        Returns:
            str: 十六进制密钥字符串
        """
        # 解析种子值
        seed_bytes = bytes([int(b, 16) for b in seed_str.split()])
        
        # 不同级别使用不同的算法计算密钥
        if level == '01':  # 级别1密钥计算
            # 简单算法：反转字节 + XOR 0x5A
            key_bytes = bytes([~b & 0xFF ^ 0x5A for b in seed_bytes])
        elif level == '03':  # 级别3密钥计算
            # 使用左移和异或
            key_bytes = bytes([((b << 1) & 0xFF) ^ 0x3C ^ (i + 1) for i, b in enumerate(seed_bytes)])
        elif level == '05':  # 级别5密钥计算
            # 使用哈希算法
            import hashlib
            key_int = int.from_bytes(seed_bytes, byteorder='big')
            hash_value = hashlib.md5(str(key_int).encode()).digest()
            key_bytes = hash_value[:4]  # 取前4字节
        elif level == '11':  # 扩展诊断级别1
            # 使用异或和重排
            key_bytes = bytes([b ^ 0x7F ^ (len(seed_bytes) - i) for i, b in enumerate(seed_bytes)])
        else:
            # 默认算法：简单异或
            key_bytes = bytes([b ^ 0xFF for b in seed_bytes])
            
        # 转换为十六进制字符串
        key_hex = ' '.join([f"{b:02X}" for b in key_bytes])
        return key_hex
    
    def test_security_access(self, level='01', invalid_test=False, wait_seconds=0):
        """测试0x27安全访问
        
        Args:
            level: 安全访问级别 ('01', '03', '05', '11')
            invalid_test: 是否测试无效密钥
            wait_seconds: 请求种子和发送密钥之间的等待时间(秒)
            
        Returns:
            bool: 安全访问是否成功
        """
        # 发送请求种子
        seed_level = level
        key_level = f"{int(level) + 1:02d}"  # 计算对应的密钥级别
        
        # 1. 请求种子
        seed_cmd = f"27{seed_level}"
        logger.info(f"请求安全访问种子: {seed_cmd}")
        response = self.send_command(seed_cmd)
        
        if not response:
            logger.error("发送请求种子命令失败")
            return False
        
        # 解析种子
        if f"67 {seed_level}" not in response:
            if "7F 27" in response:
                error_code = response.split("7F 27")[1].strip().split()[0]
                logger.error(f"请求种子失败: 错误码 {error_code}")
                return False
            logger.error(f"请求种子响应格式错误: {response}")
            return False
            
        # 提取种子
        seed_parts = response.strip().split(f"67 {seed_level}")[1].strip().split()
        # 过滤掉可能出现的'>'字符
        seed_parts = [part for part in seed_parts if part.strip() != '>' and part.strip() != '\r' and part.strip() != '\r\r']
        seed = ' '.join(seed_parts)
        logger.info(f"收到种子: {seed}")
        
        # 可选：等待一段时间测试种子过期
        if wait_seconds > 0:
            logger.info(f"等待 {wait_seconds} 秒测试种子过期...")
            time.sleep(wait_seconds)
        
        # 2. 计算密钥
        if invalid_test:
            # 使用无效密钥
            key = "AA BB CC DD"  # 随机无效密钥
            logger.info(f"使用无效密钥进行测试: {key}")
        else:
            # 计算正确的密钥
            key = self.calculate_key(seed, seed_level)
            logger.info(f"计算得到密钥: {key}")
        
        # 3. 发送密钥
        key_cmd = f"27{key_level} {key}"
        logger.info(f"发送密钥: {key_cmd}")
        response = self.send_command(key_cmd)
        
        if not response:
            logger.error("发送密钥命令失败")
            return False
            
        # 4. 检查结果
        if f"67 {key_level}" in response:
            logger.info("安全访问成功!")
            return True
        elif "7F 27" in response:
            error_code = response.split("7F 27")[1].strip().split()[0]
            logger.error(f"安全访问失败: 错误码 {error_code}")
            return False
        else:
            logger.error(f"安全访问响应格式错误: {response}")
            return False

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='OBD 0x27安全访问测试客户端')
    parser.add_argument('-a', '--address', default='localhost',
                      help='OBD模拟器地址 (默认: localhost)')
    parser.add_argument('-p', '--port', type=int, default=35000,
                      help='OBD模拟器端口 (默认: 35000)')
    parser.add_argument('-l', '--level', default='01',
                      help='安全访问级别 (默认: 01)')
    parser.add_argument('-i', '--invalid', action='store_true',
                      help='测试无效密钥')
    parser.add_argument('-w', '--wait', type=int, default=0,
                      help='请求种子和发送密钥之间的等待时间(秒)，用于测试种子过期 (默认: 0)')
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
    client = OBDSecurityClient(args.address, args.port)
    
    # 连接到OBD模拟器
    if not client.connect():
        sys.exit(1)
        
    # 初始化
    if not client.initialize():
        client.disconnect()
        sys.exit(1)
        
    # 测试安全访问
    success = client.test_security_access(args.level, args.invalid, args.wait)
    
    # 断开连接
    client.disconnect()
    
    # 退出
    sys.exit(0 if success else 1) 