import math
import random
import time
import serial
import socket
import threading
import json

class OBD2Simulator:
    """符合现实物理逻辑的OBD2模拟器 - 支持USB串口和WiFi TCP"""

    def __init__(self):
        # ===== 车辆基础参数 =====
        self.tire_circumference = 2.0  # 轮胎周长 米
        self.final_drive_ratio = 4.1   # 主减速比

        self.gear_ratios = {
            0: 0, 1: 3.454, 2: 1.944, 3: 1.370,
            4: 1.032, 5: 0.849, 6: 0.738,
        }

        # ===== 当前状态 =====
        self.gear = 0
        self.rpm = 800
        self.speed = 0.0
        self.throttle = 0.0
        self.coolant_temp = 85
        self.voltage = 14.2

        # ===== 模拟参数 =====
        self.idle_rpm_base = 750
        self.redline = 6500
        self.max_rpm = 7000
        self.rpm_noise = 0
        self.speed_noise = 0
        self.noise_timer = 0

        # ===== 通信控制 =====
        self.running = True
        self.usb_port = None
        self.ser = None
        self.tcp_server = None
        self.tcp_clients = []
        self.udp_sock = None

    def rpm_to_speed(self, rpm, gear):
        if gear == 0 or rpm == 0:
            return 0.0
        ratio = self.gear_ratios.get(gear, 1.0)
        if ratio == 0:
            return 0.0
        speed = (rpm * self.tire_circumference * 60) / (ratio * self.final_drive_ratio * 1000)
        return round(speed, 1)

    def speed_to_rpm(self, speed, gear):
        if gear == 0 or speed == 0:
            return self.idle_rpm_base
        ratio = self.gear_ratios.get(gear, 1.0)
        if ratio == 0:
            return self.idle_rpm_base
        rpm = (speed * ratio * self.final_drive_ratio * 1000) / (self.tire_circumference * 60)
        return max(int(rpm), self.idle_rpm_base)

    def set_gear(self, gear):
        if gear not in self.gear_ratios:
            return
        old_gear = self.gear
        self.gear = gear
        if gear == 0:
            self.rpm = self.idle_rpm_base + random.randint(-20, 20)
        elif old_gear == 0:
            pass
        else:
            self.rpm = self.speed_to_rpm(self.speed, gear)

    def set_rpm(self, rpm):
        self.rpm = max(0, min(rpm, self.max_rpm))
        if self.gear > 0:
            self.speed = self.rpm_to_speed(self.rpm, self.gear)

    def set_speed(self, speed):
        self.speed = max(0.0, speed)
        if self.gear > 0:
            self.rpm = self.speed_to_rpm(self.speed, self.gear)

    def set_throttle(self, throttle):
        self.throttle = max(0, min(throttle, 100))

    def update(self, dt=0.1):
        # 怠速浮动
        if self.gear == 0 or self.speed < 1.0:
            target_idle = self.idle_rpm_base + random.uniform(-30, 30)
            self.rpm += (target_idle - self.rpm) * 0.3 * dt

        # 油门响应
        if self.throttle > 0 and self.gear > 0:
            rpm_gain = self.throttle * 15 * dt
            if self.rpm > 4000:
                rpm_gain *= (1 - (self.rpm - 4000) / 6000)
            self.rpm = min(self.rpm + rpm_gain, self.redline)
            self.speed = self.rpm_to_speed(self.rpm, self.gear)

        # 松油门减速
        if self.throttle == 0 and self.speed > 0:
            decel = 5.0 * dt
            if self.gear > 0:
                decel *= (1 + (6 - self.gear) * 0.15)
            self.speed = max(0, self.speed - decel)
            self.rpm = self.speed_to_rpm(self.speed, self.gear)

        # 随机浮动
        self.noise_timer += dt
        if self.noise_timer > 0.05:
            self.noise_timer = 0
            self.rpm_noise = random.randint(-15, 15)
            self.speed_noise = random.uniform(-0.3, 0.3)

        # 水温/电压
        if self.rpm > 2000:
            self.coolant_temp = min(105, self.coolant_temp + 0.02 * dt)
        else:
            self.coolant_temp = max(80, self.coolant_temp - 0.01 * dt)
        base_voltage = 14.2 if self.rpm > 1000 else 12.6
        self.voltage = base_voltage + random.uniform(-0.1, 0.1)

    def get_display_rpm(self):
        return int(self.rpm + self.rpm_noise)

    def get_display_speed(self):
        return round(max(0, self.speed + self.speed_noise), 1)

    # ==================== ELM327 协议解析 ====================
    def parse_elm_command(self, cmd):
        """解析ELM327 AT命令和OBD请求"""
        cmd = cmd.strip().upper()

        # AT命令
        if cmd.startswith('AT'):
            return self.handle_at_command(cmd)

        # OBD请求 (如 010C)
        if len(cmd) >= 4:
            mode = cmd[:2]
            pid = cmd[2:4]
            if mode == '01':
                return self.handle_mode_01(pid)
            elif mode == '03':
                return self.handle_mode_03()
            elif mode == '09' and pid == '02':
                return self.handle_mode_09_02()

        return '?'

    def handle_at_command(self, cmd):
        """处理AT命令"""
        if cmd == 'ATZ':
            return 'ELM327 v1.5\r>'
        elif cmd == 'ATI':
            return 'ELM327 v1.5\r>'
        elif cmd == 'AT@1':
            return 'OBDII to RS232 Interpreter\r>'
        elif cmd == 'AT@2':
            return '1234567890ABCDEF\r>'
        elif cmd == 'ATSP0':
            return 'OK\r>'
        elif cmd == 'ATSP6':
            return 'OK\r>'
        elif cmd == 'ATDP':
            return 'AUTO, ISO 15765-4 (CAN 11/500)\r>'
        elif cmd == 'ATRV':
            return f'{self.voltage:.1f}V\r>'
        elif cmd == 'ATH1':
            return 'OK\r>'
        elif cmd == 'ATH0':
            return 'OK\r>'
        elif cmd == 'ATE0':
            return 'OK\r>'
        elif cmd == 'ATE1':
            return 'OK\r>'
        elif cmd == 'ATL0':
            return 'OK\r>'
        elif cmd == 'ATS0':
            return 'OK\r>'
        elif cmd == 'ATST0A':
            return 'OK\r>'
        return 'OK\r>'

    def handle_mode_01(self, pid):
        """处理Mode 01实时数据请求"""
        rpm = self.get_display_rpm()
        speed = int(self.get_display_speed())
        temp = int(self.coolant_temp)

        responses = {
            '00': '41 00 BE 3E B8 11',   # 支持的PID列表
            '01': '41 01 00',             # 故障灯状态
            '04': f'41 04 {int(self.throttle * 255 / 100):02X}',  # 发动机负荷
            '05': f'41 05 {temp + 40:02X}',  # 冷却液温度
            '06': '41 06 80',             # 短期燃油修正
            '07': '41 07 80',             # 长期燃油修正
            '0B': f'41 0B {random.randint(20, 40):02X}',  # 进气压力
            '0C': f'41 0C {(rpm * 4) >> 8:02X} {(rpm * 4) & 0xFF:02X}',  # 转速
            '0D': f'41 0D {speed:02X}',   # 车速
            '0F': f'41 0F {temp + 40:02X}',  # 进气温度
            '10': f'41 10 {random.randint(5, 15):02X}',  # 空气流量
            '11': f'41 11 {int(self.throttle * 255 / 100):02X}',  # 节气门位置
            '1F': '41 1F 00',             # 运行时间
            '2F': f'41 2F {random.randint(80, 100):02X}',  # 燃油液位
            '33': f'41 33 {(int(self.voltage * 1000)) >> 8:02X} {(int(self.voltage * 1000)) & 0xFF:02X}',  # 电压
            '42': f'41 42 {(int(self.voltage * 1000)) >> 8:02X} {(int(self.voltage * 1000)) & 0xFF:02X}',  # 控制模块电压
        }
        return responses.get(pid, 'NO DATA\r>')

    def handle_mode_03(self):
        return '43 00 00 00 00 00 00'  # 无故障码

    def handle_mode_09_02(self):
        return '49 02 01 31 32 33 34 35 36 37 38 39 41 42 43 44 45 46'  # VIN码

    # ==================== USB 串口通信 ====================
    def start_usb(self, port='COM3', baudrate=38400):
        """启动USB串口服务"""
        try:
            self.ser = serial.Serial(port, baudrate, timeout=1)
            print(f"✅ USB串口已启动: {port} @ {baudrate}")
            usb_thread = threading.Thread(target=self._usb_loop, daemon=True)
            usb_thread.start()
            return True
        except Exception as e:
            print(f"⚠️ USB串口启动失败: {e}")
            print(f"   提示: 如果没有USB转串口设备，可以跳过USB，只用WiFi")
            return False

    def _usb_loop(self):
        """USB串口通信循环"""
        buffer = ""
        while self.running and self.ser and self.ser.is_open:
            try:
                data = self.ser.read(1)
                if data:
                    char = data.decode('utf-8', errors='ignore')
                    if char == '\r' or char == '\n':
                        if buffer.strip():
                            response = self.parse_elm_command(buffer.strip())
                            self.ser.write((response + '\r>').encode())
                        buffer = ""
                    else:
                        buffer += char
            except Exception as e:
                print(f"USB读取错误: {e}")
                break

    # ==================== WiFi TCP 通信 ====================
    def start_wifi(self, host='0.0.0.0', port=35000):
        """启动WiFi TCP服务"""
        try:
            self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_server.bind((host, port))
            self.tcp_server.listen(5)
            self.tcp_server.settimeout(1.0)
            print(f"✅ WiFi TCP服务已启动: {host}:{port}")
            wifi_thread = threading.Thread(target=self._wifi_accept_loop, daemon=True)
            wifi_thread.start()
            return True
        except Exception as e:
            print(f"❌ WiFi TCP启动失败: {e}")
            return False

    def _wifi_accept_loop(self):
        """接受WiFi客户端连接"""
        while self.running:
            try:
                client, addr = self.tcp_server.accept()
                print(f"📱 WiFi客户端连接: {addr}")
                self.tcp_clients.append(client)
                client_thread = threading.Thread(
                    target=self._wifi_client_loop, args=(client, addr), daemon=True
                )
                client_thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"WiFi接受错误: {e}")
                break

    def _wifi_client_loop(self, client, addr):
        """处理单个WiFi客户端"""
        buffer = ""
        while self.running:
            try:
                data = client.recv(1024)
                if not data:
                    break
                text = data.decode('utf-8', errors='ignore')
                for char in text:
                    if char == '\r' or char == '\n':
                        if buffer.strip():
                            response = self.parse_elm_command(buffer.strip())
                            client.send((response + '\r>').encode())
                        buffer = ""
                    else:
                        buffer += char
            except Exception:
                break
        print(f"📱 WiFi客户端断开: {addr}")
        if client in self.tcp_clients:
            self.tcp_clients.remove(client)
        client.close()

    # ==================== 广播模式（UDP）====================
    def start_broadcast(self, host='0.0.0.0', port=35001):
        """启动UDP广播服务，实时推送数据"""
        try:
            self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # 【修复】Windows需要设置SO_BROADCAST权限
            self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.udp_sock.bind((host, port))
            print(f"📡 UDP广播已启动: {host}:{port}")
            broadcast_thread = threading.Thread(
                target=self._broadcast_loop, daemon=True
            )
            broadcast_thread.start()
            return True
        except Exception as e:
            print(f"❌ UDP广播启动失败: {e}")
            return False

    def _broadcast_loop(self):
        """实时广播车辆数据"""
        while self.running:
            try:
                data = json.dumps({
                    'rpm': self.get_display_rpm(),
                    'speed': self.get_display_speed(),
                    'gear': self.gear,
                    'throttle': round(self.throttle, 1),
                    'temp': round(self.coolant_temp, 1),
                    'voltage': round(self.voltage, 2),
                })
                # 广播到局域网
                self.udp_sock.sendto(
                    data.encode(), ('<broadcast>', 35001)
                )
            except Exception as e:
                pass
            time.sleep(0.1)  # 10Hz

    def stop(self):
        self.running = False
        if self.ser:
            self.ser.close()
        if self.tcp_server:
            self.tcp_server.close()
        for client in self.tcp_clients:
            client.close()
        if self.udp_sock:
            self.udp_sock.close()


# ==================== 使用示例 ====================
def demo():
    sim = OBD2Simulator()

    print("=" * 50)
    print("🚗 OBD2 模拟器 - USB + WiFi 双模式")
    print("=" * 50)

    # 启动USB串口（如果没有设备会跳过）
    sim.start_usb(port='COM3', baudrate=38400)

    # 启动WiFi TCP（手机App/电脑客户端连接）
    sim.start_wifi(host='0.0.0.0', port=35000)

    # 启动UDP广播（实时数据推送）
    sim.start_broadcast(host='0.0.0.0', port=35001)

    print("\n📋 连接方式:")
    print("  USB: 串口 COM3 @ 38400 (如无设备可跳过)")
    print("  WiFi TCP: 连接 127.0.0.1:35000")
    print("  UDP广播: 监听 35001 端口")
    print("\n🎮 控制: W/S油门, A/D换挡, R设转速, Q退出\n")

    throttle = 0.0
    last_time = time.time()

    try:
        while sim.running:
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time

            # 键盘控制
            import msvcrt
            if msvcrt.kbhit():
                key = msvcrt.getch().decode().lower()
                if key == 'w':
                    throttle = min(100, throttle + 5)
                    sim.set_throttle(throttle)
                    print(f"油门+ → {throttle:.1f}%")
                elif key == 's':
                    throttle = max(0, throttle - 5)
                    sim.set_throttle(throttle)
                    print(f"油门- → {throttle:.1f}%")
                elif key == 'a':
                    sim.set_gear(max(0, sim.gear - 1))
                    print(f"降档 → {sim.gear if sim.gear > 0 else 'N'}档")
                elif key == 'd':
                    sim.set_gear(min(6, sim.gear + 1))
                    print(f"升档 → {sim.gear if sim.gear > 0 else 'N'}档")
                elif key == 'r':
                    try:
                        rpm = int(input("输入目标转速: "))
                        sim.set_rpm(rpm)
                    except:
                        pass
                elif key == 'q':
                    break

            sim.update(dt)

            # 打印仪表盘
            rpm = sim.get_display_rpm()
            speed = sim.get_display_speed()
            gear_display = 'N' if sim.gear == 0 else str(sim.gear)
            print(f"\r[{gear_display}] {rpm:5d}RPM | {speed:6.1f}km/h | 油门{throttle:5.1f}% | {sim.coolant_temp:5.1f}℃", end='', flush=True)

            time.sleep(0.1)
    except KeyboardInterrupt:
        pass
    finally:
        sim.stop()
        print("\n\n模拟器已停止")


if __name__ == '__main__':
    demo()