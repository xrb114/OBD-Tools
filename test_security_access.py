#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合测试0x27安全访问功能
"""

import sys
import logging
import time
import socket
import argparse

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("安全访问测试")

def send_cmd(sock, cmd, wait_time=0.5):
    """发送命令并接收响应"""
    logger.debug(f"发送: {cmd}")
    sock.sendall(f"{cmd}\r".encode('ascii'))
    time.sleep(wait_time)
    
    response = b''
    try:
        while True:
            sock.settimeout(0.5)
            data = sock.recv(1024)
            if not data:
                break
            response += data
            if response.endswith(b'>'):
                break
    except socket.timeout:
        pass
        
    resp_text = response.decode('ascii', errors='ignore')
    logger.debug(f"接收: {resp_text}")
    return resp_text

def calculate_key(seed_str, level):
    """计算密钥"""
    # 解析种子
    seed_parts = [part for part in seed_str.split() if part.strip() not in ['>', '\r', '\r\r']]
    seed_bytes = bytes([int(b, 16) for b in seed_parts])
    
    # 计算密钥
    if level == '01':  # 级别1
        key_bytes = bytes([~b & 0xFF ^ 0x5A for b in seed_bytes])
    elif level == '03':  # 级别3
        key_bytes = bytes([((b << 1) & 0xFF) ^ 0x3C ^ (i + 1) for i, b in enumerate(seed_bytes)])
    elif level == '05':  # 级别5
        import hashlib
        key_int = int.from_bytes(seed_bytes, byteorder='big')
        hash_value = hashlib.md5(str(key_int).encode()).digest()
        key_bytes = hash_value[:4]
    elif level == '11':  # 扩展级别1
        key_bytes = bytes([b ^ 0x7F ^ (len(seed_bytes) - i) for i, b in enumerate(seed_bytes)])
    else:
        key_bytes = bytes([b ^ 0xFF for b in seed_bytes])
        
    # 返回十六进制字符串
    return ' '.join([f"{b:02X}" for b in key_bytes])

def test_successful_access(host, port, level):
    """测试成功的安全访问"""
    logger.info(f"=== 测试级别 {level} 安全访问（成功）===")
    
    sock = socket.socket()
    try:
        sock.connect((host, port))
        
        # 初始化
        send_cmd(sock, 'ATZ')
        send_cmd(sock, 'ATE0')
        send_cmd(sock, 'ATL0')
        send_cmd(sock, 'ATH0')
        send_cmd(sock, 'ATSP0')
        
        # 请求种子
        seed_level = level
        key_level = f"{int(level) + 1:02d}"
        logger.info(f"请求种子: 27{seed_level}")
        resp = send_cmd(sock, f"27{seed_level}")
        
        if f"67 {seed_level}" not in resp:
            logger.error(f"请求种子失败: {resp}")
            return False
            
        # 提取种子
        seed_parts = resp.split(f"67 {seed_level}")[1].strip().split()
        seed_parts = [part for part in seed_parts if part.strip() not in ['>', '\r', '\r\r']]
        seed = ' '.join(seed_parts)
        logger.info(f"收到种子: {seed}")
        
        # 计算密钥
        key = calculate_key(seed, seed_level)
        logger.info(f"计算密钥: {key}")
        
        # 发送密钥
        logger.info(f"发送密钥: 27{key_level} {key}")
        resp = send_cmd(sock, f"27{key_level} {key}")
        
        # 检查结果
        if f"67 {key_level}" in resp:
            logger.info("安全访问成功!")
            return True
        else:
            logger.error(f"安全访问失败: {resp}")
            return False
    
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
        return False
    
    finally:
        sock.close()

def test_invalid_key(host, port, level):
    """测试无效密钥"""
    logger.info(f"\n=== 测试级别 {level} 安全访问（无效密钥）===")
    
    sock = socket.socket()
    try:
        sock.connect((host, port))
        
        # 初始化
        send_cmd(sock, 'ATZ')
        send_cmd(sock, 'ATE0')
        send_cmd(sock, 'ATL0')
        send_cmd(sock, 'ATH0')
        send_cmd(sock, 'ATSP0')
        
        # 请求种子
        seed_level = level
        key_level = f"{int(level) + 1:02d}"
        logger.info(f"请求种子: 27{seed_level}")
        resp = send_cmd(sock, f"27{seed_level}")
        
        if f"67 {seed_level}" not in resp:
            logger.error(f"请求种子失败: {resp}")
            return False
            
        # 提取种子
        seed = resp.split(f"67 {seed_level}")[1].strip().split()[0]
        logger.info(f"收到种子: {seed}")
        
        # 使用无效密钥
        invalid_key = "AA BB CC DD"
        logger.info(f"发送无效密钥: 27{key_level} {invalid_key}")
        resp = send_cmd(sock, f"27{key_level} {invalid_key}")
        
        # 检查结果
        if "7F 27 35" in resp:
            logger.info("预期结果: 无效密钥错误")
            return True
        else:
            logger.error(f"未收到预期错误: {resp}")
            return False
    
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
        return False
    
    finally:
        sock.close()

def test_seed_expiry(host, port, level, wait_time=6):
    """测试种子过期"""
    logger.info(f"\n=== 测试级别 {level} 安全访问（种子过期）===")
    
    sock = socket.socket()
    try:
        sock.connect((host, port))
        
        # 初始化
        send_cmd(sock, 'ATZ')
        send_cmd(sock, 'ATE0')
        send_cmd(sock, 'ATL0')
        send_cmd(sock, 'ATH0')
        send_cmd(sock, 'ATSP0')
        
        # 请求种子
        seed_level = level
        key_level = f"{int(level) + 1:02d}"
        logger.info(f"请求种子: 27{seed_level}")
        resp = send_cmd(sock, f"27{seed_level}")
        
        if f"67 {seed_level}" not in resp:
            logger.error(f"请求种子失败: {resp}")
            return False
            
        # 提取种子
        seed = resp.split(f"67 {seed_level}")[1].strip().split()[0]
        logger.info(f"收到种子: {seed}")
        
        # 等待种子过期
        logger.info(f"等待{wait_time}秒，使种子过期...")
        time.sleep(wait_time)
        
        # 计算密钥
        key = calculate_key(seed, seed_level)
        logger.info(f"计算密钥: {key}")
        
        # 发送密钥
        logger.info(f"发送密钥: 27{key_level} {key}")
        resp = send_cmd(sock, f"27{key_level} {key}")
        
        # 检查结果
        if "7F 27 24" in resp:
            logger.info("预期结果: 种子已过期")
            return True
        else:
            logger.error(f"未收到预期错误: {resp}")
            return False
    
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
        return False
    
    finally:
        sock.close()

def test_max_attempts(host, port, level):
    """测试最大尝试次数"""
    logger.info(f"\n=== 测试级别 {level} 安全访问（最大尝试次数）===")
    
    sock = socket.socket()
    try:
        sock.connect((host, port))
        
        # 初始化
        send_cmd(sock, 'ATZ')
        send_cmd(sock, 'ATE0')
        send_cmd(sock, 'ATL0')
        send_cmd(sock, 'ATH0')
        send_cmd(sock, 'ATSP0')
        
        # 多次尝试无效密钥
        seed_level = level
        key_level = f"{int(level) + 1:02d}"
        invalid_key = "AA BB CC DD"
        
        logger.info("第1次无效尝试")
        resp = send_cmd(sock, f"27{seed_level}")
        send_cmd(sock, f"27{key_level} {invalid_key}")
        
        logger.info("第2次无效尝试")
        resp = send_cmd(sock, f"27{seed_level}")
        send_cmd(sock, f"27{key_level} {invalid_key}")
        
        logger.info("第3次无效尝试")
        resp = send_cmd(sock, f"27{seed_level}")
        send_cmd(sock, f"27{key_level} {invalid_key}")
        
        # 第4次尝试应该被拒绝
        logger.info("第4次尝试（应被拒绝）")
        resp = send_cmd(sock, f"27{seed_level}")
        
        # 检查结果
        if "7F 27 36" in resp:
            logger.info("预期结果: 超过最大尝试次数")
            return True
        else:
            logger.error(f"未收到预期错误: {resp}")
            return False
    
    except Exception as e:
        logger.error(f"测试过程中出错: {e}")
        return False
    
    finally:
        sock.close()

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='OBD 0x27安全访问测试')
    parser.add_argument('-a', '--address', default='localhost',
                      help='OBD模拟器地址 (默认: localhost)')
    parser.add_argument('-p', '--port', type=int, default=35000,
                      help='OBD模拟器端口 (默认: 35000)')
    parser.add_argument('-t', '--test', default='all',
                      help='测试类型: all, success, invalid, expiry, attempts (默认: all)')
    parser.add_argument('-l', '--level', default='01',
                      help='安全访问级别 (默认: 01)')
    parser.add_argument('-v', '--verbose', action='store_true',
                      help='启用详细日志输出')
    return parser.parse_args()

def main():
    """主函数"""
    args = parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    host = args.address
    port = args.port
    level = args.level
    
    if args.test == 'all' or args.test == 'success':
        test_successful_access(host, port, level)
        
    if args.test == 'all' or args.test == 'invalid':
        test_invalid_key(host, port, level)
        
    if args.test == 'all' or args.test == 'expiry':
        test_seed_expiry(host, port, level)
        
    if args.test == 'all' or args.test == 'attempts':
        test_max_attempts(host, port, level)

if __name__ == "__main__":
    main() 