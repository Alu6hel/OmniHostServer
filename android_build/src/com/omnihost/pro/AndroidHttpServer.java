package com.omnihost.pro;

import android.content.Context;
import android.content.res.AssetManager;
import java.io.*;
import java.net.*;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.*;
import org.json.JSONArray;
import org.json.JSONObject;

public class AndroidHttpServer {
    private final Context context;
    private final int port;
    private ServerSocket serverSocket;
    private ExecutorService threadPool;
    private volatile boolean isRunning = false;
    private String activeSite = "default";
    private final List<String> availableSites = new ArrayList<>(Arrays.asList("default", "portfolio", "business", "blog"));

    // Telemetry
    private long totalRequests = 0;
    private long totalBytes = 0;
    private final long startTime = System.currentTimeMillis();
    private final List<JSONObject> recentLogs = new ArrayList<>();
    private final SimpleDateFormat timeFormat = new SimpleDateFormat("HH:mm:ss", Locale.US);

    public AndroidHttpServer(Context context, int port) {
        this.context = context;
        this.port = port;
    }

    public synchronized void start() throws IOException {
        if (isRunning) return;
        serverSocket = new ServerSocket(port);
        threadPool = Executors.newCachedThreadPool();
        isRunning = true;

        new Thread(() -> {
            while (isRunning) {
                try {
                    Socket client = serverSocket.accept();
                    if (!isRunning) break;
                    threadPool.submit(() -> handleClient(client));
                } catch (IOException e) {
                    if (!isRunning) break;
                }
            }
        }, "OmniHostHttpListener").start();
    }

    public synchronized void stop() {
        isRunning = false;
        if (serverSocket != null && !serverSocket.isClosed()) {
            try { serverSocket.close(); } catch (IOException ignored) {}
        }
        if (threadPool != null && !threadPool.isShutdown()) {
            threadPool.shutdownNow();
        }
    }

    public boolean isRunning() {
        return isRunning;
    }

    public synchronized String getActiveSite() {
        return activeSite;
    }

    public synchronized void setActiveSite(String site) {
        this.activeSite = site;
        recordLog("SWITCH", "/site/" + site, 200, 0, "127.0.0.1");
    }

    public List<String> getAvailableSites() {
        return availableSites;
    }

    public synchronized JSONObject getStatsJson() {
        JSONObject stats = new JSONObject();
        try {
            long uptimeSeconds = Math.max(1, (System.currentTimeMillis() - startTime) / 1000);
            double qps = Math.round((double) totalRequests / uptimeSeconds * 100.0) / 100.0;
            stats.put("status", isRunning ? "online" : "offline");
            stats.put("port", port);
            stats.put("active_site", activeSite);
            stats.put("total_requests", totalRequests);
            stats.put("total_bytes", totalBytes);
            stats.put("uptime_seconds", uptimeSeconds);
            stats.put("qps", qps);

            JSONArray sitesArr = new JSONArray();
            for (String s : availableSites) sitesArr.put(s);
            stats.put("available_sites", sitesArr);

            JSONArray logsArr = new JSONArray();
            for (int i = Math.max(0, recentLogs.size() - 25); i < recentLogs.size(); i++) {
                logsArr.put(recentLogs.get(i));
            }
            stats.put("recent_logs", logsArr);
        } catch (Exception ignored) {}
        return stats;
    }

    private synchronized void recordLog(String method, String path, int status, long size, String ip) {
        totalRequests++;
        totalBytes += size;
        try {
            JSONObject log = new JSONObject();
            log.put("timestamp", timeFormat.format(new Date()));
            log.put("method", method);
            log.put("path", path);
            log.put("status", status);
            log.put("size", size);
            log.put("ip", ip);
            recentLogs.add(log);
            if (recentLogs.size() > 100) recentLogs.remove(0);
        } catch (Exception ignored) {}
    }

    private void handleClient(Socket client) {
        String clientIp = client.getInetAddress() != null ? client.getInetAddress().getHostAddress() : "127.0.0.1";
        try (
            InputStream in = client.getInputStream();
            OutputStream out = client.getOutputStream();
            BufferedReader reader = new BufferedReader(new InputStreamReader(in))
        ) {
            String requestLine = reader.readLine();
            if (requestLine == null || requestLine.isEmpty()) return;

            String[] parts = requestLine.split(" ");
            if (parts.length < 2) return;

            String method = parts[0];
            String fullUri = parts[1];
            String path = fullUri.contains("?") ? fullUri.substring(0, fullUri.indexOf('?')) : fullUri;

            // Read headers
            Map<String, String> headers = new HashMap<>();
            String headerLine;
            int contentLength = 0;
            while ((headerLine = reader.readLine()) != null && !headerLine.isEmpty()) {
                int colon = headerLine.indexOf(':');
                if (colon > 0) {
                    String k = headerLine.substring(0, colon).trim().toLowerCase(Locale.US);
                    String v = headerLine.substring(colon + 1).trim();
                    headers.put(k, v);
                    if ("content-length".equals(k)) {
                        try { contentLength = Integer.parseInt(v); } catch (Exception ignored) {}
                    }
                }
            }

            // Read body if POST
            String body = "";
            if (contentLength > 0) {
                char[] buf = new char[contentLength];
                int read = reader.read(buf, 0, contentLength);
                if (read > 0) body = new String(buf, 0, read);
            }

            // OPTIONS preflight
            if ("OPTIONS".equalsIgnoreCase(method)) {
                sendResponse(out, 200, "text/plain", "OK".getBytes(), clientIp, method, path);
                return;
            }

            // REST API Endpoints
            if ("/api/status".equals(path)) {
                byte[] json = getStatsJson().toString().getBytes("UTF-8");
                sendResponse(out, 200, "application/json", json, clientIp, method, path);
                return;
            }

            if ("/api/sites".equals(path)) {
                JSONObject obj = new JSONObject();
                obj.put("active_site", getActiveSite());
                JSONArray arr = new JSONArray();
                for (String s : availableSites) arr.put(s);
                obj.put("sites", arr);
                byte[] json = obj.toString().getBytes("UTF-8");
                sendResponse(out, 200, "application/json", json, clientIp, method, path);
                return;
            }

            if ("/api/switch-site".equals(path) && "POST".equalsIgnoreCase(method)) {
                String newSite = "default";
                try {
                    JSONObject req = new JSONObject(body);
                    if (req.has("site_name")) newSite = req.getString("site_name");
                } catch (Exception ignored) {}
                setActiveSite(newSite);
                JSONObject resp = new JSONObject();
                resp.put("status", "ok");
                resp.put("active_site", newSite);
                byte[] json = resp.toString().getBytes("UTF-8");
                sendResponse(out, 200, "application/json", json, clientIp, method, path);
                return;
            }

            // Static File Serving for active site
            serveSiteFile(out, path, clientIp, method);

        } catch (Exception ignored) {
        } finally {
            try { client.close(); } catch (Exception ignored) {}
        }
    }

    private void serveSiteFile(OutputStream out, String path, String clientIp, String method) throws IOException {
        String assetPath = "sites/" + activeSite;
        if ("/".equals(path) || path.isEmpty()) {
            path = "/index.html";
        }

        String targetAsset = assetPath + path;
        byte[] content = loadAssetBytes(targetAsset);

        // Single-Page Application (SPA) Fallback
        if (content == null && !path.contains(".")) {
            targetAsset = assetPath + "/index.html";
            content = loadAssetBytes(targetAsset);
        }

        if (content != null) {
            String mime = getMimeType(targetAsset);
            sendResponse(out, 200, mime, content, clientIp, method, path);
        } else {
            byte[] notFound = ("<h1>404 Not Found</h1><p>Site: " + activeSite + " | Path: " + path + "</p>").getBytes("UTF-8");
            sendResponse(out, 404, "text/html", notFound, clientIp, method, path);
        }
    }

    private byte[] loadAssetBytes(String assetPath) {
        try (InputStream is = context.getAssets().open(assetPath)) {
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = is.read(buf)) != -1) {
                baos.write(buf, 0, n);
            }
            return baos.toByteArray();
        } catch (IOException e) {
            return null;
        }
    }

    private void sendResponse(OutputStream out, int status, String mime, byte[] body, String clientIp, String method, String path) throws IOException {
        String statusText = status == 200 ? "OK" : (status == 404 ? "Not Found" : "Error");
        StringBuilder header = new StringBuilder();
        header.append("HTTP/1.1 ").append(status).append(" ").append(statusText).append("\r\n");
        header.append("Content-Type: ").append(mime).append("\r\n");
        header.append("Content-Length: ").append(body.length).append("\r\n");
        header.append("Access-Control-Allow-Origin: *\r\n");
        header.append("Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n");
        header.append("Access-Control-Allow-Headers: Content-Type\r\n");
        header.append("Connection: close\r\n\r\n");

        out.write(header.toString().getBytes("UTF-8"));
        out.write(body);
        out.flush();

        recordLog(method, path, status, body.length, clientIp);
    }

    private String getMimeType(String file) {
        String lower = file.toLowerCase(Locale.US);
        if (lower.endsWith(".html") || lower.endsWith(".htm")) return "text/html; charset=utf-8";
        if (lower.endsWith(".css")) return "text/css; charset=utf-8";
        if (lower.endsWith(".js") || lower.endsWith(".mjs")) return "application/javascript; charset=utf-8";
        if (lower.endsWith(".json")) return "application/json; charset=utf-8";
        if (lower.endsWith(".png")) return "image/png";
        if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) return "image/jpeg";
        if (lower.endsWith(".svg")) return "image/svg+xml";
        if (lower.endsWith(".ico")) return "image/x-icon";
        if (lower.endsWith(".txt")) return "text/plain; charset=utf-8";
        return "application/octet-stream";
    }
}
