#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OBD-II 0x29认证密钥生成工具
生成并保存用于OBD-II 0x29认证的RSA密钥对
"""

import os
import json
from crypto_utils import CryptoUtils

def generate_and_save_keys(key_folder="keys", key_size=2048, server_key_file="server_keys.json", client_key_file="client_keys.json"):
    """生成并保存服务器和客户端密钥
    
    Args:
        key_folder: 密钥保存路径
        key_size: 密钥长度
        server_key_file: 服务器密钥文件名
        client_key_file: 客户端密钥文件名
    """
    # 确保密钥目录存在
    if not os.path.exists(key_folder):
        os.makedirs(key_folder)
    
    # 生成服务器密钥对
    server_private_key, server_public_key = CryptoUtils.generate_rsa_keypair(key_size)
    
    # 序列化服务器密钥
    server_private_pem = CryptoUtils.serialize_private_key(server_private_key)
    server_public_pem = CryptoUtils.serialize_public_key(server_public_key)
    
    # 保存服务器密钥
    server_keys = {
        "private_key": server_private_pem,
        "public_key": server_public_pem
    }
    
    with open(os.path.join(key_folder, server_key_file), 'w') as f:
        json.dump(server_keys, f, indent=2)
    
    # 生成客户端密钥对
    client_private_key, client_public_key = CryptoUtils.generate_rsa_keypair(key_size)
    
    # 序列化客户端密钥
    client_private_pem = CryptoUtils.serialize_private_key(client_private_key)
    client_public_pem = CryptoUtils.serialize_public_key(client_public_key)
    
    # 保存客户端密钥
    client_keys = {
        "private_key": client_private_pem,
        "public_key": client_public_pem,
        "server_public_key": server_public_pem  # 客户端也需要知道服务器的公钥
    }
    
    with open(os.path.join(key_folder, client_key_file), 'w') as f:
        json.dump(client_keys, f, indent=2)
    
    print(f"RSA密钥对已生成并保存到 {key_folder} 目录")
    print(f"服务器密钥: {os.path.join(key_folder, server_key_file)}")
    print(f"客户端密钥: {os.path.join(key_folder, client_key_file)}")

if __name__ == "__main__":
    generate_and_save_keys() 