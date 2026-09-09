#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加密工具测试脚本
用于验证加密工具模块的功能
"""

from crypto_utils import CryptoUtils
import os
import sys
import json

def test_key_generation():
    """测试RSA密钥生成"""
    print("测试RSA密钥生成...")
    private_key, public_key = CryptoUtils.generate_rsa_keypair(1024)  # 使用更小的密钥加速测试
    
    # 序列化密钥
    private_pem = CryptoUtils.serialize_private_key(private_key)
    public_pem = CryptoUtils.serialize_public_key(public_key)
    
    print("私钥类型:", type(private_key))
    print("公钥类型:", type(public_key))
    print("私钥PEM格式前100字符:", private_pem[:100], "...")
    print("公钥PEM格式前100字符:", public_pem[:100], "...")
    
    print("RSA密钥生成测试完成\n")
    return private_key, public_key, private_pem, public_pem

def test_sign_verify(private_key, public_key):
    """测试签名和验证"""
    print("测试签名和验证...")
    
    # 生成测试数据
    challenge = CryptoUtils.generate_hex_challenge(8)
    challenge_bytes = CryptoUtils.hex_challenge_to_bytes(challenge)
    
    print("挑战:", challenge)
    print("挑战字节:", challenge_bytes)
    
    # 签名
    signature = CryptoUtils.sign_data(private_key, challenge_bytes)
    print("签名类型:", type(signature))
    print("签名长度:", len(signature))
    print("签名前50字符:", signature[:50], "...")
    
    # 验证签名
    is_valid = CryptoUtils.verify_signature(public_key, challenge_bytes, signature)
    print("签名验证结果:", is_valid)
    
    # 测试无效签名
    invalid_challenge = CryptoUtils.generate_hex_challenge(8)
    invalid_challenge_bytes = CryptoUtils.hex_challenge_to_bytes(invalid_challenge)
    
    is_invalid = CryptoUtils.verify_signature(public_key, invalid_challenge_bytes, signature)
    print("无效签名验证结果:", is_invalid)
    
    print("签名和验证测试完成\n")
    return challenge, signature

def test_session_key_generation():
    """测试会话密钥生成"""
    print("测试会话密钥生成...")
    
    # 生成服务器和客户端挑战
    server_challenge = CryptoUtils.generate_hex_challenge(8)
    client_challenge = CryptoUtils.generate_hex_challenge(8)
    
    print("服务器挑战:", server_challenge)
    print("客户端挑战:", client_challenge)
    
    # 生成会话密钥
    session_key = CryptoUtils.generate_session_key(server_challenge, client_challenge)
    print("会话密钥:", session_key)
    
    # 测试对称性
    session_key2 = CryptoUtils.generate_session_key(client_challenge, server_challenge)
    print("会话密钥(交换顺序):", session_key2)
    print("密钥是否对称:", session_key != session_key2)
    
    print("会话密钥生成测试完成\n")

def test_signature_conversion(signature):
    """测试签名转换格式"""
    print("测试签名转换格式...")
    
    # 将Base64签名转换为哈希值
    import hashlib
    signature_hash = hashlib.sha256(signature.encode()).hexdigest()[:16]
    
    print("签名哈希值:", signature_hash)
    
    # 将哈希值转换为OBD格式
    signature_hex = ' '.join([signature_hash[i:i+2] for i in range(0, len(signature_hash), 2)])
    print("OBD格式签名:", signature_hex)
    
    # 使用前缀
    signature_with_prefix = f"SIG_{signature_hash}"
    print("带前缀的签名:", signature_with_prefix)
    
    print("签名转换格式测试完成\n")

def test_load_keys():
    """测试加载密钥"""
    print("测试加载密钥...")
    
    key_folder = "keys"
    server_key_file = "server_keys.json"
    client_key_file = "client_keys.json"
    
    # 检查密钥文件是否存在
    server_key_path = os.path.join(key_folder, server_key_file)
    client_key_path = os.path.join(key_folder, client_key_file)
    
    if not os.path.exists(server_key_path):
        print(f"服务器密钥文件 {server_key_path} 不存在")
        return
    
    if not os.path.exists(client_key_path):
        print(f"客户端密钥文件 {client_key_path} 不存在")
        return
    
    try:
        # 加载服务器密钥
        with open(server_key_path, 'r') as f:
            server_keys = json.load(f)
            
        # 加载客户端密钥
        with open(client_key_path, 'r') as f:
            client_keys = json.load(f)
            
        # 反序列化密钥
        server_private_key = CryptoUtils.deserialize_private_key(server_keys['private_key'])
        server_public_key = CryptoUtils.deserialize_public_key(server_keys['public_key'])
        
        client_private_key = CryptoUtils.deserialize_private_key(client_keys['private_key'])
        client_public_key = CryptoUtils.deserialize_public_key(client_keys['public_key'])
        
        print("服务器私钥类型:", type(server_private_key))
        print("服务器公钥类型:", type(server_public_key))
        print("客户端私钥类型:", type(client_private_key))
        print("客户端公钥类型:", type(client_public_key))
        
        # 测试服务器对客户端挑战的签名
        challenge = CryptoUtils.generate_hex_challenge(8)
        challenge_bytes = CryptoUtils.hex_challenge_to_bytes(challenge)
        
        # 服务器签名
        server_signature = CryptoUtils.sign_data(server_private_key, challenge_bytes)
        
        # 使用客户端公钥验证服务器签名
        is_valid = CryptoUtils.verify_signature(server_public_key, challenge_bytes, server_signature)
        print("服务器签名验证结果:", is_valid)
        
        print("密钥加载和验证测试完成")
    except Exception as e:
        print(f"加载密钥失败: {e}")

if __name__ == "__main__":
    # 测试RSA密钥生成
    private_key, public_key, private_pem, public_pem = test_key_generation()
    
    # 测试签名和验证
    challenge, signature = test_sign_verify(private_key, public_key)
    
    # 测试会话密钥生成
    test_session_key_generation()
    
    # 测试签名转换格式
    test_signature_conversion(signature)
    
    # 测试加载密钥
    test_load_keys() 