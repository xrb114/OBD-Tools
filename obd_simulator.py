#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###########################################################################
# OBD 模拟器
# 基于ELM327-emulator项目的脚本，用于模拟 ELM327 OBD-II 适配器连接到车辆
# https://github.com/Ircama/ELM327-emulator
###########################################################################

import os
import sys
import time
import logging
import argparse
import signal
import socket
import threading
import random
import re
import json
import hashlib
from datetime import datetime
from crypto_utils import CryptoUtils

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("OBD模拟器")

# 支持的AT命令
AT_COMMANDS = {
    'ATZ': 'ELM327 v1.5\r\r>',
    'ATE0': 'OK\r\r>',  # 关闭回显
    'ATE1': 'OK\r\r>',  # 打开回显
    'ATL0': 'OK\r\r>',  # 关闭换行符
    'ATL1': 'OK\r\r>',  # 打开换行符
    'ATH0': 'OK\r\r>',  # 隐藏标头
    'ATH1': 'OK\r\r>',  # 显示标头
    'ATS0': 'OK\r\r>',  # 关闭空格
    'ATS1': 'OK\r\r>',  # 打开空格
    'ATSP0': 'OK\r\r>',  # 自动协议
    'ATI': 'ELM327 v1.5\r\r>',  # 版本信息
    'ATDP': 'AUTO\r\r>',  # 显示协议
    'ATRV': '14.2V\r\r>',  # 电压
    'AT@1': 'OBDII to RS232 Interpreter\r\r>'
}

# 支持的OBD-II PID响应
OBD_RESPONSES = {
    # 模式01 (当前数据)
    '0100': '41 00 BE 3E B8 10\r\r>',  # 支持的PID 01-20
    '0101': '41 01 00 07 E5 00\r\r>',  # 监控状态
    '0104': '41 04 20\r\r>',           # 计算的发动机负载
    '0105': '41 05 3C\r\r>',           # 发动机冷却液温度 (60℃)
    '0106': '41 06 FF\r\r>',           # 短期燃油修正 - 组1
    '0107': '41 07 03\r\r>',           # 长期燃油修正 - 组1
    '010C': '41 0C 1A F8\r\r>',        # 发动机转速 (1740 RPM)
    '010D': '41 0D 46\r\r>',           # 车速 (70 km/h)
    '010F': '41 0F 2E\r\r>',           # 进气温度 (46℃)
    '0110': '41 10 24 1A\r\r>',        # MAF空气流量率
    '0111': '41 11 2A\r\r>',           # 节气门位置 (42%)
    '0113': '41 13 03\r\r>',           # 氧传感器位置
    '011C': '41 1C 01\r\r>',           # OBD标准
    '011F': '41 1F 00 CF\r\r>',        # 发动机运行时间
    '0121': '41 21 00 00\r\r>',
    '0170': '41 21 00\r\r',
    # MIL行程距离
    
    # 模式03 (故障码)
    #'03': '43 00\r\r>',                # 无故障码
    #'03':'43 02 03 00 04 20\r\r',
    '03': '43 02 03 00 03 01\r\r',
    # 模式09 (车辆信息)
    '0902': '49 02 01 31 5A 5A 5A 5A 5A\r\r>', # VIN (部分)
    
    # 模式27 (安全访问)
    '2701': '67 01 A5 B7 C9\r\r>',     # 请求种子
    '2702': '67 02\r\r>',              # 发送密钥 (成功)
    
    # 模式29 (认证)
    '2901': '69 01 AA BB CC DD\r\r>',  # 认证挑战(deAuthenticateAll)
    '2902': '69 02 EE FF 00 11\r\r>',  # 认证挑战(authenticateOneSender)
    '2903': '69 03 22 33 44 55\r\r>',  # 认证挑战(authenticateOneReceiver)
    
    # 模式29 (认证) - 双向认证子功能
    '2904': '69 04 11 22 33 44 55 66 77 88 SERVER_CERT_01 FF EE DD CC BB AA 99 88\r\r>',  # 双向认证初始化，返回挑战和证书
    '2905': '69 05 SIG_SERVER_PRIVATE_KEY_789012_44556677\r\r>',  # 挑战响应
    '2906': '69 06\r\r>',              # 所有权验证成功
    '2907': '69 07 SERVER_CERT_01 FF EE DD CC BB AA 99 88\r\r>'   # 服务器证书
}

# 动态数据模拟类
class DynamicDataSimulator:
    def __init__(self):
        self.engine_rpm = 800
        self.vehicle_speed = 0
        self.engine_temp = 80
        self.throttle_pos = 0
        self.maf_rate = 8.0
        self.engine_load = 20
        self.last_update = time.time()
        self.running = False
        
        # 认证相关状态
        self.auth_status = False  # 是否通过认证
        self.auth_attempts = 0    # 认证尝试次数
        self.auth_challenges = {} # 存储认证挑战和对应的有效响应
        self.auth_keys = {        # 存储不同认证级别的密钥
            '01': 'A1B2C3D4',     # deAuthenticateAll的密钥
            '02': 'E5F6G7H8',     # authenticateOneSender的密钥
            '03': '12345678'      # authenticateOneReceiver的密钥
        }
        self.auth_timeout = None  # 认证超时时间
        self.load_auth_challenges()  # 加载认证挑战和响应
        
        # 安全访问相关状态
        self.security_access = {
            'status': False,        # 安全访问状态
            'level': None,          # 安全访问级别
            'seed': None,           # 当前种子
            'attempts': 0,          # 尝试次数
            'timeout': None,        # 超时时间
            'last_seed_time': None, # 上次请求种子的时间
            'seed_validity': 5      # 种子有效期(秒)
        }
        
        # 非对称密钥支持
        self.asymmetric_keys = {
            'private_key': None,   # 服务器私钥对象
            'public_key': None,    # 服务器公钥对象
            'client_public_keys': {}  # 客户端公钥对象字典
        }
        self.mutual_auth_session = {                    # 双向认证会话
            'client_id': None,                          # 客户端标识
            'server_challenge': None,                   # 服务器挑战
            'client_challenge': None,                   # 客户端挑战
            'auth_level': None,                         # 认证级别
            'session_key': None,                        # 会话密钥
            'timestamp': None                           # 时间戳
        }
        self.load_crypto_keys()  # 加载加密密钥
        
    def start(self):
        """启动模拟器"""
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        
    def stop(self):
        """停止模拟器"""
        self.running = False
        if hasattr(self, 'update_thread'):
            self.update_thread.join(timeout=1.0)
        
    def _update_loop(self):
        """更新循环，模拟车辆数据变化"""
        while self.running:
            time.sleep(0.5)
            self._update_values()
            
    def _update_values(self):
        """更新模拟值"""
        # 随机变化发动机转速
        self.engine_rpm += random.randint(-50, 50)
        self.engine_rpm = max(700, min(6000, self.engine_rpm))
        
        # 更新车速
        if random.random() < 0.1:  # 10%的概率改变车速趋势
            speed_trend = random.choice([-1, 0, 1])
            if speed_trend == 1:
                self.vehicle_speed += random.randint(1, 5)
            elif speed_trend == -1:
                self.vehicle_speed -= random.randint(1, 5)
        self.vehicle_speed = max(0, min(220, self.vehicle_speed))
        
        # 更新节气门位置
        self.throttle_pos += random.randint(-3, 3)
        self.throttle_pos = max(0, min(100, self.throttle_pos))
        
        # 更新发动机负载
        self.engine_load = 15 + (self.throttle_pos / 100.0) * 70 + random.randint(-5, 5)
        self.engine_load = max(0, min(100, self.engine_load))
        
        # 更新MAF
        self.maf_rate = 2.0 + (self.engine_rpm / 1000.0) * 5.0 + random.random() * 2.0
        
        # 更新发动机温度 (缓慢变化)
        if self.engine_rpm > 2000:
            self.engine_temp += 0.1
        elif self.engine_temp > 80:
            self.engine_temp -= 0.05
        self.engine_temp = max(70, min(110, self.engine_temp))
    
    def load_auth_challenges(self):
        """加载认证挑战和对应的有效响应"""
        # 这里可以从配置文件加载，但为简化实现，直接硬编码
        self.auth_challenges = {
            'AA BB CC DD': 'DD CC BB AA',  # 01子功能的挑战和响应
            'EE FF 00 11': '11 00 FF EE',  # 02子功能的挑战和响应
            '22 33 44 55': '55 44 33 22'   # 03子功能的挑战和响应
        }
    
    def auth_handler(self, sub_function, data=None):
        """处理0x29认证请求
        
        Args:
            sub_function: 子功能代码，比如'01', '02', '03'
            data: 客户端发来的数据，通常是认证响应
            
        Returns:
            str: 响应字符串
        """
        current_time = time.time()
        
        # 检查认证尝试次数
        if self.auth_attempts >= 3 and (self.auth_timeout is None or current_time < self.auth_timeout):
            # 如果尝试次数过多且在超时时间内，返回错误
            return '7F 29 36\r\r>'  # 36 = 超过尝试次数
            
        if self.auth_timeout and current_time < self.auth_timeout:
            # 如果在超时时间内，返回错误
            return '7F 29 37\r\r>'  # 37 = 超时未过期
            
        # 重置超时
        self.auth_timeout = None
        
        # 基本认证子功能 01-03
        if sub_function in ['01', '02', '03']:
            if not data:
                # 请求挑战，返回认证挑战
                return OBD_RESPONSES[f'29{sub_function}']
            else:
                # 处理客户端发送的认证响应
                challenge = None
                for key, value in self.auth_challenges.items():
                    if value.replace(' ', '') == data.replace(' ', ''):
                        challenge = key
                        break
                
                if challenge:
                    # 认证成功
                    self.auth_status = True
                    self.auth_attempts = 0
                    return f'69 {sub_function}\r\r>'  # 成功响应
                else:
                    # 认证失败
                    self.auth_attempts += 1
                    if self.auth_attempts >= 3:
                        self.auth_timeout = current_time + 10  # 设置10秒超时
                    return '7F 29 35\r\r>'  # 35 = 无效密钥
        
        # 处理非对称加密的双向认证
        elif sub_function == '04':  # 添加新的子功能: bidirectionalCertificateExchange
            return self._handle_bidirectional_auth(data)
        elif sub_function == '05':  # 添加新的子功能: challengeResponse
            return self._handle_challenge_response(data)
        elif sub_function == '06':  # 添加新的子功能: verifyProofOfOwnership
            return self._handle_proof_of_ownership(data)
        elif sub_function == '07':  # 添加新的子功能: verifyServerCertificate
            return self._handle_server_certificate(data)
        else:
            # 不支持的子功能
            return '7F 29 12\r\r>'  # 12 = 子功能不支持
    
    def _handle_bidirectional_auth(self, data):
        """处理双向认证的初始化请求
        
        Args:
            data: 客户端提供的数据，包含客户端ID和请求的认证级别
            
        Returns:
            str: 响应字符串，包含服务器挑战和证书
        """
        # 解析客户端数据
        client_id = "default_client"  # 默认客户端ID
        auth_level = "full_access"    # 默认认证级别
        
        if data:
            parts = data.strip().split()
            if len(parts) >= 1:
                client_id = parts[0]
            if len(parts) >= 2:
                auth_level = parts[1]
        
        # 重置会话状态
        server_challenge = CryptoUtils.generate_hex_challenge(8)  # 生成8字节(64位)的挑战
        
        self.mutual_auth_session = {
            'client_id': client_id,
            'auth_level': auth_level,
            'server_challenge': server_challenge,
            'client_challenge': None,
            'session_key': None,
            'timestamp': time.time()
        }
        
        # 获取服务器证书（这里简化为使用公钥PEM的前100个字符）
        server_cert = "NO_CERTIFICATE"
        if self.asymmetric_keys['public_key']:
            try:
                # 获取公钥PEM格式的摘要作为证书
                public_key_pem = CryptoUtils.serialize_public_key(self.asymmetric_keys['public_key'])
                cert_digest = hashlib.sha256(public_key_pem.encode()).hexdigest()[:40]
                server_cert = f"SERVER_CERT_{cert_digest}"
            except Exception as e:
                logger.error(f"生成服务器证书失败: {e}")
        
        logger.info(f"启动双向认证，客户端ID: {client_id}，挑战: {server_challenge}")
        
        # 返回挑战和证书（格式：子功能 + 挑战 + 证书）
        return f'69 04 {server_challenge} {server_cert}\r\r>'
    
    def _handle_challenge_response(self, data):
        """处理客户端对服务器挑战的响应，并发送客户端挑战
        
        Args:
            data: 客户端响应，包含对服务器挑战的签名和客户端挑战
            
        Returns:
            str: 响应字符串，包含对客户端挑战的响应
        """
        if not self.mutual_auth_session['server_challenge']:
            return '7F 29 24\r\r>'  # 24 = 请求顺序错误
        
        # 解析客户端数据
        client_signature = None
        client_challenge = None
        
        if data:
            parts = data.strip().split()
            
            # 查找客户端挑战开始的位置
            challenge_start = -1
            for i, part in enumerate(parts):
                # 客户端挑战通常是十六进制字节
                if len(part) == 2 and all(c in '0123456789ABCDEFabcdef' for c in part):
                    challenge_start = i
                    break
                    
            if challenge_start != -1:
                # 提取签名和挑战
                client_signature = ' '.join(parts[:challenge_start])
                client_challenge = ' '.join(parts[challenge_start:])
            else:
                # 如果找不到明确的挑战部分，假设前半部分是签名，后半部分是挑战
                middle = len(parts) // 2
                client_signature = ' '.join(parts[:middle])
                client_challenge = ' '.join(parts[middle:])
            
            # 确保有签名和挑战
            if not client_signature or not client_challenge:
                logger.error(f"无法解析客户端签名和挑战: {data}")
                return '7F 29 35\r\r>'  # 35 = 无效密钥/数据格式错误
        else:
            return '7F 29 35\r\r>'  # 35 = 无效密钥/数据格式错误
            
        # 验证客户端签名
        signature_valid = False
        client_id = self.mutual_auth_session['client_id']
        
        logger.info(f"收到客户端签名: {client_signature}")
        logger.info(f"收到客户端挑战: {client_challenge}")
        logger.info(f"客户端ID: {client_id}")
        logger.info(f"已加载的客户端公钥数量: {len(self.asymmetric_keys['client_public_keys'])}")
        logger.info(f"已加载的客户端: {list(self.asymmetric_keys['client_public_keys'].keys())}")
        
        # 检查签名格式，提取客户端ID
        extracted_client_id = None
        if "SIG_CLIENT_" in client_signature:
            # 尝试从签名中提取客户端ID
            try:
                # 格式: SIG_CLIENT_<client_id>_AUTH
                parts = client_signature.split('_')
                if len(parts) >= 3:
                    extracted_client_id = parts[2]
                    logger.info(f"从签名中提取的客户端ID: {extracted_client_id}")
            except:
                pass
                
        # 使用提取的客户端ID替换会话中的ID
        if extracted_client_id:
            client_id = extracted_client_id
            self.mutual_auth_session['client_id'] = client_id
            logger.info(f"使用从签名中提取的客户端ID: {client_id}")
        
        # 开发环境下，简化签名验证，接受任何包含SIG_CLIENT前缀的签名
        if "SIG_CLIENT_" in client_signature:
            logger.info(f"开发环境下: 接受包含SIG_CLIENT前缀的签名: {client_signature}")
            signature_valid = True
        
        if not signature_valid:
            self.auth_attempts += 1
            if self.auth_attempts >= 3:
                self.auth_timeout = time.time() + 10
            return '7F 29 35\r\r>'  # 35 = 无效密钥
        
        # 保存客户端挑战
        self.mutual_auth_session['client_challenge'] = client_challenge
        
        # 生成对客户端挑战的响应（使用服务器私钥签名）
        server_response = "NO_SIGNATURE"
        if self.asymmetric_keys['private_key']:
            try:
                # 对客户端挑战进行签名
                challenge_bytes = CryptoUtils.hex_challenge_to_bytes(client_challenge)
                signature = CryptoUtils.sign_data(self.asymmetric_keys['private_key'], challenge_bytes)
                
                # 简化签名格式，适应OBD传输
                server_response = f"SIG_SERVER_AUTH_{int(time.time()) % 10000:04X}"
            except Exception as e:
                logger.error(f"生成签名失败: {e}")
        
        logger.info(f"接收到客户端挑战: {client_challenge}，响应: {server_response}")
        
        # 返回对客户端挑战的响应
        return f'69 05 {server_response}\r\r>'
    
    def _handle_proof_of_ownership(self, data):
        """验证客户端对密钥的所有权证明
        
        Args:
            data: 客户端提供的所有权证明
            
        Returns:
            str: 响应字符串，认证成功或失败
        """
        if not self.mutual_auth_session['client_challenge']:
            return '7F 29 24\r\r>'  # 24 = 请求顺序错误
        
        # 验证客户端所有权证明
        # 实际实现应当验证客户端提供的密钥所有权证明
        # 这里简化处理，接受任何所有权证明
        proof_valid = True
        
        if not proof_valid:
            self.auth_attempts += 1
            if self.auth_attempts >= 3:
                self.auth_timeout = time.time() + 10
            return '7F 29 58\r\r>'  # 58 = 所有权验证失败
        
        # 生成会话密钥
        try:
            # 使用服务器挑战和客户端挑战生成会话密钥
            server_challenge = self.mutual_auth_session['server_challenge']
            client_challenge = self.mutual_auth_session['client_challenge']
            session_key = CryptoUtils.generate_session_key(server_challenge, client_challenge)
            
            self.mutual_auth_session['session_key'] = session_key
            self.auth_status = True
            self.auth_attempts = 0
            
            logger.info(f"客户端所有权验证成功，生成会话密钥: {session_key[:16]}...")
        except Exception as e:
            logger.error(f"生成会话密钥失败: {e}")
        
        # 会话建立成功，返回成功响应
        return f'69 06\r\r>'
    
    def _handle_server_certificate(self, data):
        """处理客户端对服务器证书的验证请求
        
        Args:
            data: 客户端提供的数据
            
        Returns:
            str: 响应字符串，包含服务器证书
        """
        # 生成服务器证书
        server_cert = "NO_CERTIFICATE"
        if self.asymmetric_keys['public_key']:
            try:
                # 获取公钥PEM格式的摘要作为证书
                public_key_pem = CryptoUtils.serialize_public_key(self.asymmetric_keys['public_key'])
                cert_digest = hashlib.sha256(public_key_pem.encode()).hexdigest()[:40]
                server_cert = f"SERVER_CERT_{cert_digest}"
            except Exception as e:
                logger.error(f"生成服务器证书失败: {e}")
        
        logger.info(f"发送服务器证书给客户端")
        
        # 返回服务器证书
        return f'69 07 {server_cert}\r\r>'
    
    def _generate_seed(self, level):
        """生成安全访问种子
        
        Args:
            level: 安全访问级别
            
        Returns:
            str: 十六进制种子字符串
        """
        # 基于当前时间和随机数生成种子
        timestamp = int(time.time())
        random_bytes = random.getrandbits(16)
        
        # 不同级别使用不同的算法生成种子
        if level == '01':  # 请求种子 (级别1)
            seed_value = (timestamp & 0xFF) ^ random_bytes ^ 0xA5
        elif level == '03':  # 请求种子 (级别3)
            seed_value = ((timestamp & 0xFF) << 8) ^ random_bytes ^ 0xB7
        elif level == '05':  # 请求种子 (级别5)
            seed_value = (timestamp & 0xFFFF) ^ random_bytes ^ 0xC9
        elif level == '11':  # 扩展诊断模式种子 (级别1)
            seed_value = (timestamp & 0xFF) ^ (random_bytes >> 8) ^ 0xD1
        else:
            seed_value = random_bytes  # 默认种子
            
        # 生成2-4字节的种子
        seed_bytes = seed_value.to_bytes(4, byteorder='big')
        seed_hex = ' '.join([f"{b:02X}" for b in seed_bytes])
        
        return seed_hex
        
    def _calculate_key(self, seed_hex, level):
        """计算对应种子的密钥
        
        Args:
            seed_hex: 十六进制种子字符串
            level: 安全访问级别
            
        Returns:
            str: 十六进制密钥字符串
        """
        # 解析种子值
        seed_bytes = bytes([int(b, 16) for b in seed_hex.split()])
        
        # 不同级别使用不同的算法计算密钥
        if level == '01':  # 级别1密钥计算
            # 简单算法：反转字节 + XOR 0x5A
            key_bytes = bytes([~b & 0xFF ^ 0x5A for b in seed_bytes])
        elif level == '03':  # 级别3密钥计算
            # 使用左移和异或
            key_bytes = bytes([((b << 1) & 0xFF) ^ 0x3C ^ (i + 1) for i, b in enumerate(seed_bytes)])
        elif level == '05':  # 级别5密钥计算
            # 使用哈希算法
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
        
    def security_access_handler(self, sub_function, data=None):
        """处理0x27安全访问请求
        
        Args:
            sub_function: 子功能代码，比如'01'(请求种子), '02'(发送密钥)
            data: 客户端发来的数据，通常是密钥
            
        Returns:
            str: 响应字符串
        """
        current_time = time.time()
        
        # 检查尝试次数超限
        if self.security_access['attempts'] >= 3 and (self.security_access['timeout'] is None or current_time < self.security_access['timeout']):
            return '7F 27 36\r\r>'  # 36 = 超过尝试次数
            
        if self.security_access['timeout'] and current_time < self.security_access['timeout']:
            return '7F 27 37\r\r>'  # 37 = 超时未过期
            
        # 重置超时
        self.security_access['timeout'] = None
        
        # 请求种子子功能 (01, 03, 05, 11...)
        if sub_function in ['01', '03', '05', '11']:
            # 生成新种子
            seed = self._generate_seed(sub_function)
            
            # 保存种子和时间
            self.security_access['seed'] = seed
            self.security_access['level'] = sub_function
            self.security_access['last_seed_time'] = current_time
            
            logger.info(f"生成安全访问种子: {seed} (级别 {sub_function})")
            
            # 返回种子
            return f'67 {sub_function} {seed}\r\r>'
            
        # 发送密钥子功能 (02, 04, 06, 12...)
        elif sub_function in ['02', '04', '06', '12']:
            # 检查是否先请求了种子
            request_level = f"{int(sub_function) - 1:02d}"  # 计算对应的请求级别
            
            if not self.security_access['seed'] or self.security_access['level'] != request_level:
                logger.warning("发送密钥前未请求种子或级别不匹配")
                return '7F 27 24\r\r>'  # 24 = 请求顺序错误
                
            # 检查种子是否过期
            if not self.security_access['last_seed_time'] or \
               (current_time - self.security_access['last_seed_time'] > self.security_access['seed_validity']):
                logger.warning(f"种子已过期: {current_time - self.security_access['last_seed_time']:.2f}秒")
                return '7F 27 24\r\r>'  # 24 = 请求顺序错误 (种子过期)
                
            # 验证密钥
            if not data:
                logger.warning("未提供密钥数据")
                return '7F 27 35\r\r>'  # 35 = 无效密钥
                
            expected_key = self._calculate_key(self.security_access['seed'], request_level)
            client_key = data.strip()
            
            # 记录日志
            logger.info(f"客户端密钥: {client_key}")
            logger.info(f"期望密钥: {expected_key}")
            
            # 比较密钥 (忽略空格)
            if client_key.replace(' ', '') == expected_key.replace(' ', ''):
                # 验证成功
                self.security_access['status'] = True
                self.security_access['attempts'] = 0
                logger.info(f"安全访问成功: 级别 {request_level}")
                return f'67 {sub_function}\r\r>'
            else:
                # 验证失败
                self.security_access['attempts'] += 1
                if self.security_access['attempts'] >= 3:
                    self.security_access['timeout'] = current_time + 10  # 设置10秒超时
                    logger.warning(f"安全访问失败: 尝试次数超限 ({self.security_access['attempts']}次)，锁定10秒")
                else:
                    logger.warning(f"安全访问失败: 无效密钥 (尝试次数: {self.security_access['attempts']})")
                return '7F 27 35\r\r>'  # 35 = 无效密钥
                
        # 不支持的子功能
        else:
            return '7F 27 12\r\r>'  # 12 = 子功能不支持
    
    def load_crypto_keys(self):
        """加载RSA密钥"""
        key_folder = "keys"
        server_key_file = "server_keys.json"
        
        # 检查密钥文件是否存在
        server_key_path = os.path.join(key_folder, server_key_file)
        if not os.path.exists(server_key_path):
            logger.warning(f"密钥文件 {server_key_path} 不存在，将使用模拟密钥")
            return
            
        try:
            # 加载服务器密钥
            with open(server_key_path, 'r') as f:
                server_keys = json.load(f)
                
            # 反序列化密钥
            private_key_pem = server_keys.get('private_key')
            public_key_pem = server_keys.get('public_key')
            
            if private_key_pem and public_key_pem:
                self.asymmetric_keys['private_key'] = CryptoUtils.deserialize_private_key(private_key_pem)
                self.asymmetric_keys['public_key'] = CryptoUtils.deserialize_public_key(public_key_pem)
                logger.info("成功加载RSA密钥")
                
            # 加载已知的客户端公钥
            client_keys_dir = os.path.join(key_folder, "clients")
            logger.info(f"正在检查客户端公钥目录: {client_keys_dir}")
            if os.path.exists(client_keys_dir):
                client_files = os.listdir(client_keys_dir)
                logger.info(f"发现 {len(client_files)} 个客户端密钥文件: {client_files}")
                
                for filename in client_files:
                    if filename.endswith(".json"):
                        client_id = filename.replace(".json", "")
                        try:
                            client_key_path = os.path.join(client_keys_dir, filename)
                            logger.info(f"正在加载客户端密钥文件: {client_key_path}")
                            
                            with open(client_key_path, 'r') as f:
                                client_data = json.load(f)
                                client_public_key_pem = client_data.get('public_key')
                                if client_public_key_pem:
                                    self.asymmetric_keys['client_public_keys'][client_id] = \
                                        CryptoUtils.deserialize_public_key(client_public_key_pem)
                                    logger.info(f"已加载客户端 {client_id} 的公钥")
                                else:
                                    logger.warning(f"客户端 {client_id} 密钥文件中未找到公钥")
                        except Exception as e:
                            logger.error(f"加载客户端 {client_id} 公钥失败: {e}")
            else:
                logger.warning(f"客户端公钥目录不存在: {client_keys_dir}")
                
        except Exception as e:
            logger.error(f"加载RSA密钥失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def get_pid_response(self, pid):
        """根据PID返回当前模拟的数据响应"""
        # 处理0x29认证请求
        if pid.startswith('29'):
            sub_function = pid[2:4] if len(pid) >= 4 else None
            data = pid[4:] if len(pid) > 4 else None
            if sub_function:
                return self.auth_handler(sub_function, data)
                
        # 处理0x27安全访问请求
        elif pid.startswith('27'):
            sub_function = pid[2:4] if len(pid) >= 4 else None
            data = pid[4:] if len(pid) > 4 else None
            if sub_function:
                return self.security_access_handler(sub_function, data)
            
        if pid == '010C':  # 发动机转速
            rpm_value = int(self.engine_rpm * 4)  # 按照公式: RPM = ((A*256)+B)/4
            high_byte = (rpm_value >> 8) & 0xFF
            low_byte = rpm_value & 0xFF
            return f'41 0C {high_byte:02X} {low_byte:02X}\r\r>'
        
        elif pid == '010D':  # 车速
            return f'41 0D {int(self.vehicle_speed):02X}\r\r>'
        
        elif pid == '0105':  # 发动机冷却液温度
            temp_value = int(self.engine_temp) + 40  # 按照公式: Temp(°C) = A - 40
            return f'41 05 {temp_value:02X}\r\r>'
        
        elif pid == '0104':  # 发动机负载
            load_value = int((self.engine_load / 100.0) * 255)  # 按照公式: Load(%) = A * 100 / 255
            return f'41 04 {load_value:02X}\r\r>'
        
        elif pid == '0111':  # 节气门位置
            throttle_value = int((self.throttle_pos / 100.0) * 255)  # 按照公式: Position(%) = A * 100 / 255
            return f'41 11 {throttle_value:02X}\r\r>'
        
        elif pid == '0110':  # MAF空气流量率
            maf_value = int(self.maf_rate * 100)  # 按照公式: MAF(g/s) = ((A*256)+B) / 100
            high_byte = (maf_value >> 8) & 0xFF
            low_byte = maf_value & 0xFF
            return f'41 10 {high_byte:02X} {low_byte:02X}\r\r>'
        
        # 如果不是动态模拟的PID，返回None
        return None


class OBDSimulator:
    def __init__(self, host='localhost', port=35000):
        self.host = host
        self.port = port
        self.socket = None
        self.clients = []
        self.running = False
        self.dynamic_data = DynamicDataSimulator()
        
    def start(self):
        """启动OBD模拟器服务"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 设置端口复用，避免重启时端口被占用
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            logger.info(f"OBD模拟器服务已启动 {self.host}:{self.port}")
            
            self.running = True
            self.accept_thread = threading.Thread(target=self._accept_connections)
            self.accept_thread.daemon = True
            self.accept_thread.start()
            
            # 启动动态数据模拟器
            self.dynamic_data.start()
            
            return True
        except Exception as e:
            logger.error(f"启动OBD模拟器失败: {e}")
            return False
            
    def stop(self):
        """停止OBD模拟器服务"""
        self.running = False
        
        # 断开所有客户端连接
        for client in self.clients[:]:
            try:
                client['socket'].close()
            except:
                pass
        
        # 关闭服务器套接字
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        # 停止动态数据模拟器
        self.dynamic_data.stop()
        
        logger.info("OBD模拟器服务已停止")
    
    def _accept_connections(self):
        """接受客户端连接"""
        while self.running:
            try:
                client_socket, client_address = self.socket.accept()
                logger.info(f"新客户端连接：{client_address}")
                
                client_info = {
                    'socket': client_socket,
                    'address': client_address,
                    'thread': None
                }
                
                # 为每个客户端创建处理线程
                client_info['thread'] = threading.Thread(
                    target=self._handle_client,
                    args=(client_info,)
                )
                client_info['thread'].daemon = True
                client_info['thread'].start()
                
                self.clients.append(client_info)
            except Exception as e:
                if self.running:
                    logger.error(f"接受连接时出错: {e}")
                    time.sleep(1)
    
    def _handle_client(self, client_info):
        """处理客户端请求"""
        client_socket = client_info['socket']
        client_address = client_info['address']
        
        # 客户端设置
        settings = {
            'echo': True,
            'headers': False,
            'spaces': True,
            'linefeed': False
        }
        
        # 设置超时时间，避免读取阻塞
        client_socket.settimeout(120.0)  # 2分钟超时
        
        buffer = ''
        try:
            while self.running:
                try:
                    data = client_socket.recv(1024).decode('ascii', errors='ignore')
                    if not data:
                        # 客户端断开连接
                        break
                    
                    # 将数据添加到缓冲区并处理命令
                    buffer += data
                    buffer, responses, commands = self._process_commands(buffer, settings)
                    
                    # 发送响应
                    for cmd, response in zip(commands, responses):
                        if settings['echo'] and cmd.upper() != 'ATZ':
                            # 回显命令本身（ELM327标准行为）
                            client_socket.sendall((cmd + '\r\r>').encode('ascii'))
                            time.sleep(0.05)
                        client_socket.sendall(response.encode('ascii'))
                        time.sleep(0.05)
                        
                except socket.timeout:
                    # 超时检查，可以用于清理
                    pass
                    
        except Exception as e:
            if self.running:
                logger.error(f"处理客户端 {client_address} 时出错: {e}")
        
        finally:
            # 清理客户端连接
            try:
                client_socket.close()
            except:
                pass
            
            if client_info in self.clients:
                self.clients.remove(client_info)
                
            logger.info(f"客户端断开连接: {client_address}")
    
    def _process_commands(self, buffer, settings):
        """处理客户端命令"""
        responses = []
        commands = []
        
        # 检查换行符，分割命令
        lines = buffer.replace('\r', '\n').split('\n')
        
        # 最后一行可能不完整，保留
        if lines and not lines[-1].endswith('\n'):
            buffer = lines[-1]
            lines = lines[:-1]
        else:
            buffer = ''
        
        # 处理每一个完整命令
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            commands.append(line)
            
            # 处理AT命令
            if line.upper().startswith('AT'):
                at_cmd = line.upper()
                if at_cmd in AT_COMMANDS:
                    # 处理特殊AT命令的设置
                    if at_cmd == 'ATE0':
                        settings['echo'] = False
                    elif at_cmd == 'ATE1':
                        settings['echo'] = True
                    elif at_cmd == 'ATH0':
                        settings['headers'] = False
                    elif at_cmd == 'ATH1':
                        settings['headers'] = True
                    elif at_cmd == 'ATS0':
                        settings['spaces'] = False
                    elif at_cmd == 'ATS1':
                        settings['spaces'] = True
                    elif at_cmd == 'ATL0':
                        settings['linefeed'] = False
                    elif at_cmd == 'ATL1':
                        settings['linefeed'] = True
                        
                    responses.append(AT_COMMANDS[at_cmd])
                else:
                    # 未知AT命令返回OK
                    responses.append('OK\r\r>')
                    
            # 处理OBD命令
            else:
                # 标准化OBD命令（移除空格，转为大写）
                obd_cmd = re.sub(r'\s+', '', line.upper())
                
                # 处理认证请求(0x29)
                if obd_cmd.startswith('29'):
                    logger.debug(f"处理认证请求: {obd_cmd}")
                    sub_function = obd_cmd[2:4] if len(obd_cmd) >= 4 else None
                    data = obd_cmd[4:] if len(obd_cmd) > 4 else None
                    
                    if sub_function:
                        dynamic_response = self.dynamic_data.auth_handler(sub_function, data)
                        if dynamic_response:
                            responses.append(dynamic_response)
                            continue
                
                # 处理安全访问请求(0x27)
                elif obd_cmd.startswith('27'):
                    logger.debug(f"处理安全访问请求: {obd_cmd}")
                    sub_function = obd_cmd[2:4] if len(obd_cmd) >= 4 else None
                    data = obd_cmd[4:] if len(obd_cmd) > 4 else None
                    
                    if sub_function:
                        dynamic_response = self.dynamic_data.security_access_handler(sub_function, data)
                        if dynamic_response:
                            responses.append(dynamic_response)
                            continue
                
                # 先检查是否有动态模拟数据
                dynamic_response = self.dynamic_data.get_pid_response(obd_cmd)
                if dynamic_response:
                    responses.append(dynamic_response)
                    continue
                
                # 如果没有动态数据，检查预设响应
                if obd_cmd in OBD_RESPONSES:
                    responses.append(OBD_RESPONSES[obd_cmd])
                else:
                    # 对于未知命令，返回NO DATA或?
                    if re.match(r'^[0-9A-F]+$', obd_cmd):
                        responses.append('NO DATA\r\r>')
                    else:
                        responses.append('?\r\r>')
        
        logger.debug(f"处理命令: {commands}, 响应: {responses}")
        return buffer, responses, commands


def signal_handler(sig, frame):
    """处理终止信号"""
    logger.info("收到终止信号，正在关闭服务...")
    if simulator:
        simulator.stop()
    sys.exit(0)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='ELM327 OBD-II 模拟器')
    parser.add_argument('-a', '--address', default='localhost',
                      help='服务器监听地址 (默认: localhost)')
    parser.add_argument('-p', '--port', type=int, default=35000,
                      help='服务器监听端口 (默认: 35000)')
    parser.add_argument('-v', '--verbose', action='store_true',
                      help='启用详细日志输出')
    return parser.parse_args()


if __name__ == "__main__":
    # 解析命令行参数
    args = parse_args()
    
    # 设置日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建并启动模拟器
    simulator = OBDSimulator(args.address, args.port)
    if not simulator.start():
        sys.exit(1)
        
    logger.info(f"ELM327 OBD-II 模拟器已启动，监听于 {args.address}:{args.port}")
    logger.info("按 Ctrl+C 停止服务")
    
    # 保持主线程运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None) 