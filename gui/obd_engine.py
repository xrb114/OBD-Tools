"""UDS Protocol Engine - refactored OBDController with Qt signal support."""

import time
import threading
from PyQt6.QtCore import QObject, pyqtSignal, QTimer


class OBDEngine(QObject):
    """Core OBD/UDS protocol engine with Qt signals for UI integration."""

    # Signals
    data_updated = pyqtSignal(dict)         # Real-time PID data
    dtc_received = pyqtSignal(list)         # DTC list
    vin_received = pyqtSignal(str)          # VIN string
    error_received = pyqtSignal(str)        # Error message
    connection_changed = pyqtSignal(bool)   # Connection state
    raw_command_sent = pyqtSignal(str)      # Outgoing raw command
    raw_response_received = pyqtSignal(str) # Incoming raw response
    log_message = pyqtSignal(str)           # Log/info message
    security_state_changed = pyqtSignal(str, bool)  # level, unlocked
    pid_list_received = pyqtSignal(list)    # Supported PIDs

    # Common PIDs
    PID_DEFINITIONS = {
        "0104": {"name": "发动机负载", "unit": "%", "formula": lambda a, b=0: round(a * 100 / 255, 1)},
        "0105": {"name": "冷却液温度", "unit": "°C", "formula": lambda a, b=0: a - 40},
        "0106": {"name": "短期燃油修正", "unit": "%", "formula": lambda a, b=0: round((a - 128) * 100 / 128, 1)},
        "0107": {"name": "长期燃油修正", "unit": "%", "formula": lambda a, b=0: round((a - 128) * 100 / 128, 1)},
        "010C": {"name": "发动机转速", "unit": "RPM", "formula": lambda a, b=0: round((a * 256 + b) / 4, 0)},
        "010D": {"name": "车速", "unit": "km/h", "formula": lambda a, b=0: a},
        "010F": {"name": "进气温度", "unit": "°C", "formula": lambda a, b=0: a - 40},
        "0110": {"name": "空气流量", "unit": "g/s", "formula": lambda a, b=0: round((a * 256 + b) / 100, 2)},
        "0111": {"name": "节气门位置", "unit": "%", "formula": lambda a, b=0: round(a * 100 / 255, 1)},
        "011F": {"name": "运行时间", "unit": "s", "formula": lambda a, b=0: a * 256 + b},
    }

    # Gauge display order
    GAUGE_PIDS = ["010C", "010D", "0105", "0104", "0111", "0110"]

    def __init__(self):
        super().__init__()
        self._transport = None
        self._connected = False
        self._streaming = False
        self._stream_thread = None
        self._stream_timer = None
        self._security_levels = {}
        self._last_data = {}

    @property
    def is_connected(self):
        return self._connected

    @property
    def is_streaming(self):
        return self._streaming

    @property
    def last_data(self):
        return self._last_data.copy()

    def set_transport(self, transport):
        self._transport = transport

    def connect(self) -> bool:
        if not self._transport:
            self.error_received.emit("未设置传输层")
            return False
        if self._transport.connect():
            result = self._init_elm327()
            if result:
                self._connected = True
                self.connection_changed.emit(True)
                self.log_message.emit("已连接并初始化 ELM327")
            return result
        return False

    def disconnect(self):
        self.stop_streaming()
        if self._transport:
            self._transport.close()
        self._connected = False
        self._security_levels.clear()
        self.connection_changed.emit(False)
        self.log_message.emit("已断开连接")

    def send(self, command: str) -> str:
        if not self._connected or not self._transport:
            return "NO CONNECTION"
        self.raw_command_sent.emit(command)
        response = self._transport.send(command)
        self.raw_response_received.emit(response)
        return response

    def _init_elm327(self) -> bool:
        init_cmds = ["ATZ", "ATE0", "ATL0", "ATS0", "ATH1", "ATSP0"]
        for cmd in init_cmds:
            resp = self._transport.send(cmd)
            if "ERROR" in resp.upper() and cmd == "ATZ":
                self.error_received.emit(f"ELM327初始化失败: {resp}")
                return False
            time.sleep(0.2)
        return True

    # ── PID Reading ──

    def read_pid(self, pid: str) -> dict:
        response = self.send(pid)
        return self._parse_pid_response(pid, response)

    def _parse_pid_response(self, pid: str, response: str) -> dict:
        if not response or "NO DATA" in response or "ERROR" in response:
            return {"pid": pid, "error": response or "无响应"}
        try:
            hex_bytes = response.replace("\n", " ").split()
            pid_prefix = pid[:2].upper() + pid[2:].upper()
            resp_prefix = hex(int(pid[:2], 16) + 0x40)[2:].upper() + pid[2:].upper()
            try:
                idx = hex_bytes.index(resp_prefix[:2])
                data_start = idx + 2
            except ValueError:
                data_start = 2 if len(hex_bytes) > 2 else 0
            data_bytes = []
            for h in hex_bytes[data_start:]:
                try:
                    data_bytes.append(int(h, 16))
                except ValueError:
                    break
            if pid in self.PID_DEFINITIONS and len(data_bytes) >= 1:
                pdef = self.PID_DEFINITIONS[pid]
                a = data_bytes[0] if len(data_bytes) > 0 else 0
                b = data_bytes[1] if len(data_bytes) > 1 else 0
                value = pdef["formula"](a, b)
                return {"pid": pid, "name": pdef["name"], "value": value, "unit": pdef["unit"], "raw": response}
            return {"pid": pid, "value": response, "unit": "", "raw": response}
        except Exception as e:
            return {"pid": pid, "error": str(e), "raw": response}

    def read_all_pids(self) -> dict:
        data = {}
        for pid in self.GAUGE_PIDS:
            result = self.read_pid(pid)
            if "error" not in result:
                data[pid] = result
        self._last_data = data
        self.data_updated.emit(data)
        return data

    def get_supported_pids(self) -> list:
        response = self.send("0100")
        if response and "NO DATA" not in response:
            self.pid_list_received.emit([response])
            return [response]
        return []

    # ── DTC (Fault Codes) ──

    def read_dtcs(self) -> list:
        response = self.send("03")
        dtcs = self._parse_dtc_response(response)
        self.dtc_received.emit(dtcs)
        return dtcs

    def _parse_dtc_response(self, response: str) -> list:
        if not response or "NO DATA" in response:
            return []
        dtcs = []
        hex_bytes = response.replace("\n", " ").split()
        if len(hex_bytes) < 4:
            return []
        i = 0
        while i < len(hex_bytes) - 2:
            if hex_bytes[i] == "43":
                count = int(hex_bytes[i + 1], 16) if i + 1 < len(hex_bytes) else 0
                i += 2
                for _ in range(count):
                    if i + 1 < len(hex_bytes):
                        try:
                            b1 = int(hex_bytes[i], 16)
                            b2 = int(hex_bytes[i + 1], 16)
                            dtc = self._decode_dtc(b1, b2)
                            if dtc != "P0000":
                                dtcs.append(dtc)
                        except:
                            pass
                        i += 2
                    else:
                        break
            else:
                i += 1
        return dtcs

    def _decode_dtc(self, b1: int, b2: int) -> str:
        prefix_map = {0: "P", 1: "C", 2: "B", 3: "U"}
        prefix = prefix_map.get((b1 >> 6) & 0x03, "P")
        code = f"{prefix}{(b1 & 0x3F):01X}{b2:02X}"
        return code.upper()

    def clear_dtcs(self) -> bool:
        response = self.send("04")
        if response and ("44" in response or "OK" in response.upper()):
            self.log_message.emit("故障码已清除")
            return True
        self.error_received.emit(f"清除失败: {response}")
        return False

    # ── VIN ──

    def read_vin(self) -> str:
        response = self.send("0902")
        vin = self._parse_vin(response)
        self.vin_received.emit(vin)
        return vin

    def _parse_vin(self, response: str) -> str:
        if not response or "NO DATA" in response:
            return ""
        try:
            hex_bytes = response.replace("\n", " ").split()
            chars = []
            for h in hex_bytes:
                try:
                    val = int(h, 16)
                    if 0x20 <= val <= 0x7E:
                        chars.append(chr(val))
                except:
                    continue
            vin = "".join(chars)
            for marker in ["4902", "01", "02", "03", "04", "05"]:
                vin = vin.replace(marker, "")
            return vin.strip()
        except:
            return response

    # ── Streaming ──

    def start_streaming(self, interval_ms: int = 500):
        if self._streaming:
            return
        self._streaming = True
        self._stream_timer = QTimer()
        self._stream_timer.timeout.connect(self._stream_tick)
        self._stream_timer.start(interval_ms)
        self.log_message.emit(f"开始数据流 ({interval_ms}ms 间隔)")

    def stop_streaming(self):
        if self._stream_timer:
            self._stream_timer.stop()
            self._stream_timer = None
        self._streaming = False
        self.log_message.emit("数据流已停止")

    def _stream_tick(self):
        if not self._connected:
            self.stop_streaming()
            return
        threading.Thread(target=self._stream_read, daemon=True).start()

    def _stream_read(self):
        try:
            self.read_all_pids()
        except:
            pass

    # ── Security Access (0x27) ──

    def security_request_seed(self, level: int) -> str:
        sub = f"{level:02X}"
        response = self.send(f"27{sub}")
        self.raw_response_received.emit(response)
        return response

    def security_send_key(self, level: int, key_hex: str) -> bool:
        sub = f"{level + 1:02X}"
        response = self.send(f"27{sub}{key_hex}")
        self.raw_response_received.emit(response)
        if response and "7F" not in response:
            self._security_levels[level] = True
            self.security_state_changed.emit(f"Level {level}", True)
            return True
        return False

    def security_calculate_key(self, seed_hex: str, level: int) -> str:
        seed_bytes = bytes.fromhex(seed_hex.replace(" ", ""))
        if level == 1:
            result = bytes([((~b & 0xFF) ^ 0x5A) for b in seed_bytes])
        elif level == 3:
            result = bytes([(b << 1) ^ 0x3C for b in seed_bytes])
        elif level == 5:
            import hashlib
            h = hashlib.md5(seed_bytes).digest()
            result = h[:4]
        elif level == 11:
            result = bytes([(b ^ 0x7F) for b in seed_bytes])
        else:
            result = bytes([(b ^ 0xAA) for b in seed_bytes])
        return result.hex().upper()

    # ── Raw Command ──

    def send_raw(self, command: str) -> str:
        return self.send(command)
