#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###########################################################################
# OBD 模拟器测试客户端
# 用于测试 OBD 模拟器的客户端脚本
###########################################################################

import socket
import time
import sys
import argparse
import logging

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("OBD客户端")

class OBDClient:
    def __init__(self, host='localhost', port=35000, timeout=10):
        """初始化OBD客户端"""
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
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.connected = False
        logger.info("已断开连接")
    
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
    
    def check_connection(self):
        """检查与汽车ECU的连接"""
        logger.info("检查与汽车ECU的连接...")
        
        # 请求支持的PID
        response = self.send_command("0100")
        if not response or "41 00" not in response:
            logger.error("无法获取支持的PID列表")
            return False
            
        logger.info("与汽车ECU连接正常")
        return True
    
    def monitor_data(self, interval=1.0, duration=None):
        """监控车辆数据"""
        logger.info("开始监控车辆数据...")
        
        start_time = time.time()
        counter = 0
        
        try:
            while duration is None or time.time() - start_time < duration:
                counter += 1
                logger.info(f"--- 数据监控 #{counter} ---")
                
                # 发动机转速
                response = self.send_command("010C")
                if response and "41 0C" in response:
                    parts = response.strip().split()
                    if len(parts) >= 4:
                        try:
                            a = int(parts[2], 16)
                            b = int(parts[3], 16)
                            rpm = ((a * 256) + b) / 4
                            logger.info(f"发动机转速: {rpm:.1f} RPM")
                        except Exception as e:
                            logger.error(f"解析发动机转速失败: {e}")
                
                # 车速
                response = self.send_command("010D")
                if response and "41 0D" in response:
                    parts = response.strip().split()
                    if len(parts) >= 3:
                        try:
                            speed = int(parts[2], 16)
                            logger.info(f"车速: {speed} km/h")
                        except Exception as e:
                            logger.error(f"解析车速失败: {e}")
                
                # 冷却液温度
                response = self.send_command("0105")
                if response and "41 05" in response:
                    parts = response.strip().split()
                    if len(parts) >= 3:
                        try:
                            temp = int(parts[2], 16) - 40
                            logger.info(f"冷却液温度: {temp} °C")
                        except Exception as e:
                            logger.error(f"解析冷却液温度失败: {e}")
                
                # 节气门位置
                response = self.send_command("0111")
                if response and "41 11" in response:
                    parts = response.strip().split()
                    if len(parts) >= 3:
                        try:
                            pos = int(parts[2], 16) * 100 / 255
                            logger.info(f"节气门位置: {pos:.1f} %")
                        except Exception as e:
                            logger.error(f"解析节气门位置失败: {e}")
                
                # 发动机负载
                response = self.send_command("0104")
                if response and "41 04" in response:
                    parts = response.strip().split()
                    if len(parts) >= 3:
                        try:
                            load = int(parts[2], 16) * 100 / 255
                            logger.info(f"发动机负载: {load:.1f} %")
                        except Exception as e:
                            logger.error(f"解析发动机负载失败: {e}")
                            
                logger.info("-" * 30)
                
                # 等待下一次轮询
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("用户中断监控")
        
        logger.info("停止监控车辆数据")
    
    def run_tests(self):
        """运行全套测试"""
        logger.info("开始运行OBD测试...")
        
        # 发送AT指令测试
        tests = [
            ("ATZ", "ELM327"), 
            ("ATI", "ELM327"),
            ("ATRV", "V"),
            ("AT@1", "OBD")
        ]
        
        for cmd, expected in tests:
            response = self.send_command(cmd)
            if response and expected in response:
                logger.info(f"命令 {cmd} 测试通过")
            else:
                logger.warning(f"命令 {cmd} 测试失败, 响应: {response}")
        
        # 测试OBD模式01命令
        obd_tests = [
            "0100", "0101", "0104", "0105", "010C", "010D", "0111"
        ]
        
        for cmd in obd_tests:
            response = self.send_command(cmd)
            pid_response = "41 " + cmd[2:]
            if response and pid_response in response:
                logger.info(f"OBD命令 {cmd} 测试通过")
            else:
                logger.warning(f"OBD命令 {cmd} 测试失败, 响应: {response}")
        
        logger.info("OBD测试完成")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='OBD模拟器测试客户端')
    parser.add_argument('-a', '--address', default='localhost',
                      help='服务器地址 (默认: localhost)')
    parser.add_argument('-p', '--port', type=int, default=35000,
                      help='服务器端口 (默认: 35000)')
    parser.add_argument('-t', '--timeout', type=float, default=10,
                      help='连接超时时间(秒) (默认: 10)')
    parser.add_argument('-m', '--monitor', action='store_true',
                      help='监控模式')
    parser.add_argument('-i', '--interval', type=float, default=1.0,
                      help='监控时间间隔(秒) (默认: 1.0)')
    parser.add_argument('-d', '--duration', type=float, default=None,
                      help='监控持续时间(秒) (默认: 无限)')
    parser.add_argument('-v', '--verbose', action='store_true',
                      help='启用详细日志输出')
    return parser.parse_args()


if __name__ == "__main__":
    # 解析命令行参数
    args = parse_args()
    
    # 设置日志级别
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # 创建OBD客户端
    client = OBDClient(args.address, args.port, args.timeout)
    
    try:
        # 连接到OBD模拟器
        if not client.connect():
            sys.exit(1)
        
        # 初始化ELM327
        if not client.initialize():
            logger.error("初始化失败，退出程序")
            sys.exit(1)
        
        # 检查与汽车ECU连接
        if not client.check_connection():
            logger.error("无法连接到汽车ECU，退出程序")
            sys.exit(1)
        
        # 运行测试或监控模式
        if args.monitor:
            client.monitor_data(args.interval, args.duration)
        else:
            client.run_tests()
            
    except KeyboardInterrupt:
        logger.info("接收到用户中断，程序退出")
    
    finally:
        # 断开连接
        if client:
            client.disconnect() 