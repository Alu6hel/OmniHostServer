function copyText(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    navigator.clipboard.writeText(el.innerText || el.textContent).then(() => {
        alert("Copied to clipboard: " + el.innerText);
    });
}

function pollStatus() {
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            if (data.qps !== undefined) document.getElementById('metric-qps').innerText = data.qps + ' req/s';
            if (data.total_requests !== undefined) document.getElementById('metric-hits').innerText = data.total_requests;
            if (data.total_bytes !== undefined) document.getElementById('metric-bytes').innerText = Math.round(data.total_bytes / 1024) + ' KB';
            if (data.active_site !== undefined) document.getElementById('metric-site').innerText = data.active_site;

            if (data.recent_logs && data.recent_logs.length > 0) {
                const feed = document.getElementById('log-feed');
                feed.innerHTML = '';
                data.recent_logs.forEach(log => {
                    const row = document.createElement('div');
                    row.className = 'log-row';
                    row.innerHTML = `<span class="time">[${log.timestamp}]</span> ${log.method} ${log.path} &bull; ${log.status} (${log.size} B) &bull; ${log.ip}`;
                    feed.appendChild(row);
                });
            }
        })
        .catch(err => {
            console.log("Telemetry poll standby...");
        });
}

function switchSite(siteName) {
    fetch('/api/switch-site', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ site_name: siteName })
    })
    .then(r => r.json())
    .then(res => {
        if (res.status === 'ok') {
            document.querySelectorAll('.chip').forEach(c => {
                if (c.innerText.startsWith(siteName)) {
                    c.classList.add('active');
                    c.innerText = siteName + ' ★';
                } else {
                    c.classList.remove('active');
                    c.innerText = c.innerText.replace(' ★', '');
                }
            });
            pollStatus();
        }
    });
}

setInterval(pollStatus, 2000);
pollStatus();
