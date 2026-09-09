/* ═══════════════════════════════════════════════════════════
   OBD 诊断终端 - 任天堂版 - 前端应用
   ═══════════════════════════════════════════════════════════ */

(function () {
    'use strict';

    const socket = io({
        transports: ['websocket', 'polling']
    });
    window._debugSocket = socket;  // debug: expose for inspection

    socket.on('connect', function() { console.log('[SocketIO] 已连接, id=' + socket.id); });
    socket.on('disconnect', function(reason) { console.log('[SocketIO] 断开: ' + reason); });
    socket.on('connect_error', function(err) { console.log('[SocketIO] 连接错误: ' + err.message); });

    let isConnected = false;
    let isStreaming = false;
    let isRecording = false;
    let commandHistory = [];
    let historyIndex = -1;

    const GAUGES = {
        rpm:      { pid: '010C', canvas: null, ctx: null, value: 0, target: 0, min: 0, max: 8000, label: 'RPM', unit: '' },
        speed:    { pid: '010D', canvas: null, ctx: null, value: 0, target: 0, min: 0, max: 260, label: 'km/h', unit: '' },
        coolant:  { pid: '0105', canvas: null, ctx: null, value: -40, target: -40, min: -40, max: 210, label: '\u00B0C', unit: '' },
        load:     { pid: '0104', canvas: null, ctx: null, value: 0, target: 0, min: 0, max: 100, label: '%', unit: '' },
        throttle: { pid: '0111', canvas: null, ctx: null, value: 0, target: 0, min: 0, max: 100, label: '%', unit: '' },
        maf:      { pid: '0110', canvas: null, ctx: null, value: 0, target: 0, min: 0, max: 655, label: 'g/s', unit: '' }
    };

    const EXTRA_PIDS = {
        '0106': 'val-stft',
        '0107': 'val-ltft',
        '010F': 'val-intake',
        '011F': 'val-runtime'
    };

    // ══════════════════════════════════════
    //  GAUGE RENDERING
    // ══════════════════════════════════════

    function initGauges() {
        Object.keys(GAUGES).forEach(key => {
            const canvas = document.getElementById(`gauge-${key}`);
            if (!canvas) return;
            GAUGES[key].canvas = canvas;
            GAUGES[key].ctx = canvas.getContext('2d');
            drawGauge(GAUGES[key]);
        });
        requestAnimationFrame(animateGauges);
    }

    function drawGauge(g) {
        const ctx = g.ctx;
        const w = g.canvas.width;
        const h = g.canvas.height;
        const cx = w / 2;
        const cy = h / 2;
        const r = Math.min(cx, cy) - 16;

        ctx.clearRect(0, 0, w, h);

        const startAngle = Math.PI * 0.75;
        const endAngle = Math.PI * 2.25;
        const totalAngle = endAngle - startAngle;
        const tickCount = 10;

        // Background arc
        ctx.beginPath();
        ctx.arc(cx, cy, r, startAngle, endAngle, false);
        ctx.lineWidth = 18;
        ctx.strokeStyle = '#1a1a2e';
        ctx.lineCap = 'butt';
        ctx.stroke();

        // Inner shadow ring
        ctx.beginPath();
        ctx.arc(cx, cy, r - 12, startAngle, endAngle, false);
        ctx.lineWidth = 2;
        ctx.strokeStyle = '#0a0a1a';
        ctx.stroke();

        // Tick marks
        ctx.lineWidth = 2;
        ctx.strokeStyle = '#3a3a5e';
        for (let i = 0; i <= tickCount; i++) {
            const angle = startAngle + (totalAngle * i / tickCount);
            const inner = r - 28;
            const outer = r - 18;
            ctx.beginPath();
            ctx.moveTo(cx + Math.cos(angle) * inner, cy + Math.sin(angle) * inner);
            ctx.lineTo(cx + Math.cos(angle) * outer, cy + Math.sin(angle) * outer);
            ctx.stroke();
        }

        // Value arc
        const pct = Math.max(0, Math.min(1, (g.value - g.min) / (g.max - g.min)));
        const valueAngle = startAngle + totalAngle * pct;

        let color;
        if (pct < 0.6) color = '#00a651';
        else if (pct < 0.8) color = '#f5b800';
        else color = '#e4000f';

        // Glow
        ctx.beginPath();
        ctx.arc(cx, cy, r, startAngle, valueAngle, false);
        ctx.lineWidth = 22;
        ctx.strokeStyle = color + '25';
        ctx.lineCap = 'butt';
        ctx.stroke();

        // Main arc
        ctx.beginPath();
        ctx.arc(cx, cy, r, startAngle, valueAngle, false);
        ctx.lineWidth = 14;
        ctx.strokeStyle = color;
        ctx.lineCap = 'butt';
        ctx.stroke();

        // Center dot
        ctx.beginPath();
        ctx.arc(cx, cy, 5, 0, Math.PI * 2);
        ctx.fillStyle = '#fff';
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = '#1a1a1a';
        ctx.stroke();

        // Tick labels
        ctx.font = '8px "Press Start 2P", "Courier New", monospace';
        ctx.fillStyle = '#6a6a8a';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';

        for (let i = 0; i <= tickCount; i += 2) {
            const angle = startAngle + (totalAngle * i / tickCount);
            const labelR = r - 40;
            const val = Math.round(g.min + (g.max - g.min) * i / tickCount);
            const lx = cx + Math.cos(angle) * labelR;
            const ly = cy + Math.sin(angle) * labelR;
            ctx.fillText(val.toString(), lx, ly);
        }
    }

    function animateGauges() {
        Object.values(GAUGES).forEach(g => {
            const diff = g.target - g.value;
            if (Math.abs(diff) > 0.5) {
                g.value += diff * 0.15;
                drawGauge(g);
            } else if (g.value !== g.target) {
                g.value = g.target;
                drawGauge(g);
            }
        });
        requestAnimationFrame(animateGauges);
    }

    // ══════════════════════════════════════
    //  NAVIGATION
    // ══════════════════════════════════════

    function initNav() {
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const page = btn.dataset.page;
                document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
                const target = document.getElementById(`page-${page}`);
                if (target) target.classList.add('active');
            });
        });
    }

    // ══════════════════════════════════════
    //  TABS
    // ══════════════════════════════════════

    function initTabs() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.dataset.tab;
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                document.getElementById(`tab-${tab}`).classList.add('active');
            });
        });
    }

    // ══════════════════════════════════════
    //  TOAST
    // ══════════════════════════════════════

    function showToast(message, type = '') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = 'toast' + (type ? ` ${type}` : '');
        clearTimeout(toast._timer);
        toast._timer = setTimeout(() => toast.classList.add('hidden'), 3500);
    }

    // ══════════════════════════════════════
    //  SETTINGS
    // ══════════════════════════════════════

    function initSettings() {
        const connType = document.getElementById('connType');
        const tcpConfig = document.getElementById('tcpConfig');
        const serialConfig = document.getElementById('serialConfig');

        connType.addEventListener('change', () => {
            const val = connType.value;
            tcpConfig.classList.toggle('hidden', val === 'serial');
            serialConfig.classList.toggle('hidden', val !== 'serial');
        });

        document.getElementById('btnRefreshPorts').addEventListener('click', refreshSerialPorts);

        document.getElementById('btnConnect').addEventListener('click', () => {
            const type = connType.value;
            const data = { type };

            if (type === 'serial') {
                data.port = document.getElementById('serialPort').value;
                data.baudrate = document.getElementById('serialBaud').value;
            } else {
                data.host = document.getElementById('tcpHost').value;
                data.port = document.getElementById('tcpPort').value;
            }

            addConnLog(`正在连接 (${type})...`);
            socket.emit('connect_device', data);
        });

        document.getElementById('btnDisconnect').addEventListener('click', () => {
            socket.emit('disconnect_device');
        });

        refreshSerialPorts();
    }

    function refreshSerialPorts() {
        fetch('/api/serial_ports')
            .then(r => r.json())
            .then(ports => {
                const sel = document.getElementById('serialPort');
                sel.innerHTML = '';
                if (ports.length === 0) {
                    sel.innerHTML = '<option value="">未检测到串口</option>';
                } else {
                    ports.forEach(p => {
                        const opt = document.createElement('option');
                        opt.value = p.device;
                        opt.textContent = `${p.device} - ${p.description}`;
                        sel.appendChild(opt);
                    });
                }
            })
            .catch(() => {
                const sel = document.getElementById('serialPort');
                sel.innerHTML = '<option value="">加载串口失败</option>';
            });
    }

    function addConnLog(msg) {
        const log = document.getElementById('connLog');
        const time = new Date().toLocaleTimeString();
        log.innerHTML += `<div>[${time}] ${msg}</div>`;
        log.scrollTop = log.scrollHeight;
    }

    // ══════════════════════════════════════
    //  DASHBOARD
    // ══════════════════════════════════════

    function initDashboard() {
        document.getElementById('btnStream').addEventListener('click', () => {
            if (!isConnected) {
                showToast('请先连接设备', 'error');
                return;
            }
            if (isStreaming) {
                socket.emit('stop_streaming');
            } else {
                socket.emit('start_streaming', { interval: 500 });
            }
        });
    }

    // ══════════════════════════════════════
    //  DTC
    // ══════════════════════════════════════

    function initDTC() {
        document.getElementById('btnReadDtc').addEventListener('click', () => {
            if (!isConnected) { showToast('请先连接设备', 'error'); return; }
            socket.emit('read_dtcs');
            setDtcStatus('正在读取故障码...', '');
        });

        document.getElementById('btnClearDtc').addEventListener('click', () => {
            if (!isConnected) { showToast('请先连接设备', 'error'); return; }
            if (confirm('确定要清除所有故障码吗？\n此操作不可撤销。')) {
                socket.emit('clear_dtcs');
            }
        });
    }

    function setDtcStatus(msg, cls) {
        const el = document.getElementById('dtcStatus');
        el.textContent = msg;
        el.className = 'dtc-status' + (cls ? ` ${cls}` : '');
    }

    // ══════════════════════════════════════
    //  TERMINAL
    // ══════════════════════════════════════

    function initTerminal() {
        const input = document.getElementById('termInput');

        document.getElementById('btnSend').addEventListener('click', () => sendCommand());

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                sendCommand();
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (commandHistory.length > 0 && historyIndex > 0) {
                    historyIndex--;
                    input.value = commandHistory[historyIndex];
                }
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (historyIndex < commandHistory.length - 1) {
                    historyIndex++;
                    input.value = commandHistory[historyIndex];
                } else {
                    historyIndex = commandHistory.length;
                    input.value = '';
                }
            }
        });

        document.getElementById('btnClearTerm').addEventListener('click', () => {
            const output = document.getElementById('termOutput');
            output.innerHTML = '<div class="term-line term-info">终端已清屏</div>';
        });

        document.querySelectorAll('.btn-quick').forEach(btn => {
            btn.addEventListener('click', () => {
                const cmd = btn.dataset.cmd;
                if (cmd) sendCommand(cmd);
            });
        });
    }

    function sendCommand(cmd) {
        const input = document.getElementById('termInput');
        if (!cmd) cmd = input.value.trim().toUpperCase();
        input.value = '';

        if (!cmd) return;
        if (!isConnected) {
            appendTerm('错误: 未连接设备', 'term-error');
            return;
        }

        commandHistory.push(cmd);
        historyIndex = commandHistory.length;

        appendTerm(`>>> ${cmd}`, 'term-cmd');
        socket.emit('send_command', { command: cmd });
    }

    function appendTerm(text, cls = '') {
        const output = document.getElementById('termOutput');
        const line = document.createElement('div');
        line.className = 'term-line' + (cls ? ` ${cls}` : '');
        line.textContent = text;
        output.appendChild(line);
        output.scrollTop = output.scrollHeight;
    }

    // ══════════════════════════════════════
    //  LOGGER
    // ══════════════════════════════════════

    function initLogger() {
        document.getElementById('btnRecord').addEventListener('click', () => {
            if (!isConnected) { showToast('请先连接设备', 'error'); return; }
            if (isRecording) {
                socket.emit('stop_recording');
            } else {
                const interval = document.getElementById('logInterval').value;
                socket.emit('start_recording', { interval: parseInt(interval) });
            }
        });

        document.getElementById('btnRefreshLogs').addEventListener('click', refreshLogFiles);
        refreshLogFiles();
    }

    function refreshLogFiles() {
        fetch('/api/log_files')
            .then(r => r.json())
            .then(files => {
                const body = document.getElementById('logBody');
                body.innerHTML = '';
                files.forEach(f => {
                    const sizeStr = f.size < 1024 ? `${f.size} B` : `${(f.size / 1024).toFixed(1)} KB`;
                    body.innerHTML += `
                        <tr>
                            <td>${f.name}</td>
                            <td>${sizeStr}</td>
                            <td><a href="/api/download_log/${f.name}" class="btn btn-small" style="text-decoration:none;display:inline-block;">下载</a></td>
                        </tr>`;
                });
            })
            .catch(() => {});
    }

    // ══════════════════════════════════════
    //  SECURITY
    // ══════════════════════════════════════

    function initSecurity() {
        document.getElementById('btnReqSeed').addEventListener('click', () => {
            if (!isConnected) { showToast('请先连接设备', 'error'); return; }
            const level = document.getElementById('secLevel').value;
            socket.emit('security_request_seed', { level: parseInt(level) });
            addSecLog(`[发送] 27${parseInt(level).toString(16).toUpperCase().padStart(2, '0')} - 请求种子 (等级 ${level})`);
        });

        document.getElementById('btnSendKey').addEventListener('click', () => {
            if (!isConnected) { showToast('请先连接设备', 'error'); return; }
            const level = document.getElementById('secLevel').value;
            const key = document.getElementById('secKey').value;
            if (!key) { showToast('无密钥可发送', 'error'); return; }
            socket.emit('security_send_key', { level: parseInt(level), key });
            addSecLog(`[发送] 27${(parseInt(level) + 1).toString(16).toUpperCase().padStart(2, '0')}${key} - 发送密钥`);
        });

        document.getElementById('btnAuth').addEventListener('click', () => {
            if (!isConnected) { showToast('请先连接设备', 'error'); return; }
            const subfunc = document.getElementById('authFunc').value;
            socket.emit('run_auth', { subfunc });
            addSecLog(`[发送] 29${subfunc} - 执行认证`);
        });
    }

    function addSecLog(msg, cls = '') {
        const log = document.getElementById('secLog');
        const time = new Date().toLocaleTimeString();
        log.innerHTML += `<div class="${cls}" style="position:relative;z-index:1;">[${time}] ${msg}</div>`;
        log.scrollTop = log.scrollHeight;
    }

    // ══════════════════════════════════════
    //  SOCKET EVENTS
    // ══════════════════════════════════════

    socket.on('status', (data) => {
        isConnected = data.connected;
        updateConnectionUI();
    });

    socket.on('connection_result', (data) => {
        if (data.success) {
            showToast(data.message, 'success');
            addConnLog(data.message);
        } else {
            showToast(data.message, 'error');
            addConnLog(`错误: ${data.message}`);
        }
        updateConnectionUI();
    });

    socket.on('streaming_state', (data) => {
        isStreaming = data.streaming;
        const btn = document.getElementById('btnStream');
        btn.textContent = isStreaming ? '停止采集' : '开始采集';
        btn.className = isStreaming ? 'btn btn-danger' : 'btn btn-action';
    });

    socket.on('data_update', (data) => {
        Object.entries(GAUGES).forEach(([key, g]) => {
            if (data[g.pid] && data[g.pid].value !== undefined) {
                g.target = data[g.pid].value;
                const valEl = document.getElementById(`val-${key}`);
                if (valEl) valEl.innerHTML = `${data[g.pid].value} <span class="gauge-unit">${g.label}</span>`;
            }
        });

        Object.entries(EXTRA_PIDS).forEach(([pid, elId]) => {
            if (data[pid] && data[pid].value !== undefined) {
                const el = document.getElementById(elId);
                if (el) el.textContent = data[pid].value;
            }
        });

        updateLiveTable(data);
    });

    socket.on('dtc_result', (data) => {
        const body = document.getElementById('dtcBody');
        body.innerHTML = '';
        if (data.dtcs.length === 0) {
            setDtcStatus('未发现故障码', 'success');
            return;
        }
        setDtcStatus(`发现 ${data.dtcs.length} 个故障码`, 'error');
        data.dtcs.forEach(d => {
            body.innerHTML += `
                <tr>
                    <td style="color:var(--nes-red);font-weight:bold;">${d.code}</td>
                    <td>${d.system}</td>
                    <td>${d.description}</td>
                    <td>${d.status}</td>
                </tr>`;
        });
    });

    socket.on('dtc_clear_result', (data) => {
        if (data.success) {
            document.getElementById('dtcBody').innerHTML = '';
            setDtcStatus('故障码已清除', 'success');
        } else {
            setDtcStatus('清除故障码失败', 'error');
        }
    });

    socket.on('command_response', (data) => {
        appendTerm(data.response, 'term-resp');
    });

    socket.on('recording_state', (data) => {
        isRecording = data.recording;
        const btn = document.getElementById('btnRecord');
        const status = document.getElementById('recStatus');
        if (data.recording) {
            btn.innerHTML = '&#9632; 停止录制';
            btn.className = 'btn btn-danger';
            status.textContent = '录制中...';
            status.className = 'rec-status recording';
            document.getElementById('recFile').textContent = data.file || '';
        } else {
            btn.innerHTML = '&#9679; 开始录制';
            btn.className = 'btn btn-action';
            status.textContent = '录制完成';
            status.className = 'rec-status';
            document.getElementById('recCount').textContent = `记录: ${data.count || 0}`;
            refreshLogFiles();
        }
    });

    socket.on('record_count', (data) => {
        document.getElementById('recCount').textContent = `记录: ${data.count}`;
    });

    socket.on('security_seed_result', (data) => {
        document.getElementById('secSeed').value = data.seed || data.response;
        document.getElementById('secKey').value = data.key || '';
        document.getElementById('btnSendKey').disabled = !data.seed;
        addSecLog(`[种子] ${data.seed || data.response}`, 'log-resp');
        if (data.key) addSecLog(`[计算] 密钥 = ${data.key}`, 'log-info');
    });

    socket.on('security_key_result', (data) => {
        const statusEl = document.getElementById('secStatus');
        if (data.success) {
            statusEl.innerHTML = `&#128275; 等级 ${data.level} 已解锁`;
            statusEl.className = 'sec-status unlocked';
            addSecLog(`[成功] 等级 ${data.level} 已解锁`, 'log-resp');
        } else {
            statusEl.innerHTML = '&#128274; 密钥验证失败';
            statusEl.className = 'sec-status';
            addSecLog('[失败] 密钥被拒绝', 'log-cmd');
        }
    });

    socket.on('auth_result', (data) => {
        addSecLog(`[响应] ${data.response}`, 'log-resp');
    });

    socket.on('error', (data) => {
        showToast(data.message, 'error');
    });

    // ══════════════════════════════════════
    //  HELPERS
    // ══════════════════════════════════════

    function updateConnectionUI() {
        const dot = document.querySelector('.status-dot');
        const text = document.querySelector('.status-text');
        const connStatus = document.getElementById('connStatus');
        const btnConnect = document.getElementById('btnConnect');
        const btnDisconnect = document.getElementById('btnDisconnect');

        if (isConnected) {
            dot.className = 'status-dot online';
            text.textContent = '已连接';
            connStatus.textContent = '状态: 已连接';
            connStatus.className = 'conn-status connected';
            btnConnect.disabled = true;
            btnDisconnect.disabled = false;
        } else {
            dot.className = 'status-dot offline';
            text.textContent = '未连接';
            connStatus.textContent = '状态: 未连接';
            connStatus.className = 'conn-status';
            btnConnect.disabled = false;
            btnDisconnect.disabled = true;
            isStreaming = false;
            isRecording = false;
            const streamBtn = document.getElementById('btnStream');
            streamBtn.textContent = '开始采集';
            streamBtn.className = 'btn btn-action';
        }
    }

    function updateLiveTable(data) {
        const body = document.getElementById('liveBody');
        if (!body) return;
        let html = '';
        Object.entries(data).forEach(([pid, info]) => {
            if (info.error) return;
            html += `
                <tr>
                    <td>${pid}</td>
                    <td>${info.name || ''}</td>
                    <td class="val-cell">${info.value}</td>
                    <td>${info.unit || ''}</td>
                </tr>`;
        });
        body.innerHTML = html;
    }

    // ══════════════════════════════════════
    //  INIT
    // ══════════════════════════════════════

    function init() {
        initNav();
        initTabs();
        initGauges();
        initDashboard();
        initDTC();
        initTerminal();
        initLogger();
        initSettings();
        initSecurity();
        updateConnectionUI();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
