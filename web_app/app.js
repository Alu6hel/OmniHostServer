// ==============================================================================
// OmniHost Pro - Client-Side App Controller & Android Bridge
// Complete Dynamic Backend Integration, Live Themes & Real Network Benchmarking
// ==============================================================================

const API_BASE = (window.location.protocol === 'file:') ? 'http://127.0.0.1:8090' : '';

let isServersRunning = true;
let currentTab = 'hotspot';
let activeSite = 'default';
let lanIp = '127.0.0.1';

// Tunnel State
let isTunnelActive = false;
let tunnelPublicUrl = '';

// Limits State (Image 2)
let timerLimitMin = 0;
const timerOptions = [0, 15, 30, 60, 120];
let timerIndex = 0;

let batteryLimitPct = 0;
const batteryOptions = [0, 15, 20, 30];
let batteryIndex = 0;

let dataLimitMb = 0;
const dataOptions = [0, 100, 500, 1024, 5120];
let dataIndex = 0;

// Bridge Wrapper
const hasNativeBridge = typeof window.OmniHostBridge !== 'undefined';

function initApp() {
    setupDeviceState();
    initLiveThemeCanvas();
    pollTelemetry();
    pollTunnelStatus();
    setInterval(pollTelemetry, 2000);
    setInterval(pollTunnelStatus, 4000);
}

// State Sync from Native Android or Web fallback
function setupDeviceState() {
    if (hasNativeBridge && window.OmniHostBridge.getDeviceInfoJson) {
        try {
            const dev = JSON.parse(window.OmniHostBridge.getDeviceInfoJson());
            if (dev.lanIp) lanIp = dev.lanIp;
            if (dev.activeSite) activeSite = dev.activeSite;
            if (dev.httpRunning !== undefined) isServersRunning = dev.httpRunning;
            if (dev.tunnelActive !== undefined) isTunnelActive = dev.tunnelActive;
            if (dev.tunnelUrl !== undefined) tunnelPublicUrl = dev.tunnelUrl;
            updateUrls();
            updatePowerButtonUI();
        } catch (e) {
            console.error("Bridge parse err:", e);
        }
    } else {
        // Web Mode: detect from window.location
        if (window.location.hostname && window.location.hostname !== 'localhost') {
            lanIp = window.location.hostname;
        }
        updateUrls();
    }
}

// Called by Android MainActivity
window.onHostStateSync = function(state) {
    if (state.lanIp) lanIp = state.lanIp;
    if (state.activeSite) activeSite = state.activeSite;
    if (state.httpRunning !== undefined) isServersRunning = state.httpRunning;
    if (state.tunnelActive !== undefined) isTunnelActive = state.tunnelActive;
    if (state.tunnelUrl !== undefined) tunnelPublicUrl = state.tunnelUrl;
    updateUrls();
    updatePowerButtonUI();
    highlightActiveSiteCard();
};

window.onFtpEvent = function(type, details) {
    const feed = document.getElementById('ftp-event-feed');
    if (!feed) return;
    const emptyPl = document.getElementById('ftp-empty-placeholder');
    if (emptyPl) emptyPl.style.display = 'none';

    const row = document.createElement('div');
    row.className = 'terminal-row';
    const now = new Date().toTimeString().split(' ')[0];
    row.innerText = `[${now}] [${type}] ${details}`;
    feed.appendChild(row);
    feed.scrollTop = feed.scrollHeight;
};

// URL Displays & Offline Handling
function updateUrls() {
    const elWeb = document.getElementById('display-web-url');
    const elFtp = document.getElementById('display-ftp-url');
    const elExplorer = document.getElementById('display-explorer-url');
    const elFtpFull = document.getElementById('ftp-full-url');
    const elFtpGuide = document.getElementById('ftp-guide-url');
    const elSiteTag = document.getElementById('current-site-tag');

    const stripWeb = document.getElementById('strip-web');
    const stripFtp = document.getElementById('strip-ftp');
    const stripExplorer = document.getElementById('strip-explorer');
    const btnCopyWeb = document.getElementById('btn-copy-web');
    const btnCopyFtp = document.getElementById('btn-copy-ftp');
    const btnCopyExplorer = document.getElementById('btn-copy-explorer');
    const btnOpenExplorer = document.getElementById('btn-open-explorer');

    if (!isServersRunning) {
        if (elWeb) elWeb.innerText = "● Offline — Tap Power to Start";
        if (elFtp) elFtp.innerText = "● Offline — Tap Power to Start";
        if (elExplorer) elExplorer.innerText = "● Offline — Tap Power to Start";
        if (elFtpFull) elFtpFull.innerText = "● Offline — Tap Power to Start";
        if (elFtpGuide) elFtpGuide.innerText = `ftp://${lanIp}:2121 (Offline)`;

        if (stripWeb) stripWeb.classList.add('offline');
        if (stripFtp) stripFtp.classList.add('offline');
        if (stripExplorer) stripExplorer.classList.add('offline');

        if (btnCopyWeb) btnCopyWeb.classList.add('disabled');
        if (btnCopyFtp) btnCopyFtp.classList.add('disabled');
        if (btnCopyExplorer) btnCopyExplorer.classList.add('disabled');
        if (btnOpenExplorer) btnOpenExplorer.classList.add('disabled');
    } else {
        const webUrl = `http://${lanIp}:8090`;
        const ftpUrl = `ftp://${lanIp}:2121`;
        const explorerUrl = `http://${lanIp}:8090/files`;

        if (elWeb) elWeb.innerText = webUrl;
        if (elFtp) elFtp.innerText = ftpUrl;
        if (elExplorer) elExplorer.innerText = explorerUrl;
        if (elFtpFull) elFtpFull.innerText = ftpUrl;
        if (elFtpGuide) elFtpGuide.innerText = ftpUrl;

        if (stripWeb) stripWeb.classList.remove('offline');
        if (stripFtp) stripFtp.classList.remove('offline');
        if (stripExplorer) stripExplorer.classList.remove('offline');

        if (btnCopyWeb) btnCopyWeb.classList.remove('disabled');
        if (btnCopyFtp) btnCopyFtp.classList.remove('disabled');
        if (btnCopyExplorer) btnCopyExplorer.classList.remove('disabled');
        if (btnOpenExplorer) btnOpenExplorer.classList.remove('disabled');
    }

    if (elSiteTag) elSiteTag.innerText = activeSite;
    updateTunnelUI();
}

// Tunnel State UI & Management
function updateTunnelUI() {
    const elTunnel = document.getElementById('display-tunnel-url');
    const badge = document.getElementById('tunnel-badge');
    const btnToggle = document.getElementById('btn-toggle-tunnel');
    const btnCopy = document.getElementById('btn-copy-tunnel');

    if (isTunnelActive && tunnelPublicUrl) {
        if (elTunnel) elTunnel.innerText = tunnelPublicUrl;
        if (badge) {
            badge.innerText = "LIVE ONLINE";
            badge.style.background = "rgba(16, 185, 129, 0.2)";
            badge.style.borderColor = "#10B981";
            badge.style.color = "#10B981";
        }
        if (btnToggle) {
            btnToggle.innerText = "Stop";
            btnToggle.style.background = "#EF4444";
            btnToggle.style.color = "#ffffff";
        }
        if (btnCopy) btnCopy.classList.remove('disabled');
    } else {
        if (elTunnel) elTunnel.innerText = "● Standby — Tap to Activate";
        if (badge) {
            badge.innerText = "STANDBY";
            badge.style.background = "rgba(245, 158, 11, 0.15)";
            badge.style.borderColor = "#F59E0B";
            badge.style.color = "#F59E0B";
        }
        if (btnToggle) {
            btnToggle.innerText = "Activate";
            btnToggle.style.background = "#10B981";
            btnToggle.style.color = "#000000";
        }
        if (btnCopy) btnCopy.classList.add('disabled');
    }
}

async function toggleTunnelAction() {
    const newState = !isTunnelActive;
    if (hasNativeBridge && window.OmniHostBridge.toggleTunnel) {
        window.OmniHostBridge.toggleTunnel(newState);
        showToast(newState ? "🚀 Tunnel activating..." : "🛑 Tunnel stopped.");
    } else {
        try {
            const endpoint = newState ? `${API_BASE}/api/tunnel/start` : `${API_BASE}/api/tunnel/stop`;
            const res = await fetch(endpoint, { method: 'POST' });
            const data = await res.json();
            if (data.status === 'ok') {
                isTunnelActive = newState;
                if (data.url) tunnelPublicUrl = data.url;
                updateTunnelUI();
                showToast(newState ? "🚀 Public Tunnel is Live!" : "🛑 Tunnel stopped.");
            }
        } catch (e) {
            showToast("Tunnel error: " + e.message);
        }
    }
}

async function pollTunnelStatus() {
    if (hasNativeBridge) return;
    try {
        const res = await fetch(`${API_BASE}/api/tunnel/status`);
        const data = await res.json();
        if (data) {
            isTunnelActive = !!data.active;
            if (data.url) tunnelPublicUrl = data.url;
            updateTunnelUI();
        }
    } catch (e) {}
}

// Master Power Toggle
function toggleMasterPower() {
    isServersRunning = !isServersRunning;
    if (hasNativeBridge && window.OmniHostBridge.toggleAllServers) {
        window.OmniHostBridge.toggleAllServers(isServersRunning);
    }
    updatePowerButtonUI();
    updateUrls();
    showToast(isServersRunning ? "⚡ All Servers Activated (:8090 & :2121)" : "🛑 All Servers Stopped");
}

function updatePowerButtonUI() {
    const btn = document.getElementById('main-power-btn');
    const track = document.getElementById('radial-track');
    const dot = document.getElementById('global-status-dot');
    const statusText = document.getElementById('global-status-text');
    const subtext = document.getElementById('power-subtext');
    const ftpBadge = document.getElementById('ftp-status-badge');

    if (isServersRunning) {
        if (btn) btn.classList.add('active');
        if (track) track.style.stroke = 'var(--primary)';
        if (dot) dot.classList.remove('offline');
        if (statusText) statusText.innerText = 'Serving :8090 & :2121';
        if (subtext) subtext.innerText = 'Tap to Stop Servers';
        if (ftpBadge) {
            ftpBadge.className = 'val green';
            ftpBadge.innerText = '● LISTENING (:2121)';
        }
    } else {
        if (btn) btn.classList.remove('active');
        if (track) track.style.stroke = 'var(--border-subtle)';
        if (dot) dot.classList.add('offline');
        if (statusText) statusText.innerText = '● Disabled';
        if (subtext) subtext.innerText = 'Tap to Start Servers';
        if (ftpBadge) {
            ftpBadge.className = 'val';
            ftpBadge.innerText = '● STOPPED';
        }
    }
}

// 3 Limits Cycling (Image 2)
function cycleTimerLimit() {
    timerIndex = (timerIndex + 1) % timerOptions.length;
    timerLimitMin = timerOptions[timerIndex];
    const el = document.getElementById('limit-timer-val');
    if (el) {
        el.innerText = timerLimitMin === 0 ? 'Disabled' : `${timerLimitMin} min`;
    }
    pushLimitsToBridge();
}

function cycleBatteryLimit() {
    batteryIndex = (batteryIndex + 1) % batteryOptions.length;
    batteryLimitPct = batteryOptions[batteryIndex];
    const el = document.getElementById('limit-battery-val');
    if (el) {
        el.innerText = batteryLimitPct === 0 ? 'Disabled' : `${batteryLimitPct}%`;
    }
    pushLimitsToBridge();
}

function cycleDataLimit() {
    dataIndex = (dataIndex + 1) % dataOptions.length;
    dataLimitMb = dataOptions[dataIndex];
    const el = document.getElementById('limit-data-val');
    if (el) {
        if (dataLimitMb === 0) el.innerText = 'Disabled';
        else if (dataLimitMb >= 1024) el.innerText = `${dataLimitMb / 1024} GB`;
        else el.innerText = `${dataLimitMb} MB`;
    }
    pushLimitsToBridge();
}

function pushLimitsToBridge() {
    if (hasNativeBridge && window.OmniHostBridge.setLimits) {
        window.OmniHostBridge.setLimits(timerLimitMin, batteryLimitPct, dataLimitMb);
    }
}

// Navigation Tabs
function selectTab(tabId) {
    currentTab = tabId;
    document.querySelectorAll('.tab-view').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));

    const tabEl = document.getElementById(`tab-${tabId}`);
    if (tabEl) tabEl.classList.add('active');

    const navBtn = document.getElementById(`nav-${tabId}`);
    if (navBtn) navBtn.classList.add('active');

    const titleMap = {
        'hotspot': 'WiFi Hotspot',
        'sites': 'Modular Sites',
        'ftp': 'WiFi FTP Server',
        'speed': 'Speed Test',
        'data': 'Data Usage'
    };
    const titleEl = document.getElementById('top-bar-title');
    if (titleEl && titleMap[tabId]) titleEl.innerText = titleMap[tabId];

    if (tabId === 'sites') {
        previewSite(activeSite);
    }
}

// Drawer Controls
function toggleDrawer(open) {
    const drawer = document.getElementById('drawer');
    const overlay = document.getElementById('drawer-overlay');
    if (open) {
        drawer.classList.add('open');
        overlay.classList.add('open');
    } else {
        drawer.classList.remove('open');
        overlay.classList.remove('open');
    }
}

// Modular Site Switcher
function selectSite(siteName) {
    activeSite = siteName;
    highlightActiveSiteCard();
    updateUrls();

    if (hasNativeBridge && window.OmniHostBridge.switchSite) {
        window.OmniHostBridge.switchSite(siteName);
    } else {
        fetch(`${API_BASE}/api/switch-site`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ site_name: siteName })
        }).catch(() => {});
    }

    previewSite(siteName);
}

function highlightActiveSiteCard() {
    document.querySelectorAll('.site-card').forEach(c => {
        if (c.id === `card-site-${activeSite}`) {
            c.classList.add('active');
            const badge = c.querySelector('.site-badge');
            if (badge) badge.innerText = 'Active ★';
        } else {
            c.classList.remove('active');
            const badge = c.querySelector('.site-badge');
            if (badge) badge.innerText = 'Template';
        }
    });
}

function previewSite(siteName) {
    const iframe = document.getElementById('site-preview-iframe');
    const previewUrlText = document.getElementById('preview-url-text');
    if (iframe) {
        iframe.src = `http://${lanIp}:8090/`;
    }
    if (previewUrlText) {
        previewUrlText.innerText = `http://${lanIp}:8090/ (${siteName})`;
    }
}

function openWebUrl(siteName) {
    selectSite(siteName);
    window.open(`http://${lanIp}:8090/`, '_blank');
}

function openExplorerUrl() {
    window.open(`http://${lanIp}:8090/files`, '_blank');
}

// Hotspot Settings Shortcut
function openHotspotSettings() {
    if (hasNativeBridge && window.OmniHostBridge.openHotspotSettings) {
        window.OmniHostBridge.openHotspotSettings();
    } else {
        alert("To enable your hotspot: Open Android Settings -> Network & internet -> Hotspot & tethering.");
    }
}

// Real Speed Test Benchmark
async function startSpeedTest() {
    const btn = document.getElementById('btn-run-speed-test');
    if (btn) btn.disabled = true;

    const num = document.getElementById('gauge-speed-val');
    const ratingEl = document.getElementById('speed-rating-text');

    if (num) num.innerText = "...";
    if (ratingEl) ratingEl.innerText = "Running full-duplex network benchmark...";

    // If native bridge exists, it triggers real socket test in Java
    if (hasNativeBridge && window.OmniHostBridge.runSpeedTest) {
        window.OmniHostBridge.runSpeedTest();
        return;
    }

    // Real in-browser client speed test against :8090/api/speedtest/*
    try {
        // 1. Latency Ping (3 rounds)
        const pings = [];
        for (let i = 0; i < 3; i++) {
            const t0 = performance.now();
            await fetch(`${API_BASE}/api/speedtest/ping?t=${Date.now()}`);
            pings.push(performance.now() - t0);
        }
        const avgPing = Math.round(pings.reduce((a, b) => a + b, 0) / pings.length);
        const jitter = Math.round(Math.abs(pings[1] - pings[0]) + Math.abs(pings[2] - pings[1])) / 2;

        // 2. Real Download Test (2MB payload)
        const d0 = performance.now();
        const dlRes = await fetch(`${API_BASE}/api/speedtest/download?size=2097152&t=${Date.now()}`);
        const dlBuf = await dlRes.arrayBuffer();
        const dDuration = (performance.now() - d0) / 1000;
        const dlMbps = parseFloat(((dlBuf.byteLength * 8) / (dDuration * 1000000)).toFixed(1));

        // 3. Real Upload Test (1MB payload)
        const uploadBytes = new Uint8Array(1048576);
        const u0 = performance.now();
        await fetch(`${API_BASE}/api/speedtest/upload`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/octet-stream' },
            body: uploadBytes
        });
        const uDuration = (performance.now() - u0) / 1000;
        const ulMbps = parseFloat(((uploadBytes.byteLength * 8) / (uDuration * 1000000)).toFixed(1));

        window.onSpeedTestResult({
            pingMs: avgPing,
            jitterMs: Math.round(jitter),
            downloadMbps: dlMbps,
            uploadMbps: ulMbps,
            rating: dlMbps > 40 ? 'High-Performance Line Speed — 4K Stream & Rapid Sync' : 'Stable Local Connection for Web Hosting'
        });
    } catch (e) {
        console.error("Speedtest error:", e);
        if (btn) btn.disabled = false;
        if (ratingEl) ratingEl.innerText = "Error: Please verify server is started.";
    }
}

window.onSpeedTestResult = function(res) {
    const btn = document.getElementById('btn-run-speed-test');
    if (btn) btn.disabled = false;

    const num = document.getElementById('gauge-speed-val');
    if (num) num.innerText = res.downloadMbps.toFixed(1);

    const ping = document.getElementById('speed-ping');
    if (ping) ping.innerText = `${res.pingMs} ms`;

    const jitter = document.getElementById('speed-jitter');
    if (jitter) jitter.innerText = `${res.jitterMs} ms`;

    const down = document.getElementById('speed-down');
    if (down) down.innerText = `${res.downloadMbps} Mbps`;

    const up = document.getElementById('speed-up');
    if (up) up.innerText = `${res.uploadMbps} Mbps`;

    const rating = document.getElementById('speed-rating-text');
    if (rating) rating.innerText = res.rating;
};

// Telemetry Polling & Empty State Management
function pollTelemetry() {
    if (hasNativeBridge && window.OmniHostBridge.getTelemetryJson) {
        try {
            const data = JSON.parse(window.OmniHostBridge.getTelemetryJson());
            applyTelemetryData(data);
        } catch (e) {}
    } else {
        fetch(`${API_BASE}/api/status`)
            .then(r => r.json())
            .then(data => applyTelemetryData(data))
            .catch(() => {});
    }
}

function applyTelemetryData(data) {
    if (!data) return;
    if (data.tunnel_running !== undefined) {
        isTunnelActive = !!data.tunnel_running;
        if (data.tunnel_url) tunnelPublicUrl = data.tunnel_url;
        updateTunnelUI();
    }
    const qps = document.getElementById('qps-val');
    if (qps && data.qps !== undefined) qps.innerText = `${data.qps} req/s`;

    const reqs = document.getElementById('requests-val');
    if (reqs && data.total_requests !== undefined) reqs.innerText = data.total_requests;

    const bw = document.getElementById('bandwidth-val');
    if (bw && data.total_bytes !== undefined) {
        const kb = Math.round(data.total_bytes / 1024);
        bw.innerText = kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb} KB`;
    }

    const uptime = document.getElementById('uptime-val');
    if (uptime && data.uptime_seconds !== undefined) {
        const s = data.uptime_seconds;
        uptime.innerText = s >= 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`;
    }

    const feed = document.getElementById('http-log-feed');
    const emptyPl = document.getElementById('http-empty-placeholder');

    if (data.recent_logs && data.recent_logs.length > 0) {
        if (emptyPl) emptyPl.style.display = 'none';
        if (feed) {
            feed.innerHTML = '';
            data.recent_logs.forEach(log => {
                const row = document.createElement('div');
                row.className = 'terminal-row';
                row.innerText = `[${log.timestamp}] ${log.method} ${log.path} • ${log.status} (${log.size}B) • ${log.ip}`;
                feed.appendChild(row);
            });
            feed.scrollTop = feed.scrollHeight;
        }
    } else {
        if (emptyPl) emptyPl.style.display = 'flex';
    }
}

// Copy Helper
function copyValue(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    const text = el.innerText || el.textContent;
    if (text.includes("Offline") || text.includes("Standby")) {
        showToast("Service is not running yet");
        return;
    }
    if (hasNativeBridge && window.OmniHostBridge.copyToClipboard) {
        window.OmniHostBridge.copyToClipboard(text);
        showToast("Copied to clipboard: " + text);
    } else {
        navigator.clipboard.writeText(text).then(() => {
            showToast("Copied to clipboard: " + text);
        }).catch(() => {
            showToast("Copied: " + text);
        });
    }
}

// Toast Notification
function showToast(message) {
    const container = document.getElementById('toast-notify');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast-message';
    toast.innerHTML = `<span>✨</span><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 2800);
}

// LIVE THEME ENGINE (Cyberpunk & Gold Canvas Animation)
let themeCanvasCtx = null;
let themeCanvasW = 0, themeCanvasH = 0;
let liveParticles = [];
let animFrameId = null;

function initLiveThemeCanvas() {
    const canvas = document.getElementById('live-theme-canvas');
    if (!canvas) return;
    themeCanvasCtx = canvas.getContext('2d');

    function resize() {
        themeCanvasW = canvas.width = window.innerWidth;
        themeCanvasH = canvas.height = window.innerHeight;
        initParticlesForTheme();
    }
    window.addEventListener('resize', resize);
    resize();

    function loop() {
        renderLiveTheme(themeCanvasCtx, themeCanvasW, themeCanvasH);
        animFrameId = requestAnimationFrame(loop);
    }
    if (animFrameId) cancelAnimationFrame(animFrameId);
    animFrameId = requestAnimationFrame(loop);
}

function initParticlesForTheme() {
    liveParticles = [];
    const count = 35;
    for (let i = 0; i < count; i++) {
        liveParticles.push({
            x: Math.random() * themeCanvasW,
            y: Math.random() * themeCanvasH,
            radius: Math.random() * 2.5 + 1.2,
            vx: (Math.random() - 0.5) * 0.4,
            vy: -Math.random() * 0.6 - 0.2, // Drifting upwards
            alpha: Math.random() * 0.7 + 0.3,
            pulse: Math.random() * Math.PI * 2,
            pulseSpeed: Math.random() * 0.03 + 0.015
        });
    }
}

function renderLiveTheme(ctx, w, h) {
    if (!ctx || w === 0 || h === 0) return;
    ctx.clearRect(0, 0, w, h);

    const isCyberpunk = document.body.classList.contains('theme-cyberpunk');
    const isGold = document.body.classList.contains('theme-gold');

    if (isCyberpunk) {
        // Live Animated Cyberpunk: 3D perspective grid lines
        const horizonY = h * 0.62;
        ctx.save();

        // Vanishing point horizon glow
        const grad = ctx.createRadialGradient(w / 2, horizonY, 10, w / 2, horizonY, w * 0.75);
        grad.addColorStop(0, 'rgba(255, 0, 127, 0.25)');
        grad.addColorStop(0.5, 'rgba(0, 245, 255, 0.12)');
        grad.addColorStop(1, 'rgba(6, 2, 14, 0)');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, w, h);

        // Perspective lines radiating from horizon
        ctx.strokeStyle = 'rgba(0, 245, 255, 0.18)';
        ctx.lineWidth = 1;
        const lineCount = 14;
        for (let i = -lineCount; i <= lineCount; i++) {
            ctx.beginPath();
            ctx.moveTo(w / 2, horizonY);
            ctx.lineTo((w / 2) + i * (w / 9), h);
            ctx.stroke();
        }

        // Animated forward-moving horizontal grid lines
        const time = performance.now() * 0.0015;
        ctx.strokeStyle = 'rgba(255, 0, 127, 0.22)';
        for (let j = 0; j < 8; j++) {
            const progress = (time * 0.6 + j / 8) % 1;
            const y = horizonY + Math.pow(progress, 2.2) * (h - horizonY);
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(w, y);
            ctx.stroke();
        }

        // Digital cyber data bits
        liveParticles.forEach(p => {
            p.y += p.vy * 0.8;
            p.x += p.vx * 0.5;
            p.pulse += p.pulseSpeed;
            if (p.y < 0) p.y = h;
            if (p.x < 0) p.x = w;
            if (p.x > w) p.x = 0;

            const currentAlpha = p.alpha * (0.6 + 0.4 * Math.sin(p.pulse));
            ctx.fillStyle = (p.radius > 2.2) 
                ? `rgba(255, 0, 127, ${currentAlpha})` 
                : `rgba(0, 245, 255, ${currentAlpha})`;
            ctx.fillRect(p.x, p.y, p.radius * 1.5, p.radius * 1.5);
        });

        ctx.restore();
    } else if (isGold) {
        // Live Animated Gold: Shimmering warm champagne stardust and floating golden bokeh embers
        ctx.save();

        const goldAura = ctx.createRadialGradient(w / 2, h * 0.38, 20, w / 2, h * 0.38, w * 0.65);
        goldAura.addColorStop(0, 'rgba(255, 184, 0, 0.14)');
        goldAura.addColorStop(0.6, 'rgba(217, 119, 6, 0.05)');
        goldAura.addColorStop(1, 'rgba(8, 6, 3, 0)');
        ctx.fillStyle = goldAura;
        ctx.fillRect(0, 0, w, h);

        // Floating bokeh embers & stardust
        liveParticles.forEach(p => {
            p.y += p.vy * 0.7; // gently float upward
            p.x += Math.sin(p.pulse) * 0.35;
            p.pulse += p.pulseSpeed;
            if (p.y < -10) {
                p.y = h + 10;
                p.x = Math.random() * w;
            }

            const currentAlpha = p.alpha * (0.5 + 0.5 * Math.sin(p.pulse));
            const rad = p.radius * 2.8;
            const pGrad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, rad);
            pGrad.addColorStop(0, `rgba(255, 224, 130, ${currentAlpha})`);
            pGrad.addColorStop(0.4, `rgba(245, 158, 11, ${currentAlpha * 0.6})`);
            pGrad.addColorStop(1, 'rgba(245, 158, 11, 0)');

            ctx.fillStyle = pGrad;
            ctx.beginPath();
            ctx.arc(p.x, p.y, rad, 0, Math.PI * 2);
            ctx.fill();
        });

        ctx.restore();
    } else {
        // Starfield for Obsidian & Nord
        ctx.save();
        liveParticles.forEach(p => {
            p.pulse += p.pulseSpeed * 0.5;
            const currentAlpha = 0.25 + 0.2 * Math.sin(p.pulse);
            ctx.fillStyle = `rgba(255, 255, 255, ${currentAlpha})`;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.radius * 0.7, 0, Math.PI * 2);
            ctx.fill();
        });
        ctx.restore();
    }
}

// Theme Switcher
function setTheme(themeClass) {
    document.body.className = themeClass;
    document.querySelectorAll('.theme-btn').forEach(b => {
        if (b.getAttribute('onclick').includes(themeClass)) b.classList.add('active');
        else b.classList.remove('active');
    });
    initParticlesForTheme();
    const name = themeClass.replace('theme-', '');
    showToast(`Live Theme: ${name.charAt(0).toUpperCase() + name.slice(1)}`);
}

// Modals
function openTunnelModal() {
    document.getElementById('modal-title').innerText = 'Cloudflare Encrypted Outbound Tunnel';
    document.getElementById('modal-content').innerHTML = `
        <p><strong>Zero Port-Forwarding &bull; 100% Origin IP Obfuscation</strong></p>
        <p style="margin: 8px 0;">Public visitors access your modular website over an encrypted Cloudflare edge tunnel. Your ISP, home address, and home router firewall are completely masked.</p>
        <div style="background:#04060A; padding:8px; border-radius:6px; font-family:monospace; margin:8px 0; color:#38BDF8;">
            ${tunnelPublicUrl || 'https://omnihost-live.trycloudflare.com'}
        </div>
        <button class="action-btn primary" style="width:100%; margin-top:10px; justify-content:center;" onclick="toggleTunnelAction(); closeModal();">
            ${isTunnelActive ? '🛑 Stop Outbound Tunnel' : '🚀 Activate Outbound Tunnel'}
        </button>
    `;
    document.getElementById('modal-container').classList.add('open');
}

function openDnsModal() {
    document.getElementById('modal-title').innerText = 'Custom Domain DNS Wizard';
    document.getElementById('modal-content').innerHTML = `
        <p><strong>Step-by-Step DNS Guidance for Your Domain Registrar:</strong></p>
        <ul style="padding-left:18px; margin:8px 0; font-size:11px; line-height:1.6;">
            <li><strong>Namecheap:</strong> Advanced DNS -> Add CNAME Record -> Host: @ -> Value: [tunnel-id].cfargotunnel.com</li>
            <li><strong>GoDaddy:</strong> DNS Management -> Add CNAME Record -> Name: www -> Value: [tunnel-id].cfargotunnel.com</li>
            <li><strong>Porkbun:</strong> Details -> DNS Records -> CNAME -> Host: @</li>
            <li><strong>Squarespace:</strong> Settings -> Domains -> Advanced DNS Settings</li>
        </ul>
    `;
    document.getElementById('modal-container').classList.add('open');
}

function showProInfo() {
    document.getElementById('modal-title').innerText = 'OmniHost Pro Commercial License';
    document.getElementById('modal-content').innerHTML = `
        <div style="text-align:center; padding:10px 0;">
            <div style="font-size:32px;">👑</div>
            <h4 style="color:#F59E0B; margin:6px 0;">OMNIHOST PRO - FULL SUITE</h4>
            <p style="font-size:11px; color:#94A3B8;">All-in-One Modular Website &amp; High-Speed WiFi FTP Cloud Server</p>
            <p style="font-size:11px; margin-top:8px;">Licensed under the <strong>Alumungandr Master Charter</strong>.<br>Founder &amp; Chief Architect: <strong>David Anthony Jones ("Alu")</strong>.</p>
        </div>
    `;
    document.getElementById('modal-container').classList.add('open');
}

function closeModal() {
    document.getElementById('modal-container').classList.remove('open');
}

document.addEventListener('DOMContentLoaded', initApp);
