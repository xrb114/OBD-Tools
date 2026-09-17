# OBD-TOOL

OBD-TOOL 是一个基于 Python 的 OBD-II / UDS 诊断工具，主要用于通过 **ELM327 兼容适配器**连接车辆，并提供 Web 端实时数据监控、OBD-II PID 读取、DTC 故障码读取以及 UDS 诊断功能。

项目当前以 **Web 端为主要使用方式**，支持通过串口或 TCP/IP 连接真实 ELM327 设备。

同时项目保留了一个自研的 `obd_simulator.py`，用于开发和测试 Web 端、ELM327 通信以及 OBD-II PID 解析，不依赖真实车辆即可进行基础功能测试。

---

## 功能特点

### Web 诊断界面

* 基于 Flask + Socket.IO
* 浏览器直接访问诊断界面
* 实时显示车辆数据
* Web Terminal
* OBD-II PID 读取
* DTC 故障码读取
* VIN 读取
* 实时数据流
* TCP / 串口设备连接
* 实时通信状态显示
* 日志记录

### OBD-II

支持常见的标准 OBD-II Mode 01 PID，包括：

* 发动机转速
* 车速
* 发动机冷却液温度
* 发动机负荷
* 短期燃油修正
* 长期燃油修正
* 进气温度
* MAF 空气流量
* 节气门位置
* 发动机运行时间
* 燃油液位
* 控制模块电压

同时支持：

* Mode 03：读取故障码
* Mode 09：读取车辆信息
* VIN 读取
* ELM327 AT 命令

### UDS

项目包含部分 UDS 诊断功能：

* `0x27` Security Access
* `0x29` Authentication
* Seed / Key 认证流程
* 多安全访问级别
* 基于 RSA 的认证功能
* 双向认证实验功能

---

#  项目结构

```text
OBD-TOOL/
│
├── web/                         # Web 版核心程序
│   ├── server.py                # Flask + Socket.IO 服务
│   ├── obd_engine.py            # OBD/UDS 协议引擎
│   ├── transport.py             # TCP / Serial 通信层
│   ├── dtc_database.py          # DTC 数据库
│   │
│   └── static/
│       ├── index.html           # Web 主页面
│       ├── app.js               # 前端逻辑
│       ├── style.css            # 页面样式
│       ├── socket.io.min.js     # Socket.IO 客户端
│       └── fonts/               # Web 字体
│
├── obd_simulator.py             # 自研 OBD-II 测试模拟器
│
├── logs/                        # OBD 数据日志
│
└── requirements.txt             # Python 依赖
```

---

#  快速开始

## 1. 安装依赖

建议使用 Python 3.10+。

安装项目依赖：

```bash
pip install -r requirements.txt
```

---

#  启动 Web 服务

Web 是当前项目的主要运行入口。

在项目根目录执行：

```bash
python -m web.server
```

启动后，根据终端输出访问 Web 页面。

通常为：

```text
http://127.0.0.1:8088
```

---

#  连接真实 ELM327

Web 后端通过 `web/transport.py` 提供两种通信方式：

```text
                    ┌── SerialTransport ── USB/串口 ELM327
Web
 │
 ▼
server.py
 │
 ▼
obd_engine.py
 │
 ▼
transport.py
 │
 └── TCPTransport ─────── TCP/WiFi ELM327
```

## 串口连接

例如：

```text
COM4
38400 baud
```

Web 页面选择对应串口后连接设备。

实际波特率取决于 ELM327 适配器。

---

## TCP 连接

支持 TCP ELM327 设备，例如：

```text
192.168.1.100:35000
```

输入：

```text
Host: 192.168.1.100
Port: 35000
```

即可通过 TCP 建立连接。

---

#  Web Terminal

Web Terminal 可以直接发送 ELM327 命令。

例如：

```text
ATZ
```

返回：

```text
ELM327 v1.5
```

关闭回显：

```text
ATE0
```

选择自动协议：

```text
ATSP0
```

读取支持的 PID：

```text
0100
```

读取发动机转速：

```text
010C
```

读取车速：

```text
010D
```

读取冷却液温度：

```text
0105
```

读取发动机负荷：

```text
0104
```

读取节气门位置：

```text
0111
```

读取故障码：

```text
03
```

读取 VIN：

```text
0902
```

---

# 📊 支持的 OBD-II PID

| PID    | 描述            | 单位   |
| ------ | ------------- | ---- |
| `0100` | 支持的 PID 01-20 | -    |
| `0101` | 监控状态          | -    |
| `0104` | 计算的发动机负荷      | %    |
| `0105` | 发动机冷却液温度      | °C   |
| `0106` | 短期燃油修正        | %    |
| `0107` | 长期燃油修正        | %    |
| `010B` | 进气歧管绝对压力      | kPa  |
| `010C` | 发动机转速         | RPM  |
| `010D` | 车速            | km/h |
| `010F` | 进气温度          | °C   |
| `0110` | MAF 空气流量      | g/s  |
| `0111` | 节气门位置         | %    |
| `011F` | 发动机运行时间       | s    |
| `012F` | 燃油液位          | %    |
| `0142` | 控制模块电压        | V    |
| `03`   | 故障码           | DTC  |
| `0902` | VIN           | -    |

---

#  实时数据

Web 页面支持实时轮询车辆 PID。

默认主要监控：

```text
发动机转速
车速
冷却液温度
发动机负荷
节气门位置
MAF 空气流量
```

数据流程：

```text
Web
 │
 ▼
OBDEngine
 │
 ├── 010C RPM
 ├── 010D Speed
 ├── 0105 Coolant
 ├── 0104 Load
 ├── 0111 Throttle
 └── 0110 MAF
 │
 ▼
ELM327
 │
 ▼
车辆 ECU
```

实时数据通过 Socket.IO 推送到浏览器。

---

#  自研 OBD-II 模拟器

项目保留：

```text
obd_simulator.py
```

它不是 Web 系统运行的必要组件，而是一个用于开发和测试的独立工具。

模拟器支持：

* 虚拟发动机转速
* 虚拟车速
* 虚拟挡位
* 虚拟油门
* 虚拟冷却液温度
* 虚拟蓄电池电压
* OBD-II PID
* ELM327 AT 命令
* USB 串口通信
* TCP/WiFi 通信
* UDP 实时数据广播

---

## 启动模拟器

```bash
python obd_simulator.py
```

默认可以启动：

```text
USB:
COM3 @ 38400

TCP:
0.0.0.0:35000

UDP:
35001
```

模拟器启动后，可以使用 Web OBD 工具连接：

```text
127.0.0.1:35000
```

这样可以在没有真实车辆和 ELM327 的情况下测试 Web 页面。

---

# 模拟器控制

运行模拟器后：

| 按键  | 功能     |
| --- | ------ |
| `W` | 增加油门   |
| `S` | 减少油门   |
| `A` | 降档     |
| `D` | 升档     |
| `R` | 设置目标转速 |
| `Q` | 退出模拟器  |

模拟器根据：

```text
转速
挡位
主减速比
轮胎周长
油门
```

计算车辆速度和发动机状态。

---

#  ELM327 AT 命令

当前支持常见 AT 命令：

```text
ATZ
ATI
AT@1
AT@2

ATSP0
ATSP6
ATDP

ATRV

ATH0
ATH1

ATE0
ATE1

ATL0
ATS0

ATST0A
```

---

#  DTC 故障码

支持通过 Mode 03 读取故障码：

```text
03
```

例如：

```text
43 00 00 00 00 00 00
```

表示当前没有故障码。

Web 端可以将 ECU 返回的 DTC 数据进一步转换为故障码描述。

---

#  UDS 0x27 Security Access

项目提供 UDS `0x27` 安全访问相关测试功能。

支持：

```text
2701 / 2702
2703 / 2704
2705 / 2706
2711 / 2712
```

基本流程：

```text
Tester
  │
  │ 2701
  ▼
ECU
  │
  │ 67 01 + Seed
  ▼
Tester
  │
  │ 根据 Seed 计算 Key
  │
  │ 2702 + Key
  ▼
ECU
  │
  │ 67 02
  ▼
Security Access Granted
```

---

## Security Access 测试

运行：

```bash
python security_access_client.py
```

指定安全级别：

```bash
python security_access_client.py -l 01
```

测试错误密钥：

```bash
python security_access_client.py -l 01 -i
```

测试 Seed 超时：

```bash
python security_access_client.py -l 01 -w 6
```

---

#  UDS 0x29 Authentication

项目还包含 UDS `0x29` Authentication 实验功能。

支持基础认证：

```text
2901
2902
2903
```

以及基于 PKI 的双向认证：

```text
2904
2905
2906
2907
```

双向认证使用 RSA 密钥。

密钥目录：

```text
keys/
├── server_keys.json
├── client_keys.json
└── clients/
    └── default_client.json
```

---

#  测试工具

## 0x27 Security Access

```bash
python security_access_client.py
```

综合测试：

```bash
python test_security_access.py
```

Seed 过期：

```bash
python test_seed_expiry.py
```

---

## 0x29 Authentication

基础认证：

```bash
python auth_test_client.py
```

双向认证：

```bash
python auth_bidirectional_client.py
```

---

## OBD 客户端

```bash
python obd_client.py
```

用于测试基础 OBD-II 数据读取。

---

#  日志

运行过程中产生的 OBD 数据可以保存到：

```text
logs/
```

例如：

```text
logs/
├── obd_20260909_143853.csv
├── obd_20260909_144837.csv
├── obd_20260909_192207.csv
└── obd_20260918_000500.csv
```

日志可以用于后续：

* 数据分析
* 车辆状态回放
* PID 数据检查
* 实时数据异常排查
* 车辆测试记录

---

#  项目模块关系

当前 Web 版本的核心链路：

```text
                    Browser
                       │
                       │ Socket.IO
                       ▼
               ┌───────────────┐
               │ web/server.py │
               └───────┬───────┘
                       │
                       ▼
             ┌───────────────────┐
             │ web/obd_engine.py │
             └─────────┬─────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ web/transport.py│
              └────────┬────────┘
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
       SerialTransport      TCPTransport
             │                   │
             ▼                   ▼
          ELM327              ELM327
             │                   │
             └─────────┬─────────┘
                       ▼
                    Vehicle
                       │
                       ▼
                      ECU
```

---

#  Web 运行所需文件

如果只运行 Web 版本，核心文件主要是：

```text
web/
├── __init__.py
├── server.py
├── obd_engine.py
├── transport.py
├── dtc_database.py
└── static/
    ├── index.html
    ├── app.js
    ├── style.css
    ├── socket.io.min.js
    └── fonts/
```

再加：

```text
requirements.txt
```

因此：

```text
gui/
ELM327-emulator/
```

都不是 Web 版本的必要依赖。

`obd_simulator.py` 也不是 Web 的运行依赖，仅用于测试。

---

#  开发建议

推荐将项目划分为两个部分：

```text
生产使用
│
└── web/
    ├── server.py
    ├── obd_engine.py
    ├── transport.py
    └── static/

测试
│
└──obd_simulator.py



```

这样 Web 核心与测试工具互相独立。

---

# ⚠️ 注意事项

本项目中的 UDS Security Access、Authentication 以及相关密钥算法主要用于开发、测试和研究。

实际车辆上的 UDS 服务、Seed/Key 算法、认证机制以及安全策略通常由具体 ECU 厂商实现，并不一定与本项目中的测试实现一致。

连接真实车辆时，应确认：

* ELM327 适配器工作正常
* 串口参数正确
* TCP 地址和端口正确
* 车辆支持对应 OBD-II 服务
* 不要向未知 ECU 随意发送写入或编程类 UDS 请求

---

# 📚 参考标准

项目涉及的主要协议和标准：

* ELM327
* SAE J1979 / OBD-II
* ISO 14229-1 / UDS
* ISO 15764
* PKCS#1
* RSA

---

# 🗺️ 开发计划

* [x] Web OBD 控制界面
* [x] ELM327 AT 命令
* [x] TCP ELM327 通信
* [x] Serial ELM327 通信
* [x] OBD-II Mode 01
* [x] OBD-II Mode 03
* [x] VIN 读取
* [x] Web 实时数据
* [x] DTC 数据库
* [x] 自研 OBD-II 测试模拟器
* [x] UDS 0x27 基础实现
* [x] UDS 0x29 基础实现
* [ ] 完善 UDS 诊断会话 `0x10`
* [ ] ECU Reset `0x11`
* [ ] Clear DTC `0x14`
* [ ] Read DTC Information `0x19`
* [ ] Read Data By Identifier `0x22`
* [ ] Write Data By Identifier `0x2E`
* [ ] Routine Control `0x31`
* [ ] Request Download `0x34`
* [ ] Transfer Data `0x36`
* [ ] 完善 0x27 Seed/Key 管理
* [ ] 完善 0x29 双向认证
* [ ] 增加 ECDSA 支持
* [ ] 完善实时日志系统
* [ ] 增加数据回放功能
* [ ] 增加更多车辆/ECU适配
* [ ] 完善 Web 配置界面

---

#  License

本项目主要用于汽车电子、OBD-II、UDS、诊断工具以及相关通信协议的学习、开发与测试。
