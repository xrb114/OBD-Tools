#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密工具模块
用于OBD-II 0x29认证服务的密钥生成、签名和验证
"""

import os
import base64
import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature

class CryptoUtils:
    @staticmethod
    def generate_rsa_keypair(key_size=2048):
        """生成RSA密钥对
        
        Args:
            key_size: 密钥长度，默认2048位
            
        Returns:
            tuple: (私钥对象, 公钥对象)
        """
        # 生成私钥
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size
        )
        
        # 从私钥中获取公钥
        public_key = private_key.public_key()
        
        return private_key, public_key
    
    @staticmethod
    def serialize_private_key(private_key, password=None):
        """将私钥序列化为PEM格式
        
        Args:
            private_key: 私钥对象
            password: 密码(可选)，用于加密私钥
            
        Returns:
            str: PEM格式的私钥
        """
        # 确定加密算法
        encryption_algorithm = serialization.NoEncryption()
        if password:
            encryption_algorithm = serialization.BestAvailableEncryption(password.encode())
            
        # 序列化私钥
        pem_private = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption_algorithm
        )
        
        return pem_private.decode('utf-8')
    
    @staticmethod
    def serialize_public_key(public_key):
        """将公钥序列化为PEM格式
        
        Args:
            public_key: 公钥对象
            
        Returns:
            str: PEM格式的公钥
        """
        # 序列化公钥
        pem_public = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return pem_public.decode('utf-8')
    
    @staticmethod
    def deserialize_private_key(pem_private, password=None):
        """从PEM格式加载私钥
        
        Args:
            pem_private: PEM格式的私钥
            password: 密码(可选)，如果私钥已加密
            
        Returns:
            object: 私钥对象
        """
        # 处理可能的密码
        pwd = None
        if password:
            pwd = password.encode()
            
        # 加载私钥
        private_key = serialization.load_pem_private_key(
            pem_private.encode(),
            password=pwd
        )
        
        return private_key
    
    @staticmethod
    def deserialize_public_key(pem_public):
        """从PEM格式加载公钥
        
        Args:
            pem_public: PEM格式的公钥
            
        Returns:
            object: 公钥对象
        """
        # 加载公钥
        public_key = serialization.load_pem_public_key(
            pem_public.encode()
        )
        
        return public_key
    
    @staticmethod
    def sign_data(private_key, data):
        """使用私钥对数据进行签名
        
        Args:
            private_key: 私钥对象
            data: 需要签名的数据，可以是字符串或字节
            
        Returns:
            str: Base64编码的签名
        """
        # 确保数据是字节格式
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        # 进行签名
        signature = private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # 使用Base64编码签名，便于传输
        return base64.b64encode(signature).decode('utf-8')
    
    @staticmethod
    def verify_signature(public_key, data, signature):
        """验证签名
        
        Args:
            public_key: 公钥对象
            data: 被签名的原始数据，可以是字符串或字节
            signature: Base64编码的签名
            
        Returns:
            bool: 签名是否有效
        """
        # 确保数据是字节格式
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        # 解码签名
        try:
            sig_bytes = base64.b64decode(signature)
            
            # 验证签名
            public_key.verify(
                sig_bytes,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return True
        except (InvalidSignature, ValueError, TypeError):
            return False
    
    @staticmethod
    def generate_hex_challenge(length=16):
        """生成随机的十六进制挑战值
        
        Args:
            length: 字节长度，默认16字节(128位)
            
        Returns:
            str: 十六进制格式的挑战值(以空格分隔)
        """
        # 生成随机字节
        random_bytes = os.urandom(length)
        
        # 转为十六进制格式，以空格分隔每个字节
        hex_values = [f"{b:02X}" for b in random_bytes]
        return ' '.join(hex_values)
    
    @staticmethod
    def hex_challenge_to_bytes(hex_challenge):
        """将空格分隔的十六进制挑战值转换为字节
        
        Args:
            hex_challenge: 十六进制格式的挑战值(以空格分隔)
            
        Returns:
            bytes: 字节格式的挑战值
        """
        # 移除空格并解析十六进制
        hex_str = hex_challenge.replace(' ', '')
        return bytes.fromhex(hex_str)
    
    @staticmethod
    def generate_session_key(server_random, client_random):
        """从服务器和客户端随机数生成会话密钥
        
        Args:
            server_random: 服务器随机数(挑战)
            client_random: 客户端随机数(挑战)
            
        Returns:
            str: 会话密钥的十六进制表示
        """
        # 确保输入是字节
        if isinstance(server_random, str):
            server_random = CryptoUtils.hex_challenge_to_bytes(server_random)
        if isinstance(client_random, str):
            client_random = CryptoUtils.hex_challenge_to_bytes(client_random)
            
        # 将两个随机数连接起来并生成哈希
        combined = server_random + client_random
        session_key = hashlib.sha256(combined).hexdigest()
        
        return session_key


# 示例用法
if __name__ == "__main__":
    # 生成密钥对
    private_key, public_key = CryptoUtils.generate_rsa_keypair()
    
    # 序列化密钥
    pem_private = CryptoUtils.serialize_private_key(private_key)
    pem_public = CryptoUtils.serialize_public_key(public_key)
    
    print("私钥:")
    print(pem_private)
    print("\n公钥:")
    print(pem_public)
    
    # 生成挑战
    challenge = CryptoUtils.generate_hex_challenge()
    print(f"\n挑战: {challenge}")
    
    # 签名
    signature = CryptoUtils.sign_data(private_key, CryptoUtils.hex_challenge_to_bytes(challenge))
    print(f"\n签名: {signature}")
    
    # 验证签名
    is_valid = CryptoUtils.verify_signature(
        public_key, 
        CryptoUtils.hex_challenge_to_bytes(challenge),
        signature
    )
    
    print(f"\n签名有效: {is_valid}")
    
    # 生成会话密钥
    server_challenge = CryptoUtils.generate_hex_challenge()
    client_challenge = CryptoUtils.generate_hex_challenge()
    
    session_key = CryptoUtils.generate_session_key(server_challenge, client_challenge)
    print(f"\n服务器挑战: {server_challenge}")
    print(f"客户端挑战: {client_challenge}")
    print(f"会话密钥: {session_key}") 