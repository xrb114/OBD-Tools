"""Transport layer for ELM327 communication."""

import socket
import time
import threading
import logging

logger = logging.getLogger(__name__)


class TCPTransport:
    def __init__(self, host="127.0.0.1", port=35000, timeout=5.0):
        self.host = host
        self.port = port
        self.timeout = timeout

        self._sock = None
        self._connected = False

        # 保证同一个 TCP 连接同一时间只有一个命令在发送/读取
        self._lock = threading.Lock()

        # TCP 是字节流，需要保存上一次 recv 中多出来的数据
        self._rx_buffer = ""

    @property
    def is_connected(self):
        return self._connected

    def connect(self):
        try:
            logger.info(
                "TCPTransport: 正在连接 %s:%s...",
                self.host,
                self.port,
            )

            self._sock = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM,
            )

            self._sock.settimeout(self.timeout)
            self._sock.connect((self.host, self.port))

            self._connected = True
            self._rx_buffer = ""

            logger.info(
                "TCPTransport: 已连接到 %s:%s",
                self.host,
                self.port,
            )

            return True

        except Exception as e:
            logger.error("TCPTransport: 连接失败 - %s", e)

            if self._sock:
                try:
                    self._sock.close()
                except Exception:
                    pass

            self._sock = None
            self._connected = False

            raise ConnectionError(f"TCP连接失败: {e}")

    def _read_until_prompt(self):
        """
        从 TCP 字节流中读取一个完整的 ELM327 响应。

        ELM327 通常以 '>' 作为命令响应结束标志。

        注意：
        一次 recv() 可能同时包含多个响应，
        因此必须保存 '>' 后面的数据到 _rx_buffer。
        """

        deadline = time.time() + self.timeout

        while time.time() < deadline:

            # 先检查之前缓存的数据
            prompt_index = self._rx_buffer.find(">")

            if prompt_index >= 0:
                response = self._rx_buffer[:prompt_index]

                # 保留 > 后面的数据
                self._rx_buffer = self._rx_buffer[prompt_index + 1:]

                return response

            try:
                chunk = self._sock.recv(4096)

                if not chunk:
                    raise ConnectionError("TCP连接已关闭")

                text = chunk.decode(
                    "ascii",
                    errors="replace",
                )

                logger.debug(
                    "TCPTransport: 收到数据: %r",
                    text,
                )

                self._rx_buffer += text

            except socket.timeout:
                break

        # 超时情况下，如果还有缓存数据，也返回
        if self._rx_buffer:
            response = self._rx_buffer
            self._rx_buffer = ""
            return response

        return ""

    @staticmethod
    def _clean_response(response):
        response = response.replace("\x00", "")

        lines = []

        for line in response.replace("\r", "\n").split("\n"):
            line = line.strip()

            if not line:
                continue

            lines.append(line)

        return "\n".join(lines)

    def send(self, command: str) -> str:
        if not self._connected or not self._sock:
            raise ConnectionError("未连接")

        command = command.strip()

        if not command:
            return ""

        with self._lock:
            try:
                logger.debug(
                    "TCPTransport: 发送命令: %s",
                    command,
                )

                self._sock.sendall(
                    (command + "\r").encode("ascii")
                )

                response = self._read_until_prompt()

                result = self._clean_response(response)

                logger.debug(
                    "TCPTransport: 清理后响应: %r",
                    result,
                )

                return result

            except Exception as e:
                logger.error(
                    "TCPTransport: 发送失败 - %s",
                    e,
                )

                raise IOError(f"发送失败: {e}")

    def close(self):
        with self._lock:
            if self._sock:
                try:
                    self._sock.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass

                try:
                    self._sock.close()
                except Exception:
                    pass

            self._sock = None
            self._connected = False
            self._rx_buffer = ""


class SerialTransport:
    def __init__(self, port="COM3", baudrate=38400, timeout=5.0):
        self.port_name = port
        self.baudrate = baudrate
        self.timeout = timeout

        self._serial = None
        self._connected = False

        self._lock = threading.Lock()

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
            raise ConnectionError(
                f"串口连接失败: {e}"
            )

    @staticmethod
    def _clean_response(response):
        response = response.replace("\x00", "")

        lines = []

        for line in response.replace("\r", "\n").split("\n"):
            line = line.strip()

            if not line:
                continue

            lines.append(line)

        return "\n".join(lines)

    def send(self, command: str) -> str:
        if not self._connected or not self._serial:
            raise ConnectionError("未连接")

        command = command.strip()

        if not command:
            return ""

        with self._lock:
            try:
                # 清掉旧数据
                self._serial.reset_input_buffer()

                self._serial.write(
                    (command + "\r").encode("ascii")
                )

                self._serial.flush()

                response = ""
                deadline = time.time() + self.timeout

                while time.time() < deadline:

                    if self._serial.in_waiting:
                        chunk = self._serial.read(
                            self._serial.in_waiting
                        ).decode(
                            "ascii",
                            errors="replace",
                        )

                        response += chunk

                        if ">" in response:
                            break

                    time.sleep(0.01)

                result = self._clean_response(response)

                logger.debug(
                    "SerialTransport: %s -> %r",
                    command,
                    result,
                )

                return result

            except Exception as e:
                raise IOError(
                    f"发送失败: {e}"
                )

    def close(self):
        with self._lock:
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
            ports.append({
                "device": p.device,
                "description": p.description,
            })

    except ImportError:
        pass

    return ports