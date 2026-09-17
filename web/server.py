"""Flask + SocketIO web server for OBD-II UDS Terminal."""
from gevent import monkey
monkey.patch_all()
# trigger reload
import os
import sys
import csv
import json
import threading
import logging
from datetime import datetime
from flask import Flask, render_template, send_from_directory, jsonify, request
from flask_socketio import SocketIO, emit

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.transport import TCPTransport, SerialTransport, list_serial_ports
from web.obd_engine import OBDEngine
from web.dtc_database import decode_dtc_code, DTC_DATABASE

logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static", template_folder="static")
app.config["SECRET_KEY"] = "obd-terminal-nintendo"
#socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
#socketio = SocketIO(app, cors_allowed_origins="*", allow_eio3=True)
socketio = SocketIO(app, cors_allowed_origins="*", allow_eio3=True, async_mode="gevent")
# Global engine instance
engine = OBDEngine()
engine_lock = threading.Lock()


# ── Routes ──

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/serial_ports")
def api_serial_ports():
    return jsonify(list_serial_ports())


@app.route("/api/log_files")
def api_log_files():
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    files = []
    if os.path.exists(log_dir):
        for f in sorted(os.listdir(log_dir), reverse=True):
            if f.endswith(".csv"):
                filepath = os.path.join(log_dir, f)
                size = os.path.getsize(filepath)
                files.append({"name": f, "size": size})
    return jsonify(files)


@app.route("/api/download_log/<filename>")
def api_download_log(filename):
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    return send_from_directory(log_dir, filename, as_attachment=True)


# ── SocketIO Events ──

@socketio.on("connect")
def handle_connect():
    emit("status", {"connected": engine.is_connected, "streaming": engine.is_streaming})


# ── Connection Management ──

@socketio.on("connect_device")
def handle_connect_device(data):
    def do_connect():
        try:
            conn_type = data.get("type", "simulator")
            print(f"[连接] 类型: {conn_type}")

            transport = None
            if conn_type == "serial":
                port = data.get("port", "COM3")
                baudrate = int(data.get("baudrate", 38400))
                transport = SerialTransport(port=port, baudrate=baudrate)
                print(f"[连接] 串口: {port} @ {baudrate}")
            elif conn_type == "tcp":
                host = data.get("host", "127.0.0.1")
                port = int(data.get("port", 35000))
                transport = TCPTransport(host=host, port=port)
                print(f"[连接] TCP: {host}:{port}")
            else:  # simulator
                host = data.get("host", "127.0.0.1")
                port = int(data.get("port", 35000))
                transport = TCPTransport(host=host, port=port)
                print(f"[连接] 模拟器: {host}:{port}")

            with engine_lock:
                if engine.is_connected:
                    engine.disconnect()
                engine.set_transport(transport)
                print("[连接] 正在连接...")
                engine.connect()

            print("[连接] 成功!")
            socketio.emit("connection_result", {"success": True, "message": "连接成功"})
            socketio.emit("status", {"connected": True, "streaming": False})

        except Exception as e:
            print(f"[连接] 失败: {e}")
            socketio.emit("connection_result", {"success": False, "message": str(e)})

    threading.Thread(target=do_connect, daemon=True).start()


@socketio.on("disconnect_device")
def handle_disconnect_device():
    try:
        with engine_lock:
            engine.disconnect()
        emit("connection_result", {"success": True, "message": "已断开连接"})
        emit("status", {"connected": False, "streaming": False}, broadcast=True)
    except Exception as e:
        emit("connection_result", {"success": False, "message": str(e)})


# ── Dashboard ──

@socketio.on("start_streaming")
def handle_start_streaming(data=None):
    if not engine.is_connected:
        emit("error", {"message": "请先连接设备"})
        return

    interval = 500

    if data and "interval" in data:
        interval = int(data["interval"])

    engine.start_streaming(interval)

    emit(
        "streaming_state",
        {"streaming": True},
        broadcast=True,
    )

    def emit_data():
        logger.info(
            "[实时数据] 数据流启动，间隔=%dms",
            interval,
        )

        while engine.is_streaming and engine.is_connected:
            try:
                with engine_lock:
                    data = engine.read_all_pids()

                if data:
                    logger.info(
                        "[实时数据] %s",
                        data,
                    )

                    socketio.emit(
                        "data_update",
                        data,
                    )

            except Exception as e:
                logger.exception(
                    "[实时数据] 读取失败"
                )

                socketio.emit(
                    "error",
                    {
                        "message": f"实时数据读取失败: {e}"
                    },
                )

            socketio.sleep(
                interval / 1000.0
            )

        logger.info("[实时数据] 数据流结束")

    socketio.start_background_task(
        emit_data
    )


@socketio.on("stop_streaming")
def handle_stop_streaming():
    engine.stop_streaming()
    emit("streaming_state", {"streaming": False}, broadcast=True)


# ── DTC ──

@socketio.on("read_dtcs")
def handle_read_dtcs():
    if not engine.is_connected:
        emit("error", {"message": "请先连接设备"})
        return
    try:
        with engine_lock:
            dtcs = engine.read_dtcs()
        result = []
        system_map = {"P": "动力", "C": "底盘", "B": "车身", "U": "通信"}
        for dtc in dtcs:
            prefix = dtc[0] if dtc else "P"
            result.append({
                "code": dtc,
                "system": system_map.get(prefix, "未知"),
                "description": decode_dtc_code(dtc),
                "status": "当前故障"
            })
        emit("dtc_result", {"dtcs": result})
    except Exception as e:
        emit("error", {"message": f"读取故障码失败: {e}"})


@socketio.on("clear_dtcs")
def handle_clear_dtcs():
    if not engine.is_connected:
        emit("error", {"message": "请先连接设备"})
        return
    try:
        with engine_lock:
            success = engine.clear_dtcs()
        emit("dtc_clear_result", {"success": success})
    except Exception as e:
        emit("error", {"message": f"清除故障码失败: {e}"})


# ── Terminal ──

@socketio.on("send_command")
def handle_send_command(data):
    if not engine.is_connected:
        emit("error", {"message": "请先连接设备"})
        return
    cmd = data.get("command", "").strip()
    if not cmd:
        return
    try:
        with engine_lock:
            response = engine.send_raw(cmd)
        emit("command_response", {"command": cmd, "response": response})
    except Exception as e:
        emit("command_response", {"command": cmd, "response": f"ERROR: {e}"})


# ── Logger ──

_log_file = None
_log_writer = None
_record_count = 0
_recording = False
_record_timer = None


@socketio.on("start_recording")
def handle_start_recording(data=None):
    global _log_file, _log_writer, _record_count, _recording, _record_timer
    if not engine.is_connected:
        emit("error", {"message": "请先连接设备"})
        return
    if _recording:
        return

    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(log_dir, f"obd_{ts}.csv")

    _log_file = open(filepath, "w", newline="", encoding="utf-8-sig")
    _log_writer = csv.writer(_log_file)
    headers = ["timestamp"]
    for pid in ["0104", "0105", "0106", "0107", "010C", "010D", "010F", "0110", "0111", "011F"]:
        if pid in OBDEngine.PID_DEFINITIONS:
            headers.append(OBDEngine.PID_DEFINITIONS[pid]["name"])
        else:
            headers.append(pid)
    _log_writer.writerow(headers)
    _log_file.flush()

    _record_count = 0
    _recording = True
    interval = int(data.get("interval", 500)) if data else 500

    emit("recording_state", {"recording": True, "file": os.path.basename(filepath)}, broadcast=True)

    def record_tick():
        global _record_count
        while _recording and engine.is_connected:
            data = engine.last_data
            if data:
                row = [datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]]
                for pid in ["0104", "0105", "0106", "0107", "010C", "010D", "010F", "0110", "0111", "011F"]:
                    if pid in data and "value" in data[pid]:
                        row.append(data[pid]["value"])
                    else:
                        row.append("")
                if _log_writer:
                    _log_writer.writerow(row)
                    _log_file.flush()
                    _record_count += 1
                    socketio.emit("record_count", {"count": _record_count})
            import time
            time.sleep(interval / 1000.0)

    _record_timer = threading.Thread(target=record_tick, daemon=True)
    _record_timer.start()


@socketio.on("stop_recording")
def handle_stop_recording():
    global _log_file, _log_writer, _recording, _record_count
    _recording = False
    if _log_file:
        _log_file.close()
        _log_file = None
        _log_writer = None
    emit("recording_state", {"recording": False, "count": _record_count}, broadcast=True)


# ── Security Access (0x27) ──

@socketio.on("security_request_seed")
def handle_security_request_seed(data):
    if not engine.is_connected:
        emit("error", {"message": "请先连接设备"})
        return
    level = int(data.get("level", 1))
    try:
        with engine_lock:
            response = engine.security_request_seed(level)
        seed_hex = ""
        if response and "7F" not in response:
            hex_bytes = response.replace("\n", " ").split()
            seed_hex = "".join(hex_bytes[2:]) if len(hex_bytes) > 2 else ""
        key = engine.security_calculate_key(seed_hex, level) if seed_hex else ""
        emit("security_seed_result", {
            "level": level,
            "response": response,
            "seed": seed_hex,
            "key": key
        })
    except Exception as e:
        emit("error", {"message": f"请求种子失败: {e}"})


@socketio.on("security_send_key")
def handle_security_send_key(data):
    if not engine.is_connected:
        emit("error", {"message": "请先连接设备"})
        return
    level = int(data.get("level", 1))
    key_hex = data.get("key", "")
    try:
        with engine_lock:
            success = engine.security_send_key(level, key_hex)
        emit("security_key_result", {"level": level, "success": success})
    except Exception as e:
        emit("error", {"message": f"发送密钥失败: {e}"})


# ── Authentication (0x29) ──

@socketio.on("run_auth")
def handle_run_auth(data):
    if not engine.is_connected:
        emit("error", {"message": "请先连接设备"})
        return
    sub_func = data.get("subfunc", "01")
    try:
        with engine_lock:
            response = engine.send_raw(f"29{sub_func}")
        emit("auth_result", {"subfunc": sub_func, "response": response})
    except Exception as e:
        emit("error", {"message": f"认证失败: {e}"})


# ── Main ──

def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    port = int(os.environ.get("PORT", 8088))
    print(f"\n  UDS Terminal Web - Nintendo Editio v2")
    print(f"  http://localhost:{port}\n")
    socketio.run(app, host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
