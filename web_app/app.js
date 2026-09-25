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
let currentBatteryPct = 100;
let isDeviceCharging = false;

let dataLimitMb = 0;
const dataOptions = [0, 100, 500, 1024, 5120];
let dataIndex = 0;

// Bridge Wrapper
const hasNativeBridge = typeof window.OmniHostBridge !== 'undefined';

function initApp() {
    setupDeviceState();
    initLiveThemeCanvas();
    initPowerShape();
    initBlackHole();
    pollTelemetry();
    pollTunnelStatus();
    setInterval(pollTelemetry, 1000); // 1-second ultra-responsive live telemetry & battery refresh
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
            if (dev.batteryLevel !== undefined) currentBatteryPct = dev.batteryLevel;
            if (dev.isCharging !== undefined) isDeviceCharging = dev.isCharging;
            updateBatteryCardUI();
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
        initWebBatteryApi();
    }
}

// Called by Android MainActivity
window.onHostStateSync = function(state) {
    if (state.lanIp) lanIp = state.lanIp;
    if (state.activeSite) activeSite = state.activeSite;
    if (state.httpRunning !== undefined) isServersRunning = state.httpRunning;
    if (state.tunnelActive !== undefined) isTunnelActive = state.tunnelActive;
    if (state.tunnelUrl !== undefined) tunnelPublicUrl = state.tunnelUrl;
    if (state.batteryLevel !== undefined) currentBatteryPct = state.batteryLevel;
    if (state.isCharging !== undefined) isDeviceCharging = state.isCharging;
    updateBatteryCardUI();
    checkBatteryLimitEnforcement();
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
    const elWebdav = document.getElementById('display-webdav-url');
    const elFtpFull = document.getElementById('ftp-full-url');
    const elFtpGuide = document.getElementById('ftp-guide-url');
    const elWebdavStatus = document.getElementById('webdav-status-url');
    const elWebdavGuide = document.getElementById('webdav-guide-url');
    const elFtpStatus = document.getElementById('ftp-status-url');
    const elSiteTag = document.getElementById('current-site-tag');

    const topDot = document.getElementById('top-live-dot');
    const trayDot = document.getElementById('tray-dot-power');
    const trayNote = document.getElementById('tray-note-power');

    if (!isServersRunning) {
        if (elWeb) elWeb.innerText = "● Offline — Tap Power to Start";
        if (elFtp) elFtp.innerText = "● Offline — Tap Power to Start";
        if (elExplorer) elExplorer.innerText = "● Offline — Tap Power to Start";
        if (elWebdav) elWebdav.innerText = "● Offline — Tap Power to Start";
        if (elFtpFull) elFtpFull.innerText = "● Offline — Tap Power to Start";
        if (elFtpGuide) elFtpGuide.innerText = `ftp://${lanIp}:2121 (Offline)`;
        if (elWebdavStatus) elWebdavStatus.innerText = `http://${lanIp}:8090/webdav (Offline)`;
        if (elWebdavGuide) elWebdavGuide.innerText = `http://${lanIp}:8090/webdav (Offline)`;
        if (elFtpStatus) elFtpStatus.innerText = `ftp://${lanIp}:2121 (Offline)`;

        if (topDot) { topDot.classList.remove('online'); topDot.classList.add('offline'); }
        if (trayDot) { trayDot.classList.remove('online'); trayDot.classList.add('offline'); }
        if (trayNote) trayNote.innerText = "Offline";
    } else {
        const webUrl = `http://${lanIp}:8090`;
        const ftpUrl = `ftp://${lanIp}:2121`;
        const explorerUrl = `http://${lanIp}:8090/files`;
        const webdavUrl = `http://${lanIp}:8090/webdav`;

        if (elWeb) elWeb.innerText = webUrl;
        if (elFtp) elFtp.innerText = ftpUrl;
        if (elExplorer) elExplorer.innerText = explorerUrl;
        if (elWebdav) elWebdav.innerText = webdavUrl;
        if (elFtpFull) elFtpFull.innerText = ftpUrl;
        if (elFtpGuide) elFtpGuide.innerText = ftpUrl;
        if (elWebdavStatus) elWebdavStatus.innerText = webdavUrl;
        if (elWebdavGuide) elWebdavGuide.innerText = webdavUrl;
        if (elFtpStatus) elFtpStatus.innerText = ftpUrl;

        if (topDot) { topDot.classList.remove('offline'); topDot.classList.add('online'); }
        if (trayDot) { trayDot.classList.remove('offline'); trayDot.classList.add('online'); }
        if (trayNote) trayNote.innerText = "Online";
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

    const trayDotTunnel = document.getElementById('tray-dot-tunnel');
    const trayNoteTunnel = document.getElementById('tray-note-tunnel');

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
        if (trayDotTunnel) {
            trayDotTunnel.classList.remove('standby');
            trayDotTunnel.classList.add('online');
        }
        if (trayNoteTunnel) {
            trayNoteTunnel.innerText = "Live";
        }
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
        if (trayDotTunnel) {
            trayDotTunnel.classList.remove('online');
            trayDotTunnel.classList.add('standby');
        }
        if (trayNoteTunnel) {
            trayNoteTunnel.innerText = "Standby";
        }
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
    if (typeof triggerBlackHoleWave === 'function') {
        triggerBlackHoleWave();
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
// 3 Limits Interactive Bottom Sheet Modal
let currentLimitsModalType = 'timer';
let currentLimitsModalVal = 30;

function openLimitsModal(type) {
    currentLimitsModalType = type;
    const container = document.getElementById('limits-modal-container');
    const titleEl = document.getElementById('limits-modal-title');
    const subEl = document.getElementById('limits-modal-desc') || document.getElementById('limits-modal-sub');
    const valEl = document.getElementById('limits-current-val-text') || document.getElementById('limits-modal-val-display');
    const slider = document.getElementById('limits-range-slider') || document.getElementById('limits-modal-slider');
    const presetsRow = document.getElementById('limits-presets-container') || document.getElementById('limits-presets-row');

    let presets = [];
    if (type === 'timer') {
        if (titleEl) titleEl.innerText = "⏱️ Set Auto-Stop Timer";
        if (subEl) subEl.innerText = "Automatically stops sharing when time runs out";
        if (slider) {
            slider.min = "5";
            slider.max = "240";
            slider.step = "5";
        }
        currentLimitsModalVal = timerLimitMin > 0 ? timerLimitMin : 30;
        presets = [15, 30, 60, 120];
    } else if (type === 'battery') {
        if (titleEl) titleEl.innerText = "🔋 Battery Guard";
        if (subEl) subEl.innerText = `Stops sharing when battery drops to this level (Live: ${currentBatteryPct}%)`;
        if (slider) {
            slider.min = "10";
            slider.max = "50";
            slider.step = "5";
        }
        currentLimitsModalVal = batteryLimitPct > 0 ? batteryLimitPct : 20;
        presets = [15, 20, 25, 30];
    } else if (type === 'data') {
        if (titleEl) titleEl.innerText = "📊 Data Allowance";
        if (subEl) subEl.innerText = "Stops sharing after this amount of traffic is transferred";
        if (slider) {
            slider.min = "50";
            slider.max = "5120";
            slider.step = "50";
        }
        currentLimitsModalVal = dataLimitMb > 0 ? dataLimitMb : 500;
        presets = [100, 500, 1024, 2048];
    }

    if (slider) slider.value = currentLimitsModalVal;
    updateLimitsDisplayVal(valEl);

    if (presetsRow) {
        presetsRow.innerHTML = '';
        presets.forEach(p => {
            const btn = document.createElement('button');
            btn.className = 'limits-preset-btn' + (p === currentLimitsModalVal ? ' active' : '');
            let label = p;
            if (type === 'timer') label = `${p}m`;
            else if (type === 'battery') label = `${p}%`;
            else if (type === 'data') label = p >= 1024 ? `${p / 1024}G` : `${p}M`;
            btn.innerText = label;
            btn.onclick = () => setLimitPreset(p);
            presetsRow.appendChild(btn);
        });
    }

    if (container) {
        container.classList.add('open');
        container.style.display = 'flex';
    }
}

function updateLimitsDisplayVal(valEl) {
    if (!valEl) valEl = document.getElementById('limits-current-val-text') || document.getElementById('limits-modal-val-display');
    if (!valEl) return;
    let label = `${currentLimitsModalVal} min`;
    if (currentLimitsModalType === 'battery') label = `${currentLimitsModalVal}%`;
    else if (currentLimitsModalType === 'data') label = currentLimitsModalVal >= 1024 ? `${currentLimitsModalVal / 1024} GB` : `${currentLimitsModalVal} MB`;
    valEl.innerText = label;
}

function onLimitsSliderInput(val) {
    currentLimitsModalVal = parseInt(val, 10);
    updateLimitsDisplayVal();
    updateActivePresetBtn();
}

function setLimitPreset(val) {
    currentLimitsModalVal = parseInt(val, 10);
    const slider = document.getElementById('limits-range-slider') || document.getElementById('limits-modal-slider');
    if (slider) slider.value = currentLimitsModalVal;
    updateLimitsDisplayVal();
    updateActivePresetBtn();
}

function updateActivePresetBtn() {
    const presetsRow = document.getElementById('limits-presets-row');
    if (!presetsRow) return;
    const children = Array.from(presetsRow.children);
    children.forEach(b => {
        const txt = b.innerText.replace(/[^0-9]/g, '');
        if (parseInt(txt, 10) === currentLimitsModalVal) {
            b.classList.add('active');
        } else {
            b.classList.remove('active');
        }
    });
}

function applyLimitsFromModal() {
    if (currentLimitsModalType === 'timer') {
        timerLimitMin = currentLimitsModalVal;
        const el = document.getElementById('limit-timer-val');
        if (el) el.innerText = `${timerLimitMin} min`;
        showToast(`⏱️ Auto-Off Timer set to ${timerLimitMin} min`);
    } else if (currentLimitsModalType === 'battery') {
        batteryLimitPct = currentLimitsModalVal;
        updateBatteryCardUI();
        checkBatteryLimitEnforcement();
        showToast(`🔋 Battery Guard set to ${batteryLimitPct}%`);
    } else if (currentLimitsModalType === 'data') {
        dataLimitMb = currentLimitsModalVal;
        const el = document.getElementById('limit-data-val');
        if (el) {
            el.innerText = dataLimitMb >= 1024 ? `${dataLimitMb / 1024} GB` : `${dataLimitMb} MB`;
        }
        showToast(`📊 Data Limit set to ${dataLimitMb >= 1024 ? (dataLimitMb / 1024) + ' GB' : dataLimitMb + ' MB'}`);
    }
    pushLimitsToBridge();
    closeLimitsModal();
}

function disableLimitFromModal() {
    if (currentLimitsModalType === 'timer') {
        timerLimitMin = 0;
        const el = document.getElementById('limit-timer-val');
        if (el) el.innerText = 'Disabled';
        showToast('⏱️ Auto-Off Timer: Disabled');
    } else if (currentLimitsModalType === 'battery') {
        batteryLimitPct = 0;
        updateBatteryCardUI();
        showToast('🔋 Battery Guard: Disabled');
    } else if (currentLimitsModalType === 'data') {
        dataLimitMb = 0;
        const el = document.getElementById('limit-data-val');
        if (el) el.innerText = 'Disabled';
        showToast('📊 Data Allowance: Disabled');
    }
    pushLimitsToBridge();
    closeLimitsModal();
}

function closeLimitsModal() {
    const container = document.getElementById('limits-modal-container');
    if (container) {
        container.classList.remove('open');
        container.style.display = 'none';
    }
}

function updateBatteryCardUI() {
    const el = document.getElementById('limit-battery-val');
    if (!el) return;
    const chargeIcon = isDeviceCharging ? '⚡' : '';
    if (batteryLimitPct === 0) {
        el.innerHTML = `Disabled <span style="font-size:9px; color:var(--text-dim); display:block; margin-top:2px;">Live: ${currentBatteryPct}% ${chargeIcon}</span>`;
    } else {
        el.innerHTML = `<span style="color:#10B981; font-weight:700;">${batteryLimitPct}%</span> <span style="font-size:9px; color:var(--text-dim); display:block; margin-top:2px;">Live: ${currentBatteryPct}% ${chargeIcon}</span>`;
    }
}

function checkBatteryLimitEnforcement() {
    if (batteryLimitPct > 0 && isServersRunning && !isDeviceCharging) {
        if (currentBatteryPct <= batteryLimitPct) {
            toggleMasterPower();
            showToast(`🛑 Battery dropped to ${currentBatteryPct}% (Limit: ${batteryLimitPct}%). Servers stopped to save battery!`);
        }
    }
}

function initWebBatteryApi() {
    if (!hasNativeBridge && typeof navigator !== 'undefined' && navigator.getBattery) {
        navigator.getBattery().then(battery => {
            currentBatteryPct = Math.round(battery.level * 100);
            isDeviceCharging = battery.charging;
            updateBatteryCardUI();

            battery.addEventListener('levelchange', () => {
                currentBatteryPct = Math.round(battery.level * 100);
                updateBatteryCardUI();
                checkBatteryLimitEnforcement();
            });
            battery.addEventListener('chargingchange', () => {
                isDeviceCharging = battery.charging;
                updateBatteryCardUI();
            });
        }).catch(() => {});
    }
}

function pushLimitsToBridge() {
    if (hasNativeBridge && window.OmniHostBridge.setLimits) {
        window.OmniHostBridge.setLimits(timerLimitMin, batteryLimitPct, dataLimitMb);
    }
}

// Navigation Tabs (5 Clean Tabs)
function selectTab(tabId) {
    currentTab = tabId;
    document.querySelectorAll('.tab-view').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));

    const tabEl = document.getElementById(`tab-${tabId}`);
    if (tabEl) tabEl.classList.add('active');

    const navBtn = document.getElementById(`nav-${tabId}`);
    if (navBtn) navBtn.classList.add('active');

    const titleMap = {
        'hotspot': 'OmniHost Pro',
        'sites': 'Modular Sites',
        'ftp': 'WiFi FTP Server',
        'speed': 'Speed Test',
        'data': 'Data Usage'
    };
    const titleEl = document.getElementById('top-bar-title');
    if (titleEl && titleMap[tabId]) titleEl.innerText = titleMap[tabId];

    const backBtn = document.getElementById('top-bar-back-btn');
    if (backBtn) {
        backBtn.style.display = (tabId === 'hotspot') ? 'none' : 'inline-flex';
    }

    if (tabId === 'sites') {
        previewSite(activeSite);
    }
}

function getWebDavUrl() {
    return isServersRunning ? `http://${lanIp}:8090/webdav` : `http://${lanIp}:8090/webdav (Offline)`;
}

function copyWebDavUrl() {
    if (!isServersRunning) {
        showToast("Server is offline — tap Power to start");
        return;
    }
    const url = `http://${lanIp}:8090/webdav`;
    copyValueText(url, "WebDAV Cloud Drive URL copied!");
    showQrModal('WebDAV Cloud Drive (RFC 4918)', url, 'URL copied! Mount phone storage as a local hard drive on Windows (Map Network Drive), macOS (Finder Cmd+K), or Solid Explorer.');
}

function copyAllEndpoints() {
    if (!isServersRunning) {
        showToast("Server is offline — tap Power to start");
        return;
    }
    const text = `OmniHost Pro Endpoints:\n` +
                 `• Website: http://${lanIp}:8090/\n` +
                 `• GalaxSee Hub: http://${lanIp}:8090/files\n` +
                 `• WebDAV Cloud Drive: http://${lanIp}:8090/webdav\n` +
                 `• WiFi FTP: ftp://${lanIp}:2121\n` +
                 (isTunnelActive && tunnelPublicUrl ? `• Public HTTPS: ${tunnelPublicUrl}\n` : '');
    copyValueText(text, "All Server Endpoints copied!");
}

function copyValueText(text, successMsg) {
    if (hasNativeBridge && window.OmniHostBridge.copyToClipboard) {
        window.OmniHostBridge.copyToClipboard(text);
        showToast(successMsg || ("Copied: " + text));
    } else if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showToast(successMsg || ("Copied: " + text));
        }).catch(() => {
            showToast("Copied: " + text);
        });
    } else {
        showToast(successMsg || ("Copied: " + text));
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
    if (!isServersRunning) {
        showToast("Server is offline — tap Power to start");
        return;
    }
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

// Real-World Speedometer & Bandwidth Engine
let currentSpeedTestMode = 'wan';

function setSpeedTestMode(mode) {
    currentSpeedTestMode = (mode === 'lan') ? 'lan' : 'wan';
    const btnWan = document.getElementById('btn-mode-wan');
    const btnLan = document.getElementById('btn-mode-lan');
    const serverName = document.getElementById('speed-server-name');
    const ratingText = document.getElementById('speed-rating-text');

    if (btnWan && btnLan) {
        if (currentSpeedTestMode === 'wan') {
            btnWan.classList.add('active');
            btnLan.classList.remove('active');
            if (serverName) serverName.innerText = 'Cloudflare Global Edge Network';
            if (ratingText) ratingText.innerText = 'Tap "Run Network Speed Test" to benchmark real Internet speed.';
        } else {
            btnLan.classList.add('active');
            btnWan.classList.remove('active');
            if (serverName) serverName.innerText = 'OmniHost Local Server (:8090)';
            if (ratingText) ratingText.innerText = 'Tap "Run Network Speed Test" to benchmark local WiFi / device bus throughput.';
        }
    }
    resetSpeedTestUI();
}

function resetSpeedTestUI() {
    const num = document.getElementById('gauge-speed-val');
    if (num) num.innerText = '0.0';
    updateGaugeFill(0);
    const ping = document.getElementById('speed-ping');
    if (ping) ping.innerText = '-- ms';
    const jitter = document.getElementById('speed-jitter');
    if (jitter) jitter.innerText = '-- ms';
    const down = document.getElementById('speed-down');
    if (down) down.innerText = '-- Mbps';
    const up = document.getElementById('speed-up');
    if (up) up.innerText = '-- Mbps';
}

function updateGaugeFill(mbps) {
    const ring = document.getElementById('gauge-ring');
    if (!ring) return;
    let maxScale = 100;
    if (mbps > 500) maxScale = 1000;
    else if (mbps > 200) maxScale = 500;
    else if (mbps > 100) maxScale = 200;

    const pct = Math.min(1, Math.max(0.02, mbps / maxScale));
    const deg = Math.round(pct * 360);
    ring.style.background = `conic-gradient(var(--primary) 0deg, var(--accent-cyan) ${deg}deg, rgba(255, 255, 255, 0.08) ${deg}deg 360deg)`;
}

window.onSpeedTestProgress = function(p) {
    if (!p) return;
    const num = document.getElementById('gauge-speed-val');
    if (num && p.currentMbps !== undefined && p.currentMbps > 0) {
        num.innerText = p.currentMbps.toFixed(1);
        updateGaugeFill(p.currentMbps);
    }
    if (p.pingMs > 0) {
        const ping = document.getElementById('speed-ping');
        if (ping) ping.innerText = `${p.pingMs} ms`;
    }
    if (p.jitterMs > 0) {
        const jitter = document.getElementById('speed-jitter');
        if (jitter) jitter.innerText = `${p.jitterMs} ms`;
    }
    if (p.downloadMbps > 0) {
        const down = document.getElementById('speed-down');
        if (down) down.innerText = `${p.downloadMbps.toFixed(1)} Mbps`;
    }
    if (p.server) {
        const server = document.getElementById('speed-server-name');
        if (server) server.innerText = p.server;
    }
    if (p.statusText) {
        const rating = document.getElementById('speed-rating-text');
        if (rating) rating.innerText = p.statusText;
    }
};

window.onSpeedTestResult = function(res) {
    const btn = document.getElementById('btn-run-speed-test');
    if (btn) btn.disabled = false;

    const num = document.getElementById('gauge-speed-val');
    if (num) num.innerText = res.downloadMbps.toFixed(1);
    updateGaugeFill(res.downloadMbps);

    const ping = document.getElementById('speed-ping');
    if (ping) ping.innerText = `${res.pingMs} ms`;

    const jitter = document.getElementById('speed-jitter');
    if (jitter) jitter.innerText = `${res.jitterMs} ms`;

    const down = document.getElementById('speed-down');
    if (down) down.innerText = `${res.downloadMbps.toFixed(1)} Mbps`;

    const up = document.getElementById('speed-up');
    if (up) up.innerText = `${res.uploadMbps.toFixed(1)} Mbps`;

    const rating = document.getElementById('speed-rating-text');
    if (rating) rating.innerText = res.rating;

    const server = document.getElementById('speed-server-name');
    if (server && res.server) server.innerText = res.server;

    const icon = document.getElementById('speed-rating-icon');
    if (icon) icon.innerText = res.isOffline ? '🏠' : (res.downloadMbps > 50 ? '⚡' : '🚀');
};

async function startSpeedTest() {
    const btn = document.getElementById('btn-run-speed-test');
    if (btn) btn.disabled = true;

    resetSpeedTestUI();
    const ratingEl = document.getElementById('speed-rating-text');
    if (ratingEl) ratingEl.innerText = `Connecting to ${currentSpeedTestMode === 'wan' ? 'Cloudflare Edge' : 'Local Server'}...`;

    // 1. Android Native Execution (Hardware socket streaming)
    if (hasNativeBridge && window.OmniHostBridge && window.OmniHostBridge.runSpeedTest) {
        try {
            window.OmniHostBridge.runSpeedTest(currentSpeedTestMode);
            return;
        } catch (e) {
            console.warn("Native speed test failed, falling back to JS:", e);
        }
    }

    // 2. Pure Web Browser Fallback (ReadableStream & XHR Progress)
    try {
        if (currentSpeedTestMode === 'wan') {
            // Step A: Latency & Colo Trace
            let serverColo = "Cloudflare Global Edge";
            const pings = [];
            for (let i = 0; i < 3; i++) {
                const t0 = performance.now();
                const res = await fetch(`https://cloudflare.com/cdn-cgi/trace?t=${Date.now()}`, { cache: 'no-store' });
                const text = await res.text();
                pings.push(performance.now() - t0);
                if (i === 0) {
                    const match = text.match(/colo=([A-Z0-9]+)/);
                    if (match) serverColo = `Cloudflare Edge (${match[1]})`;
                }
                const curPing = Math.round(pings.reduce((a, b) => a + b, 0) / pings.length);
                window.onSpeedTestProgress({
                    phase: 'ping',
                    pingMs: curPing,
                    jitterMs: 0,
                    server: serverColo,
                    statusText: `Pinging ${serverColo}...`
                });
                await new Promise(r => setTimeout(r, 60));
            }
            const avgPing = Math.round(pings.reduce((a, b) => a + b, 0) / pings.length);
            const jitter = Math.round(Math.abs(pings[1] - pings[0]) + Math.abs(pings[2] - pings[1])) / 2;

            // Step B: Real Download Streaming (5MB)
            const downUrl = `https://speed.cloudflare.com/__down?bytes=5000000&t=${Date.now()}`;
            const dlRes = await fetch(downUrl, { cache: 'no-store' });
            if (!dlRes.ok) throw new Error("Cloudflare unreachable");
            const reader = dlRes.body.getReader();
            let totalDown = 0;
            const downStart = performance.now();
            let lastDownUpdate = downStart;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                totalDown += value.length;
                const now = performance.now();
                if (now - lastDownUpdate > 80 && (now - downStart) > 100) {
                    const curMbps = parseFloat(((totalDown * 8) / ((now - downStart) / 1000 * 1000000)).toFixed(1));
                    window.onSpeedTestProgress({
                        phase: 'download',
                        currentMbps: curMbps,
                        pingMs: avgPing,
                        jitterMs: Math.round(jitter),
                        server: serverColo,
                        statusText: `Testing Real Download: ${curMbps} Mbps...`
                    });
                    lastDownUpdate = now;
                }
            }
            const downDuration = (performance.now() - downStart) / 1000;
            const dlMbps = parseFloat(((totalDown * 8) / (downDuration * 1000000)).toFixed(1));

            // Step C: Real Upload (1.5MB)
            const uploadBytes = new Uint8Array(1572864);
            uploadBytes.fill(0xAA);
            const upStart = performance.now();
            let lastUpUpdate = upStart;

            await new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                xhr.open('POST', `https://speed.cloudflare.com/__up?t=${Date.now()}`);
                xhr.upload.onprogress = (e) => {
                    const now = performance.now();
                    if (now - lastUpUpdate > 80 && e.loaded > 0) {
                        const curUpMbps = parseFloat(((e.loaded * 8) / ((now - upStart) / 1000 * 1000000)).toFixed(1));
                        window.onSpeedTestProgress({
                            phase: 'upload',
                            currentMbps: curUpMbps,
                            pingMs: avgPing,
                            jitterMs: Math.round(jitter),
                            downloadMbps: dlMbps,
                            server: serverColo,
                            statusText: `Testing Real Upload: ${curUpMbps} Mbps...`
                        });
                        lastUpUpdate = now;
                    }
                };
                xhr.onload = () => resolve();
                xhr.onerror = () => reject(new Error("Upload failed"));
                xhr.send(uploadBytes);
            });
            const upDuration = (performance.now() - upStart) / 1000;
            const ulMbps = parseFloat(((uploadBytes.byteLength * 8) / (upDuration * 1000000)).toFixed(1));

            let rating = dlMbps >= 100 ? '⚡ Gigabit/Fiber Grade — Ultra-Fast Stream & Server Hosting'
                       : dlMbps >= 50 ? '🚀 High-Speed Broadband — Excellent for Multi-Client Serving'
                       : dlMbps >= 20 ? '🌐 Solid Broadband — Seamless Web Hosting & Cloud Sync'
                       : dlMbps >= 5 ? '📶 Moderate Connection — Standard Web Serving'
                       : '⚠️ Low-Bandwidth Link — Limited Server Throughput';

            window.onSpeedTestResult({
                mode: 'wan',
                pingMs: avgPing,
                jitterMs: Math.round(jitter),
                downloadMbps: dlMbps,
                uploadMbps: ulMbps,
                server: serverColo,
                rating: rating,
                isOffline: false
            });
        } else {
            // Local LAN Benchmark against :8090
            const pings = [];
            for (let i = 0; i < 3; i++) {
                const t0 = performance.now();
                await fetch(`${API_BASE}/api/speedtest/ping?t=${Date.now()}`);
                pings.push(performance.now() - t0);
            }
            const avgPing = Math.round(pings.reduce((a, b) => a + b, 0) / pings.length);
            const jitter = 1;

            const d0 = performance.now();
            const dlRes = await fetch(`${API_BASE}/api/speedtest/download?size=4194304&t=${Date.now()}`);
            const dlBuf = await dlRes.arrayBuffer();
            const dDuration = (performance.now() - d0) / 1000;
            const dlMbps = parseFloat(((dlBuf.byteLength * 8) / (dDuration * 1000000)).toFixed(1));

            const uploadBytes = new Uint8Array(2097152);
            const u0 = performance.now();
            await fetch(`${API_BASE}/api/speedtest/upload`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/octet-stream' },
                body: uploadBytes
            });
            const uDuration = (performance.now() - u0) / 1000;
            const ulMbps = parseFloat(((uploadBytes.byteLength * 8) / (uDuration * 1000000)).toFixed(1));

            window.onSpeedTestResult({
                mode: 'lan',
                pingMs: avgPing,
                jitterMs: jitter,
                downloadMbps: dlMbps,
                uploadMbps: ulMbps,
                server: 'OmniHost Local Engine (:8090)',
                rating: '🏠 Local WiFi / Device Bus Throughput (Direct LAN Benchmark)',
                isOffline: false
            });
        }
    } catch (e) {
        console.error("Speedtest error:", e);
        if (btn) btn.disabled = false;
        if (ratingEl) ratingEl.innerText = "Network Error: Could not reach edge server. Check internet connection.";
    }
}

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

    if (data.batteryLevel !== undefined) currentBatteryPct = data.batteryLevel;
    if (data.isCharging !== undefined) isDeviceCharging = data.isCharging;
    updateBatteryCardUI();
    checkBatteryLimitEnforcement();

    const batEl = document.getElementById('telemetry-battery-val');
    if (batEl) batEl.innerText = `${currentBatteryPct}%`;

    const chgEl = document.getElementById('telemetry-charging-val');
    if (chgEl) chgEl.innerText = isDeviceCharging ? 'Charging (AC/USB) ⚡' : 'Running on Battery 🔋';

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

// Service Card Action Strips & QR Code Modals
let currentQrUrl = '';

function copyServiceUrl(type) {
    let url = '';
    if (type === 'http') {
        url = `http://${lanIp}:8090`;
    } else if (type === 'drop') {
        url = `http://${lanIp}:8090/file_manager.html`;
    } else if (type === 'ftp') {
        url = `ftp://${lanIp}:2121`;
    }
    if (!url) return;
    if (hasNativeBridge && window.OmniHostBridge.copyToClipboard) {
        window.OmniHostBridge.copyToClipboard(url);
        showToast("Copied to clipboard: " + url);
    } else if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(() => {
            showToast("Copied to clipboard: " + url);
        }).catch(() => {
            showToast("Copied: " + url);
        });
    } else {
        showToast("Copied: " + url);
    }
}

function openExternalUrl(type) {
    let url = '';
    if (type === 'http') {
        url = `http://${lanIp}:8090`;
    } else if (type === 'drop') {
        url = `http://${lanIp}:8090/file_manager.html`;
    } else if (type === 'ftp') {
        url = `ftp://${lanIp}:2121`;
    }
    if (!url) return;
    window.open(url, '_blank');
}

function getWebUrl() {
    return `http://${lanIp}:8090`;
}

function getFtpUrl() {
    return `ftp://${lanIp}:2121`;
}

function getExplorerUrl() {
    return `http://${lanIp}:8090/files`;
}

function getDropUrl() {
    return `http://${lanIp}:8090/file_manager.html`;
}

function showFtpQr() {
    showQrModal('Wireless File Drop', getFtpUrl(), 'Connect from your PC, Mac, or phone wirelessly.');
}

function showHttpQr() {
    showQrModal('Personal Web Link', getWebUrl(), 'Point any phone or computer camera to open your hosted website immediately.');
}

function showDropQr() {
    const url = `http://${lanIp}:8090/file_manager.html`;
    showQrModal('Wireless File Drop', url, 'Scan to send or download photos, videos, and files directly to this phone.');
}

function showQrModal(title, url, tip) {
    currentQrUrl = url;
    const container = document.getElementById('qr-modal-container');
    const titleEl = document.getElementById('qr-modal-title');
    const canvasWrap = document.getElementById('qr-code-mount') || document.getElementById('qr-modal-canvas-wrap');
    const urlEl = document.getElementById('qr-modal-url');
    const tipEl = document.getElementById('qr-modal-instructions') || document.getElementById('qr-modal-tip');

    if (titleEl) titleEl.innerText = `📱 ${title}`;
    if (urlEl) urlEl.innerText = url;
    if (tipEl && tip) tipEl.innerText = tip;

    if (canvasWrap) {
        canvasWrap.innerHTML = '';
        if (window.QRCode && window.QRCode.toString) {
            window.QRCode.toString(url, { type: 'svg', margin: 1 }, function(err, svgString) {
                if (!err && svgString) {
                    canvasWrap.innerHTML = svgString;
                } else {
                    canvasWrap.innerText = 'QR Error: ' + (err || 'Failed to render');
                }
            });
        } else {
            canvasWrap.innerText = 'QR Generator Loading...';
        }
    }

    if (container) {
        container.classList.add('open');
        container.style.display = 'flex';
    }
}

function closeQrModal() {
    const container = document.getElementById('qr-modal-container');
    if (container) {
        container.classList.remove('open');
        container.style.display = 'none';
    }
}

function copyQrUrl() {
    if (!currentQrUrl) return;
    if (hasNativeBridge && window.OmniHostBridge.copyToClipboard) {
        window.OmniHostBridge.copyToClipboard(currentQrUrl);
        showToast("Copied to clipboard: " + currentQrUrl);
    } else if (navigator.clipboard) {
        navigator.clipboard.writeText(currentQrUrl).then(() => {
            showToast("Copied to clipboard: " + currentQrUrl);
        }).catch(() => {
            showToast("Copied: " + currentQrUrl);
        });
    } else {
        showToast("Copied: " + currentQrUrl);
    }
}

function shareQrUrl() {
    if (!currentQrUrl) return;
    if (navigator.share) {
        navigator.share({
            title: 'OmniHost Connect',
            text: 'Connect to my shared OmniHost link:',
            url: currentQrUrl
        }).catch(() => {});
    } else if (hasNativeBridge && window.OmniHostBridge.shareText) {
        window.OmniHostBridge.shareText(currentQrUrl);
    } else {
        copyQrUrl();
    }
}

function shareFtpInfo() {
    const info = `OmniHost Pro FTP Server\nHost: ftp://${lanIp}:2121\nPort: 2121\nMode: Anonymous / Full Read & Write`;
    if (navigator.share) {
        navigator.share({
            title: 'OmniHost FTP Access',
            text: info
        }).catch(() => {});
    } else if (hasNativeBridge && window.OmniHostBridge.shareText) {
        window.OmniHostBridge.shareText(info);
    } else if (navigator.clipboard) {
        navigator.clipboard.writeText(info).then(() => {
            showToast("FTP info copied to clipboard");
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

// ==============================================================================
// LIVE BLACK HOLE ENGINE (Relativistic Accretion, Photon Ring & Gravitational Lensing)
// Responsive to Themes & State (Active Server Vortex vs. Quiescent Void)
// ==============================================================================
let blackholeCanvas = null;
let blackholeCtx = null;
let blackholeAnimId = null;
let blackholeParticles = [];
let blackholeWave = { radius: 0, maxRadius: 130, alpha: 0, speed: 4 };

function initBlackHole() {
    blackholeCanvas = document.getElementById('blackhole-canvas');
    if (!blackholeCanvas) return;
    blackholeCtx = blackholeCanvas.getContext('2d');

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const size = 260;
    blackholeCanvas.width = size * dpr;
    blackholeCanvas.height = size * dpr;
    blackholeCtx.scale(dpr, dpr);

    initBlackHoleParticles();

    if (blackholeAnimId) cancelAnimationFrame(blackholeAnimId);
    let lastTime = performance.now();
    function loop(now) {
        const dt = Math.min((now - lastTime) / 1000, 0.1);
        lastTime = now;
        renderBlackHole(blackholeCtx, size, size, dt);
        blackholeAnimId = requestAnimationFrame(loop);
    }
    blackholeAnimId = requestAnimationFrame(loop);
}

function initBlackHoleParticles() {
    blackholeParticles = [];
    const count = 135;
    const rMin = 34;
    const rMax = 124;
    for (let i = 0; i < count; i++) {
        const u = Math.random();
        const r = rMin + (rMax - rMin) * Math.pow(u, 1.6);
        const angle = Math.random() * Math.PI * 2;
        blackholeParticles.push({
            r: r,
            angle: angle,
            size: Math.random() * 1.8 + 0.9,
            speedFactor: Math.random() * 0.35 + 0.85,
            infallRate: Math.random() * 0.09 + 0.02,
            alpha: Math.random() * 0.6 + 0.35,
            colorIdx: Math.floor(Math.random() * 5),
            history: []
        });
    }
}

function triggerBlackHoleWave() {
    blackholeWave.radius = 28;
    blackholeWave.alpha = 1.0;
}

function getBlackHolePalette() {
    const body = document.body;
    if (body.classList.contains('theme-cyberpunk')) {
        return {
            photonGlow: '#00F5FF',
            photonCore: '#FFFFFF',
            lensingColor: 'rgba(0, 245, 255, 0.38)',
            lensingGlow: 'rgba(255, 0, 127, 0.28)',
            colors: ['#00F5FF', '#FF007F', '#FFE600', '#D946EF', '#FFFFFF'],
            jetColor: 'rgba(0, 245, 255, 0.65)',
            jetGlow: 'rgba(255, 0, 127, 0.45)',
            ambientGlow: 'rgba(0, 245, 255, 0.18)'
        };
    } else if (body.classList.contains('theme-gold')) {
        return {
            photonGlow: '#FFB800',
            photonCore: '#FFFDF0',
            lensingColor: 'rgba(255, 184, 0, 0.42)',
            lensingGlow: 'rgba(245, 158, 11, 0.32)',
            colors: ['#FFB800', '#F59E0B', '#EF4444', '#FDE047', '#FFFFFF'],
            jetColor: 'rgba(255, 184, 0, 0.75)',
            jetGlow: 'rgba(245, 158, 11, 0.5)',
            ambientGlow: 'rgba(245, 158, 11, 0.2)'
        };
    } else if (body.classList.contains('theme-nord')) {
        return {
            photonGlow: '#38BDF8',
            photonCore: '#ECEFF4',
            lensingColor: 'rgba(56, 189, 248, 0.35)',
            lensingGlow: 'rgba(136, 192, 208, 0.25)',
            colors: ['#88C0D0', '#81A1C1', '#38BDF8', '#E5E9F0', '#FFFFFF'],
            jetColor: 'rgba(56, 189, 248, 0.65)',
            jetGlow: 'rgba(136, 192, 208, 0.4)',
            ambientGlow: 'rgba(56, 189, 248, 0.16)'
        };
    } else if (body.classList.contains('theme-slate')) {
        return {
            photonGlow: '#E4E4E7',
            photonCore: '#FFFFFF',
            lensingColor: 'rgba(16, 185, 129, 0.32)',
            lensingGlow: 'rgba(228, 228, 231, 0.22)',
            colors: ['#E4E4E7', '#10B981', '#94A3B8', '#6EE7B7', '#FFFFFF'],
            jetColor: 'rgba(228, 228, 231, 0.68)',
            jetGlow: 'rgba(16, 185, 129, 0.4)',
            ambientGlow: 'rgba(16, 185, 129, 0.16)'
        };
    } else {
        // Obsidian / Default Fluent Dark
        return {
            photonGlow: '#00D2FF',
            photonCore: '#FFFFFF',
            lensingColor: 'rgba(37, 99, 235, 0.38)',
            lensingGlow: 'rgba(0, 210, 255, 0.28)',
            colors: ['#00D2FF', '#2563EB', '#60A5FA', '#38BDF8', '#FFFFFF'],
            jetColor: 'rgba(0, 210, 255, 0.68)',
            jetGlow: 'rgba(37, 99, 235, 0.45)',
            ambientGlow: 'rgba(0, 210, 255, 0.18)'
        };
    }
}

function renderBlackHole(ctx, w, h, dt) {
    if (!ctx || w === 0 || h === 0) return;
    const cx = w / 2;
    const cy = h / 2;
    const palette = getBlackHolePalette();
    const isRunning = isServersRunning;

    ctx.clearRect(0, 0, w, h);

    const speedMult = isRunning ? 1.65 : 0.35;
    const activityFactor = isRunning ? 1.0 : 0.4;
    const rEventHorizon = 28;
    const rPhoton = 32;

    // 1. Relativistic Jets (Collimated Bipolar Outflows when servers active)
    if (isRunning) {
        ctx.save();
        const jetGradTop = ctx.createLinearGradient(cx, cy - rEventHorizon, cx, cy - 122);
        jetGradTop.addColorStop(0, palette.photonCore);
        jetGradTop.addColorStop(0.2, palette.jetColor);
        jetGradTop.addColorStop(1, 'transparent');

        ctx.fillStyle = jetGradTop;
        ctx.beginPath();
        ctx.moveTo(cx - 3, cy - rEventHorizon + 2);
        ctx.lineTo(cx + 3, cy - rEventHorizon + 2);
        ctx.lineTo(cx + 8, cy - 122);
        ctx.lineTo(cx - 8, cy - 122);
        ctx.closePath();
        ctx.fill();

        const jetGradBot = ctx.createLinearGradient(cx, cy + rEventHorizon, cx, cy + 122);
        jetGradBot.addColorStop(0, palette.photonCore);
        jetGradBot.addColorStop(0.2, palette.jetColor);
        jetGradBot.addColorStop(1, 'transparent');

        ctx.fillStyle = jetGradBot;
        ctx.beginPath();
        ctx.moveTo(cx - 3, cy + rEventHorizon - 2);
        ctx.lineTo(cx + 3, cy + rEventHorizon - 2);
        ctx.lineTo(cx + 8, cy + 122);
        ctx.lineTo(cx - 8, cy + 122);
        ctx.closePath();
        ctx.fill();
        ctx.restore();
    }

    // 2. Ambient Gravitational Lensing Halo / Corona
    ctx.save();
    const haloGrad = ctx.createRadialGradient(cx, cy, rEventHorizon, cx, cy, 120);
    haloGrad.addColorStop(0, palette.ambientGlow);
    haloGrad.addColorStop(0.5, palette.lensingGlow);
    haloGrad.addColorStop(1, 'transparent');
    ctx.fillStyle = haloGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, 120, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // 3. Gravitational Lensing Warp: Upper Arc (Interstellar Gargantua Effect)
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(cx, cy - 10, 58, 38, -0.15, Math.PI * 0.95, Math.PI * 2.05);
    ctx.strokeStyle = palette.lensingColor;
    ctx.lineWidth = isRunning ? 16 : 8;
    ctx.filter = isRunning ? 'blur(4px)' : 'blur(2px)';
    ctx.stroke();

    ctx.beginPath();
    ctx.ellipse(cx, cy - 10, 56, 36, -0.15, Math.PI * 0.98, Math.PI * 2.02);
    ctx.strokeStyle = palette.photonCore;
    ctx.lineWidth = isRunning ? 2.5 : 1;
    ctx.filter = 'none';
    ctx.stroke();
    ctx.restore();

    // 4. Accretion Disk Swirling Matter Particles (Keplerian Velocity & Relativistic Beaming)
    const tilt = -0.18; // ~10.3 deg tilt
    const cosTilt = Math.cos(tilt);
    const sinTilt = Math.sin(tilt);
    const yAspect = 0.38; // 3D projection aspect ratio

    ctx.save();
    for (let i = 0; i < blackholeParticles.length; i++) {
        const p = blackholeParticles[i];

        // Keplerian angular velocity: v = k / r^1.4 (inner particles whip much faster)
        const omega = (220 / Math.pow(p.r, 1.35)) * speedMult * p.speedFactor;
        p.angle += omega * dt;
        p.r -= p.infallRate * (isRunning ? 1.5 : 0.5);

        // Particle swallowed by singularity -> respawn at outer rim
        if (p.r < rEventHorizon - 1) {
            p.r = 114 + Math.random() * 10;
            p.angle = Math.random() * Math.PI * 2;
            p.history = [];
        }

        // 3D coordinate mapping
        const rawX = p.r * Math.cos(p.angle);
        const rawY = p.r * Math.sin(p.angle) * yAspect;
        const screenX = cx + (rawX * cosTilt - rawY * sinTilt);
        const screenY = cy + (rawX * sinTilt + rawY * cosTilt);

        // Relativistic Doppler Beaming:
        // Left-side particles move toward observer -> boosted brightness & white shift
        // Right-side particles move away -> dimmed
        const doppler = -Math.sin(p.angle); // approaches when sin < 0
        let dopplerBoost = 1.0 + (doppler * 0.65);
        if (dopplerBoost < 0.25) dopplerBoost = 0.25;

        const alpha = Math.min(1.0, p.alpha * dopplerBoost * activityFactor);
        const col = (doppler > 0.4 && isRunning) ? palette.photonCore : palette.colors[p.colorIdx % palette.colors.length];

        // Draw particle trail
        p.history.push({ x: screenX, y: screenY });
        if (p.history.length > (isRunning ? 4 : 2)) p.history.shift();

        if (p.history.length > 1) {
            ctx.beginPath();
            ctx.moveTo(p.history[0].x, p.history[0].y);
            for (let h = 1; h < p.history.length; h++) {
                ctx.lineTo(p.history[h].x, p.history[h].y);
            }
            ctx.strokeStyle = col;
            ctx.globalAlpha = alpha * 0.6;
            ctx.lineWidth = p.size;
            ctx.stroke();
        }

        // Draw particle head
        ctx.beginPath();
        ctx.arc(screenX, screenY, p.size, 0, Math.PI * 2);
        ctx.fillStyle = col;
        ctx.globalAlpha = alpha;
        ctx.fill();
    }
    ctx.restore();

    // 5. Gravitational Lensing Warp: Lower Arc
    ctx.save();
    ctx.beginPath();
    ctx.ellipse(cx, cy + 10, 56, 32, -0.15, 0, Math.PI);
    ctx.strokeStyle = palette.lensingGlow;
    ctx.lineWidth = isRunning ? 10 : 5;
    ctx.filter = 'blur(3px)';
    ctx.stroke();
    ctx.restore();

    // 6. Brilliant Photon Sphere (Einstein Ring) with Doppler Crescent
    ctx.save();
    // Inner diffuse glow
    ctx.beginPath();
    ctx.arc(cx, cy, rPhoton + 3, 0, Math.PI * 2);
    ctx.strokeStyle = palette.photonGlow;
    ctx.lineWidth = isRunning ? 6 : 3;
    ctx.filter = 'blur(4px)';
    ctx.stroke();

    // Sharp Photon Ring
    ctx.filter = 'none';
    ctx.beginPath();
    ctx.arc(cx, cy, rPhoton, 0, Math.PI * 2);
    ctx.strokeStyle = palette.photonGlow;
    ctx.lineWidth = isRunning ? 3.5 : 2;
    ctx.stroke();

    // Intense Doppler Blueshift Crescent on the approaching (left) side
    ctx.beginPath();
    ctx.arc(cx, cy, rPhoton, Math.PI * 0.6, Math.PI * 1.4);
    ctx.strokeStyle = palette.photonCore;
    ctx.lineWidth = isRunning ? 4.5 : 2.5;
    ctx.stroke();
    ctx.restore();

    // 7. Event Horizon (Central Pitch-Black Singularity Core)
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, rEventHorizon, 0, Math.PI * 2);
    ctx.fillStyle = '#000000';
    ctx.shadowColor = '#000000';
    ctx.shadowBlur = 12;
    ctx.fill();
    ctx.restore();

    // 8. Gravitational Wave Shockwave Ripple (triggered on power click)
    if (blackholeWave.alpha > 0.01) {
        ctx.save();
        ctx.beginPath();
        ctx.arc(cx, cy, blackholeWave.radius, 0, Math.PI * 2);
        ctx.strokeStyle = palette.photonGlow;
        ctx.lineWidth = 4 * blackholeWave.alpha;
        ctx.globalAlpha = blackholeWave.alpha;
        ctx.shadowColor = palette.photonGlow;
        ctx.shadowBlur = 15;
        ctx.stroke();
        ctx.restore();

        blackholeWave.radius += blackholeWave.speed;
        blackholeWave.alpha *= 0.93;
    }
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

// Power Gauge Shape Switcher (Round, Square, Hexagon, Capsule)
let currentPowerShape = 'round';

function initPowerShape() {
    try {
        const saved = localStorage.getItem('omnihost_power_shape');
        if (saved) currentPowerShape = saved;
    } catch (e) {}
    setPowerShape(currentPowerShape, false);
}

function setPowerShape(shape, showNotification = true) {
    if (!['round', 'square', 'hexagon', 'capsule'].includes(shape)) shape = 'round';
    currentPowerShape = shape;
    try {
        localStorage.setItem('omnihost_power_shape', shape);
    } catch (e) {}

    const container = document.querySelector('.power-toggle-container');
    if (container) {
        container.classList.remove('shape-round', 'shape-square', 'shape-hexagon', 'shape-capsule');
        container.classList.add(`shape-${shape}`);
    }

    // Update shape buttons (both toolbar and drawer)
    document.querySelectorAll('.shape-btn').forEach(btn => {
        const btnShape = btn.getAttribute('data-shape') || (btn.id ? btn.id.replace('shape-btn-', '') : '');
        if (btnShape === shape) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    if (showNotification) {
        const shapeLabels = {
            round: '⚪ Round Dial',
            square: '⬛ Cyber Squircle',
            hexagon: '⬡ Hex Shield',
            capsule: '💊 Reactor Capsule'
        };
        showToast(`Layout: ${shapeLabels[shape] || shape}`);
    }
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
