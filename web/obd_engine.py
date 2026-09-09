"""OBD/UDS Protocol Engine (no Qt dependency)."""

import time
import threading
import hashlib
import logging

logger = logging.getLogger(__name__)


class OBDEngine:
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

    GAUGE_PIDS = ["010C", "010D", "0105", "0104", "0111", "0110"]

    def __init__(self):
        self._transport = None
        self._connected = False
        self._streaming = False
        self._stream_thread = None
        self._stream_interval = 0.5
        self._security_levels = {}
        self._last_data = {}

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_streaming(self) -> bool:
        return self._streaming

    @property
    def last_data(self) -> dict:
        return self._last_data.copy()

    def set_transport(self, transport):
        self._transport = transport

    def connect(self):
        if not self._transport:
            raise ValueError("未设置传输层")
        logger.info("OBDEngine: 正在连接传输层...")
        self._transport.connect()
        logger.info("OBDEngine: 传输层已连接，开始 ELM327 初始化...")
        if not self._init_elm327():
            raise ConnectionError("ELM327 初始化失败")
        self._connected = True
        logger.info("OBDEngine: 连接完成")

    def disconnect(self):
        self.stop_streaming()
        if self._transport:
            try:
                self._transport.close()
            except Exception as e:
                logger.warning(f"关闭传输层时出现异常: {e}")
        self._connected = False
        self._security_levels.clear()

    def send(self, command: str) -> str:
        if not self._connected or not self._transport:
            return "NO CONNECTION"
        response = self._transport.send(command)
        return response

    def _init_elm327(self) -> bool:
        init_cmds = ["ATZ", "ATE0", "ATL0", "ATS0", "ATH1", "ATSP0"]
        for cmd in init_cmds:
            logger.info(f"ELM327初始化: 发送 {cmd}")
            resp = self._transport.send(cmd)
            logger.info(f"ELM327初始化: {cmd} -> {repr(resp)}")
            if "ERROR" in resp.upper() and cmd == "ATZ":
                logger.error(f"ELM327初始化失败: {cmd} 返回 ERROR")
                return False
            time.sleep(0.2)
        logger.info("ELM327初始化完成")
        return True

    # ── PID Reading ──

    def read_pid(self, pid: str) -> dict:
        response = self.send(pid)
        return self._parse_pid_response(pid, response)

    def _parse_pid_response(self, pid: str, response: str) -> dict:
        if not response or "NO DATA" in response or "ERROR" in response:
            return {"pid": pid, "error": response or "无响应"}
        try:
            clean_resp = response.replace(">", "").replace("\r", " ").replace("\n", " ")
            hex_bytes = clean_resp.split()

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
        return data

    def get_supported_pids(self) -> list:
        response = self.send("0100")
        if response and "NO DATA" not in response:
            return [response]
        return []

    # ── DTC ──

    def read_dtcs(self) -> list:
        response = self.send("03")
        return self._parse_dtc_response(response)

    def _parse_dtc_response(self, response: str) -> list:
        if not response or "NO DATA" in response:
            return []

        # 清理多余换行符、回车符和 Prompt >
        clean_resp = response.replace(">", "").replace("\r", " ").replace("\n", " ")
        hex_bytes = clean_resp.split()

        if not hex_bytes:
            return []

        dtcs = []
        i = 0
        while i < len(hex_bytes):
            # 寻找 Service 03 的响应头 43
            if hex_bytes[i] == "43":
                i += 1  # 指向 43 后面的字节
                if i >= len(hex_bytes):
                    break

                # 判断下一个字节是否为"故障码数量 count"
                remaining = len(hex_bytes) - i
                try:
                    possible_count = int(hex_bytes[i], 16)
                    # 如果剩余字节数是奇数，并且数值刚好等于 DTC 对数 (remaining - 1) / 2
                    if remaining % 2 == 1 and possible_count == (remaining - 1) // 2:
                        i += 1  # 确认是 count 字节，跳过它
                except ValueError:
                    pass

                # 开始解析 DTC 字节对 (每 2 字节一组)
                while i + 1 < len(hex_bytes):
                    # 遇到下一个响应头或特定 AT 响应字符时退出
                    if hex_bytes[i] in ["43", "SEARCHING...", "OK", "STOPPED"]:
                        break
                    try:
                        b1 = int(hex_bytes[i], 16)
                        b2 = int(hex_bytes[i + 1], 16)

                        # 过滤 00 00 无效数据
                        if b1 != 0 or b2 != 0:
                            dtc = self._decode_dtc(b1, b2)
                            if dtc != "P0000" and dtc not in dtcs:
                                dtcs.append(dtc)
                    except ValueError:
                        break
                    i += 2
            else:
                i += 1

        return dtcs

    def _decode_dtc(self, b1: int, b2: int) -> str:
        prefix_map = {0: "P", 1: "C", 2: "B", 3: "U"}

        # 提取系统类别 (高 2 位: 00=P, 01=C, 10=B, 11=U)
        system_type = (b1 >> 6) & 0x03
        prefix = prefix_map.get(system_type, "P")

        # 强制高字节低 6 位与低字节 8 位格式化为 2 位 HEX 字符 (不足补 0)
        high_str = f"{(b1 & 0x3F):02X}"
        low_str = f"{b2:02X}"

        # 拼接出标准 5 位 DTC Code，例如: P0300
        return f"{prefix}{high_str}{low_str}".upper()

    def clear_dtcs(self) -> bool:
        response = self.send("04")
        if response and ("44" in response or "OK" in response.upper()):
            return True
        return False

    # ── VIN ──

    def read_vin(self) -> str:
        response = self.send("0902")
        return self._parse_vin(response)

    def _parse_vin(self, response: str) -> str:
        if not response or "NO DATA" in response:
            return ""
        try:
            clean_resp = response.replace(">", "").replace("\r", " ").replace("\n", " ")
            hex_bytes = clean_resp.split()
            chars = []
            for h in hex_bytes:
                try:
                    val = int(h, 16)
                    if 0x20 <= val <= 0x7E:
                        chars.append(chr(val))
                except Exception:
                    continue
            vin = "".join(chars)
            for marker in ["4902", "01", "02", "03", "04", "05"]:
                vin = vin.replace(marker, "")
            return vin.strip()
        except Exception:
            return response

    # ── Streaming ──

    def start_streaming(self, interval_ms: int = 500):
        if self._streaming:
            return
        self._streaming = True
        self._stream_interval = interval_ms / 1000.0
        self._stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._stream_thread.start()

    def stop_streaming(self):
        self._streaming = False

    def _stream_loop(self):
        while self._streaming and self._connected:
            try:
                self.read_all_pids()
            except Exception as e:
                logger.error(f"数据流读取异常: {e}")
            time.sleep(self._stream_interval)

    # ── Security Access (0x27) ──

    def security_request_seed(self, level: int) -> str:
        sub = f"{level:02X}"
        return self.send(f"27{sub}")

    def security_send_key(self, level: int, key_hex: str) -> bool:
        sub = f"{level + 1:02X}"
        response = self.send(f"27{sub}{key_hex}")
        if response and "7F" not in response:
            self._security_levels[level] = True
            return True
        return False

    def security_calculate_key(self, seed_hex: str, level: int) -> str:
        seed_bytes = bytes.fromhex(seed_hex.replace(" ", ""))
        if level == 1:
            result = bytes([((~b & 0xFF) ^ 0x5A) for b in seed_bytes])
        elif level == 3:
            result = bytes([(b << 1) ^ 0x3C for b in seed_bytes])
        elif level == 5:
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