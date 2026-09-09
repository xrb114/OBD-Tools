import socket
import serial
import time
import csv
import os
import threading
from datetime import datetime


# ============================================================
# 配置
# ============================================================

DEFAULT_TCP_HOST = "127.0.0.1"
DEFAULT_TCP_PORT = 8800

DEFAULT_SERIAL_PORT = "COM3"
DEFAULT_SERIAL_BAUD = 38400

LOG_DIR = "logs"


# ============================================================
# TCP Transport
# ============================================================

class TCPTransport:

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None

    def connect(self):
        print(f"[+] TCP 连接 {self.host}:{self.port}")

        self.sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        self.sock.settimeout(3)
        self.sock.connect((self.host, self.port))

        print("[+] TCP 连接成功")

    def send(self, command):

        command = command.strip()

        # 发送 OBD 命令
        self.sock.sendall(
            (command + "\r").encode("ascii")
        )

        data = b""

        while True:

            try:
                chunk = self.sock.recv(4096)

                if not chunk:
                    break

                data += chunk

                # ELM327 / OBD 模拟器提示符
                if b">" in data:
                    break

            except socket.timeout:
                break

        # 解码
        response = data.decode(
            "ascii",
            errors="replace"
        )

        # 清理 ELM327 返回格式
        response = response.replace("\r", "\n")
        response = response.replace(">", "")
        response = response.strip()

        return response

    def close(self):

        if self.sock:

            try:
                self.sock.close()
            except:
                pass

            self.sock = None


# ============================================================
# Serial Transport
# ============================================================

class SerialTransport:

    def __init__(self, port, baudrate=38400):

        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def connect(self):

        print(
            f"[+] 串口连接 {self.port} "
            f"@ {self.baudrate}"
        )

        self.ser = serial.Serial(
            self.port,
            self.baudrate,
            timeout=3
        )

        print("[+] 串口连接成功")

    def send(self, command):

        command = command.strip()

        print(f"TX >> {command}")

        self.ser.write(
            (command + "\r").encode("ascii")
        )

        data = b""

        start = time.time()

        while time.time() - start < 3:

            chunk = self.ser.read(
                self.ser.in_waiting or 1
            )

            if chunk:

                data += chunk

                if b">" in data:

                    break

        response = data.decode(
            "ascii",
            errors="replace"
        )

        print(f"RX << {repr(response)}")

        return response

    def close(self):

        if self.ser:

            try:
                self.ser.close()
            except:
                pass

            self.ser = None


# ============================================================
# OBD Controller
# ============================================================

class OBDController:

    def __init__(self, transport):

        self.transport = transport
        self.connected = False

    # --------------------------------------------------------
    # 连接
    # --------------------------------------------------------

    def connect(self):

        self.transport.connect()

        self.connected = True

        self.init_elm327()

    # --------------------------------------------------------
    # ELM327 初始化
    # --------------------------------------------------------

    def init_elm327(self):

        print()
        print("=" * 60)
        print("ELM327 初始化")
        print("=" * 60)

        commands = [

            "ATZ",

            "ATE0",

            "ATL0",

            "ATS0",

            "ATH0",

            "ATSP0",

        ]

        for command in commands:

            self.transport.send(command)

            time.sleep(0.3)

    # --------------------------------------------------------
    # 发送 OBD
    # --------------------------------------------------------

    def send(self, command):

        return self.transport.send(command)

    # --------------------------------------------------------
    # 读故障码
    # --------------------------------------------------------

    def read_dtcs(self):

        print()
        print("=" * 60)
        print("故障码")
        print("=" * 60)

        response = self.send("03")

        print()

        dtcs = self.parse_dtcs(response)

        if not dtcs:

            print("没有检测到故障码")

            return []

        print(f"发现 {len(dtcs)} 个故障码")

        for dtc in dtcs:

            print(
                f"  {dtc['code']} "
                f"{dtc['description']}"
            )

        return dtcs

    # --------------------------------------------------------
    # 清除故障码
    # --------------------------------------------------------

    def clear_dtcs(self):

        print()
        print("=" * 60)
        print("清除故障码")
        print("=" * 60)

        response = self.send("04")

        print()

        if "44" in response:

            print("[+] 故障码清除成功")

        else:

            print(
                f"[!] 清除失败: {response}"
            )

    # --------------------------------------------------------
    # DTC 解析
    # --------------------------------------------------------

    def parse_dtcs(self, response):

        response = response.upper()

        if "43 00" in response:

            return []

        # 去掉提示符
        response = response.replace(
            "\r",
            " "
        )

        response = response.replace(
            ">",
            " "
        )

        parts = response.split()

        try:

            index = parts.index("43")

        except ValueError:

            return []

        data = parts[index + 1:]

        dtcs = []

        # 每两个字节一个 DTC

        for i in range(
                0,
                len(data) - 1,
                2
        ):

            try:

                b1 = int(data[i], 16)
                b2 = int(data[i + 1], 16)

            except ValueError:

                continue

            if b1 == 0 and b2 == 0:

                continue

            dtc = self.decode_dtc(
                b1,
                b2
            )

            if dtc:

                dtcs.append(dtc)

        return dtcs

    # --------------------------------------------------------
    # DTC 解码
    # --------------------------------------------------------

    def decode_dtc(self, b1, b2):

        letters = [
            "P",
            "C",
            "B",
            "U"
        ]

        letter = letters[
            (b1 >> 6) & 0x03
            ]

        digit1 = (
                (b1 >> 4) & 0x03
        )

        digit2 = (
                b1 & 0x0F
        )

        digit3 = (
                (b2 >> 4) & 0x0F
        )

        digit4 = (
                b2 & 0x0F
        )

        code = (
            f"{letter}"
            f"{digit1}"
            f"{digit2:X}"
            f"{digit3:X}"
            f"{digit4:X}"
        )

        descriptions = {

            "P0300":
                "随机/多缸失火",

            "P0301":
                "1缸失火",

            "P0302":
                "2缸失火",

            "P0303":
                "3缸失火",

            "P0304":
                "4缸失火",

            "P0171":
                "系统过稀",

            "P0172":
                "系统过浓",

            "P0420":
                "催化转换器效率低于阈值",

            "P0100":
                "空气流量传感器故障",

            "P0115":
                "发动机冷却液温度传感器故障",

            "P0120":
                "节气门位置传感器故障",

        }

        return {

            "code": code,

            "description":
                descriptions.get(
                    code,
                    "未知故障码"
                )
        }

    # --------------------------------------------------------
    # PID
    # --------------------------------------------------------

    def read_pid(self, pid, name):

        response = self.send(pid)

        value = self.parse_pid(
            pid,
            response
        )

        print(
            f"{name:<15} "
            f"{value}"
        )

        return value

    # --------------------------------------------------------
    # PID 解析
    # --------------------------------------------------------

    def parse_pid(self, pid, response):

        response = response.upper()

        response = response.replace(
            "\r",
            " "
        )

        response = response.replace(
            ">",
            " "
        )

        parts = response.split()

        try:

            index = parts.index(
                pid[:2].replace(
                    "01",
                    "41"
                )
            )

        except ValueError:

            return response.strip()

        # 更简单可靠的方法
        # 直接从响应中寻找 PID

        target = "41 " + pid[2:]

        tokens = response.split()

        target_tokens = target.split()

        for i in range(
                len(tokens) - len(target_tokens) + 1
        ):

            if tokens[
                i:i + len(target_tokens)
            ] == target_tokens:

                data = tokens[
                    i + len(target_tokens):
                ]

                return self.decode_pid(
                    pid,
                    data
                )

        return response.strip()

    # --------------------------------------------------------
    # PID 数值转换
    # --------------------------------------------------------

    def decode_pid(self, pid, data):

        try:

            if pid == "0104":

                a = int(data[0], 16)

                return (
                    f"{a * 100 / 255:.1f} %"
                )

            if pid == "0105":

                a = int(data[0], 16)

                return (
                    f"{a - 40} °C"
                )

            if pid == "0106":

                a = int(data[0], 16)

                return (
                    f"{(a - 128) * 100 / 128:.1f} %"
                )

            if pid == "0107":

                a = int(data[0], 16)

                return (
                    f"{(a - 128) * 100 / 128:.1f} %"
                )

            if pid == "010C":

                a = int(data[0], 16)

                b = int(data[1], 16)

                rpm = (
                        (a * 256 + b) / 4
                )

                return f"{rpm:.0f} RPM"

            if pid == "010D":

                a = int(data[0], 16)

                return f"{a} km/h"

            if pid == "010F":

                a = int(data[0], 16)

                return f"{a - 40} °C"

            if pid == "0110":

                a = int(data[0], 16)

                b = int(data[1], 16)

                maf = (
                        (a * 256 + b) / 100
                )

                return f"{maf:.2f} g/s"

            if pid == "0111":

                a = int(data[0], 16)

                return (
                    f"{a * 100 / 255:.1f} %"
                )

            if pid == "011F":

                a = int(data[0], 16)

                b = int(data[1], 16)

                seconds = (
                        a * 256 + b
                )

                return f"{seconds} s"

            return " ".join(data)

        except Exception:

            return "解析失败"

    # --------------------------------------------------------
    # 一次读取所有数据
    # --------------------------------------------------------

    def read_all_data(self):

        print()
        print("=" * 60)
        print("实时数据")
        print("=" * 60)

        data = {}

        data["load"] = self.read_pid(
            "0104",
            "发动机负载"
        )

        data["coolant"] = self.read_pid(
            "0105",
            "冷却液温度"
        )

        data["stft"] = self.read_pid(
            "0106",
            "短期燃油修正"
        )

        data["ltft"] = self.read_pid(
            "0107",
            "长期燃油修正"
        )

        data["rpm"] = self.read_pid(
            "010C",
            "发动机转速"
        )

        data["speed"] = self.read_pid(
            "010D",
            "车速"
        )

        data["intake"] = self.read_pid(
            "010F",
            "进气温度"
        )

        data["maf"] = self.read_pid(
            "0110",
            "MAF"
        )

        data["throttle"] = self.read_pid(
            "0111",
            "节气门"
        )

        return data

    # --------------------------------------------------------
    # VIN
    # --------------------------------------------------------

    def read_vin(self):

        print()
        print("=" * 60)
        print("VIN")
        print("=" * 60)

        response = self.send(
            "0902"
        )

        print(
            f"VIN RAW: {response}"
        )

        return response

    # --------------------------------------------------------
    # 数据 LOG
    # --------------------------------------------------------

    def start_log(self):

        os.makedirs(
            LOG_DIR,
            exist_ok=True
        )

        filename = os.path.join(
            LOG_DIR,
            "obd_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            + ".csv"
        )

        print()
        print("=" * 60)
        print("开始记录 LOG")
        print("=" * 60)

        print(
            f"文件: {filename}"
        )

        fields = [
            "timestamp",
            "load",
            "coolant",
            "stft",
            "ltft",
            "rpm",
            "speed",
            "intake",
            "maf",
            "throttle"
        ]

        stop_event = threading.Event()

        def logger_thread():

            with open(
                    filename,
                    "w",
                    newline="",
                    encoding="utf-8-sig"
            ) as f:

                writer = csv.DictWriter(
                    f,
                    fieldnames=fields
                )

                writer.writeheader()

                while not stop_event.is_set():

                    timestamp = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                    row = {
                        "timestamp": timestamp
                    }

                    row["load"] = self.read_pid(
                        "0104",
                        "发动机负载"
                    )

                    row["coolant"] = self.read_pid(
                        "0105",
                        "冷却液温度"
                    )

                    row["stft"] = self.read_pid(
                        "0106",
                        "短期燃油修正"
                    )

                    row["ltft"] = self.read_pid(
                        "0107",
                        "长期燃油修正"
                    )

                    row["rpm"] = self.read_pid(
                        "010C",
                        "发动机转速"
                    )

                    row["speed"] = self.read_pid(
                        "010D",
                        "车速"
                    )

                    row["intake"] = self.read_pid(
                        "010F",
                        "进气温度"
                    )

                    row["maf"] = self.read_pid(
                        "0110",
                        "MAF"
                    )

                    row["throttle"] = self.read_pid(
                        "0111",
                        "节气门"
                    )

                    writer.writerow(row)

                    f.flush()

                    time.sleep(1)

        thread = threading.Thread(
            target=logger_thread,
            daemon=True
        )

        thread.start()

        print()
        print(
            "正在记录数据..."
        )

        print(
            "按 Enter 停止 LOG"
        )

        input()

        stop_event.set()

        thread.join(
            timeout=3
        )

        print(
            f"[+] LOG 保存完成:"
            f" {filename}"
        )

    # --------------------------------------------------------
    # 原始命令
    # --------------------------------------------------------

    def raw_mode(self):

        print()
        print("=" * 60)
        print("原始 ELM327 模式")
        print("=" * 60)

        print(
            "输入命令，例如:"
        )

        print(
            "  ATDP"
        )

        print(
            "  ATRV"
        )

        print(
            "  010C"
        )

        print(
            "输入 exit 返回"
        )

        while True:

            try:

                command = input(
                    "\nOBD> "
                ).strip()

            except KeyboardInterrupt:

                break

            if not command:

                continue

            if command.lower() == "exit":

                break

            self.send(command)

    # --------------------------------------------------------
    # 主菜单
    # --------------------------------------------------------

    def menu(self):

        while True:

            print()
            print("=" * 60)
            print("             OBD-II TESTER")
            print("=" * 60)

            print(
                "1. 读取故障码"
            )

            print(
                "2. 清除故障码"
            )

            print(
                "3. 读取数据流"
            )

            print(
                "4. VIN"
            )

            print(
                "5. 开始记录 LOG"
            )

            print(
                "6. 原始 ELM327 命令"
            )

            print(
                "7. 退出"
            )

            print(
                "=" * 60
            )

            choice = input(
                "选择模式: "
            ).strip()

            if choice == "1":

                self.read_dtcs()

            elif choice == "2":

                self.clear_dtcs()

            elif choice == "3":

                self.read_all_data()

            elif choice == "4":

                self.read_vin()

            elif choice == "5":

                self.start_log()

            elif choice == "6":

                self.raw_mode()

            elif choice == "7":

                break

            else:

                print(
                    "[!] 无效选择"
                )


# ============================================================
# 选择连接方式
# ============================================================

def select_connection():

    print()
    print("=" * 60)
    print("              OBD-II TESTER")
    print("=" * 60)

    print(
        "1. USB / 串口 ELM327"
    )

    print(
        "2. Wi-Fi / TCP ELM327"
    )

    print(
        "3. OBD 模拟器"
    )

    print(
        "4. 退出"
    )

    print(
        "=" * 60
    )

    choice = input(
        "选择连接方式: "
    ).strip()

    # --------------------------------------------------------
    # USB
    # --------------------------------------------------------

    if choice == "1":

        port = input(
            f"COM 端口 "
            f"[默认 {DEFAULT_SERIAL_PORT}]: "
        ).strip()

        if not port:

            port = DEFAULT_SERIAL_PORT

        baud = input(
            f"波特率 "
            f"[默认 {DEFAULT_SERIAL_BAUD}]: "
        ).strip()

        if not baud:

            baud = DEFAULT_SERIAL_BAUD

        transport = SerialTransport(
            port,
            int(baud)
        )

    # --------------------------------------------------------
    # Wi-Fi
    # --------------------------------------------------------

    elif choice == "2":

        host = input(
            f"IP "
            f"[默认 {DEFAULT_TCP_HOST}]: "
        ).strip()

        if not host:

            host = DEFAULT_TCP_HOST

        port = input(
            f"端口 "
            f"[默认 35000]: "
        ).strip()

        if not port:

            port = "35000"

        transport = TCPTransport(
            host,
            int(port)
        )

    # --------------------------------------------------------
    # 模拟器
    # --------------------------------------------------------

    elif choice == "3":

        host = input(
            f"模拟器 IP "
            f"[默认 {DEFAULT_TCP_HOST}]: "
        ).strip()

        if not host:

            host = DEFAULT_TCP_HOST

        port = input(
            f"模拟器端口 "
            f"[默认 {DEFAULT_TCP_PORT}]: "
        ).strip()

        if not port:

            port = str(
                DEFAULT_TCP_PORT
            )

        transport = TCPTransport(
            host,
            int(port)
        )

    else:

        return None

    return transport


# ============================================================
# Main
# ============================================================

def main():

    transport = select_connection()

    if transport is None:

        print(
            "退出"
        )

        return

    obd = OBDController(
        transport
    )

    try:

        obd.connect()

        obd.menu()

    except Exception as e:

        print()
        print(
            "[!] 连接/运行失败:"
        )

        print(e)

    finally:

        transport.close()

        print()
        print(
            "[+] OBD 连接已关闭"
        )


if __name__ == "__main__":

    main()