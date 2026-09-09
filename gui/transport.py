"""Transport layer for ELM327 communication (TCP and Serial)."""
import socket
import time
from PyQt6.QtCore import QObject, pyqtSignal


class BaseTransport(QObject):
    """Base transport with Qt signals for async event handling."""
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)
    raw_response = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._connected = False

    @property
    def is_connected(self):
        return self._connected

    def connect(self):
        raise NotImplementedError

    def send(self, command: str) -> str:
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


class TCPTransport(BaseTransport):
    """WiFi/TCP ELM327 adapter transport."""

    def __init__(self, host: str = "127.0.0.1", port: int = 35000, timeout: float = 5.0):
        super().__init__()
        self.host = host
        self.port = port
        self.timeout = timeout
        self._sock = None

    def connect(self):
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self.timeout)
            self._sock.connect((self.host, self.port))
            self._connected = True
            self.connected.emit()
            return True
        except Exception as e:
            self.error.emit(f"TCP连接失败: {e}")
            return False

    def send(self, command: str) -> str:
        if not self._connected or not self._sock:
            self.error.emit("未连接")
            return "NO CONNECTION"
        try:
            self._sock.sendall((command + "\r").encode("ascii"))
            response = ""
            deadline = time.time() + self.timeout
            while time.time() < deadline:
                try:
                    chunk = self._sock.recv(4096).decode("ascii", errors="replace")
                    if not chunk:
                        break
                    response += chunk
                    if ">" in response:
                        break
                except socket.timeout:
                    break
            cleaned = response.replace(">", "").strip()
            lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
            result = "\n".join(lines)
            self.raw_response.emit(result)
            return result
        except Exception as e:
            self.error.emit(f"发送失败: {e}")
            return "ERROR"

    def close(self):
        if self._sock:
            try:
                self._sock.close()
            except:
                pass
            self._sock = None
        self._connected = False
        self.disconnected.emit()


class SerialTransport(BaseTransport):
    """USB/Serial ELM327 adapter transport."""

    def __init__(self, port: str = "COM3", baudrate: int = 38400, timeout: float = 5.0):
        super().__init__()
        self.port_name = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial = None

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
            self.connected.emit()
            return True
        except Exception as e:
            self.error.emit(f"串口连接失败: {e}")
            return False

    def send(self, command: str) -> str:
        if not self._connected or not self._serial:
            self.error.emit("未连接")
            return "NO CONNECTION"
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
            result = "\n".join(lines)
            self.raw_response.emit(result)
            return result
        except Exception as e:
            self.error.emit(f"发送失败: {e}")
            return "ERROR"

    def close(self):
        if self._serial:
            try:
                self._serial.close()
            except:
                pass
            self._serial = None
        self._connected = False
        self.disconnected.emit()


def list_serial_ports():
    """List available serial ports on the system."""
    ports = []
    try:
        import serial.tools.list_ports
        for p in serial.tools.list_ports.comports():
            ports.append({"device": p.device, "description": p.description})
    except ImportError:
        pass
    return ports
