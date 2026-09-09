"""Transport layer for ELM327 communication (no Qt dependency)."""

import socket
import time
import logging

logger = logging.getLogger(__name__)


class TCPTransport:
    def __init__(self, host="127.0.0.1", port=35000, timeout=5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock = None
        self._connected = False

    @property
    def is_connected(self):
        return self._connected

    def connect(self):
        try:
            logger.info(f"TCPTransport: 正在连接 {self.host}:{self.port}...")
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self.timeout)
            self._sock.connect((self.host, self.port))
            self._connected = True
            logger.info(f"TCPTransport: 已连接到 {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"TCPTransport: 连接失败 - {e}")
            raise ConnectionError(f"TCP连接失败: {e}")

    def send(self, command: str) -> str:
        if not self._connected or not self._sock:
            raise ConnectionError("未连接")
        try:
            logger.debug(f"TCPTransport: 发送命令: {command}")
            self._sock.sendall((command + "\r").encode("ascii"))
            response = ""
            deadline = time.time() + self.timeout
            while time.time() < deadline:
                try:
                    chunk = self._sock.recv(4096).decode("ascii", errors="replace")
                    if not chunk:
                        break
                    logger.debug(f"TCPTransport: 收到数据: {repr(chunk)}")
                    response += chunk
                    if ">" in response:
                        break
                except socket.timeout:
                    logger.debug(f"TCPTransport: 接收超时, 当前响应: {repr(response)}")
                    break
            cleaned = response.replace(">", "").strip()
            lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
            result = "\n".join(lines)
            logger.debug(f"TCPTransport: 清理后响应: {repr(result)}")
            return result
        except Exception as e:
            logger.error(f"TCPTransport: 发送失败 - {e}")
            raise IOError(f"发送失败: {e}")

    def close(self):
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        self._connected = False


class SerialTransport:
    def __init__(self, port="COM3", baudrate=38400, timeout=5.0):
        self.port_name = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial = None
        self._connected = False

    @property
    def is_connected(self):
        return self._connected

    def connect(self):
        try:
            import serial
            self._serial = serial.Serial(
                port=self.port_name,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout,
            )
            self._connected = True
            return True
        except Exception as e:
            raise ConnectionError(f"串口连接失败: {e}")

    def send(self, command: str) -> str:
        if not self._connected or not self._serial:
            raise ConnectionError("未连接")
        try:
            self._serial.reset_input_buffer()
            self._serial.write((command + "\r").encode("ascii"))
            self._serial.flush()
            response = ""
            deadline = time.time() + self.timeout
            while time.time() < deadline:
                if self._serial.in_waiting:
                    chunk = self._serial.read(self._serial.in_waiting).decode("ascii", errors="replace")
                    response += chunk
                    if ">" in response:
                        break
                time.sleep(0.02)
            cleaned = response.replace(">", "").strip()
            lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
            return "\n".join(lines)
        except Exception as e:
            raise IOError(f"发送失败: {e}")

    def close(self):
        if self._serial:
            try:
                self._serial.close()
            except Exception:
                pass
            self._serial = None
        self._connected = False


def list_serial_ports():
    ports = []
    try:
        import serial.tools.list_ports
        for p in serial.tools.list_ports.comports():
            ports.append({"device": p.device, "description": p.description})
    except ImportError:
        pass
    return ports
