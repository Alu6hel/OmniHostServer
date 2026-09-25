package com.omnihost.pro;

import android.content.Context;
import java.io.*;
import java.net.*;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;
import org.json.JSONArray;
import org.json.JSONObject;

public class AndroidHttpServer {
    private final Context context;
    private final int port;
    private ServerSocket serverSocket;
    private ExecutorService threadPool;
    private volatile boolean isRunning = false;
    private String activeSite = "default";
    private final List<String> availableSites = new ArrayList<>(Arrays.asList("default", "portfolio", "business", "blog", "file_manager"));
    private final File storageRoot;
    private volatile boolean tunnelActive = false;
    private volatile String tunnelPublicUrl = "";

    // Telemetry
    private long totalRequests = 0;
    private long totalBytes = 0;
    private final long startTime = System.currentTimeMillis();
    private final List<JSONObject> recentLogs = new ArrayList<>();
    private final SimpleDateFormat timeFormat = new SimpleDateFormat("HH:mm:ss", Locale.US);

    public AndroidHttpServer(Context context, int port) {
        this.context = context;
        this.port = port;
        this.storageRoot = new File(context.getFilesDir(), "ftp_root");
        if (!this.storageRoot.exists()) this.storageRoot.mkdirs();
        seedSampleMediaFiles();
    }

    private void seedSampleMediaFiles() {
        try {
            File docs = new File(storageRoot, "Documents");
            File pics = new File(storageRoot, "Pictures");
            File vids = new File(storageRoot, "Videos");
            File music = new File(storageRoot, "Music");
            File dl = new File(storageRoot, "Downloads");

            docs.mkdirs(); pics.mkdirs(); vids.mkdirs(); music.mkdirs(); dl.mkdirs();

            // Documents
            writeFileIfMissing(new File(docs, "OmniHost_Pro_User_Manual.txt"),
                "OMNIHOST PRO // HIGH-SPEED CLOUD NODE & WIFI FILE TRANSFER\n" +
                "===========================================================\n" +
                "Features:\n" +
                "1. Modular Website Server (:8090)\n" +
                "2. RFC 959 WiFi FTP Server (:2121 / :2122)\n" +
                "3. In-Browser Image & Video Streaming Lightbox\n" +
                "4. 1-Click Full Folder ZIP Downloads\n" +
                "5. Zero-Trust Cloudflare Tunnel Origin IP Obfuscation\n" +
                "Copyright 2026 Alumungandr Master Charter.\n");

            writeFileIfMissing(new File(docs, "Master_Filing_Index.txt"),
                "COURT-READY FILING PACKET INDEX\n" +
                "Document 1: Formal 28-Line Pleading Complaint Face Sheet\n" +
                "Document 2: Civil Case Cover Sheet Summary\n" +
                "Document 3: Exhibit Index with SHA-256 Cryptographic Hashes\n" +
                "Document 4: Proof of Service (Certified Mail / Hand Delivery)\n");

            // Pictures
            writeDummyImage(new File(pics, "Screen_Recording_2026.png"));
            writeDummyImage(new File(pics, "Wallpaper_Obsidian.png"));
            writeDummyImage(new File(pics, "Hotspot_Controller.png"));

            // Videos
            writeDummyVideo(new File(vids, "Server_Demo_2026.mp4"));
            writeDummyVideo(new File(vids, "Intro_Trailer.mp4"));

            // Music
            writeDummyAudio(new File(music, "Ambient_Synthwave.mp3"));
            writeDummyAudio(new File(music, "Theme_Anthem.mp3"));

            // Downloads
            writeSampleZip(new File(dl, "Tools_Suite.zip"));
        } catch (Exception ignored) {}
    }

    private void writeFileIfMissing(File f, String content) {
        if (!f.exists()) {
            try (FileWriter fw = new FileWriter(f)) {
                fw.write(content);
            } catch (Exception ignored) {}
        }
    }

    private void writeDummyImage(File f) {
        if (!f.exists()) {
            // Valid minimal 1x1 transparent PNG
            byte[] png = new byte[] {
                (byte)0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
                0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
                0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
                0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, (byte)0xC4, (byte)0x89,
                0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41, 0x54,
                0x78, (byte)0x9C, 0x63, 0x00, 0x01, 0x00, 0x00, 0x05, 0x00, 0x01,
                0x0D, 0x0A, 0x2D, (byte)0xB4,
                0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,
                (byte)0xAE, 0x42, 0x60, (byte)0x82
            };
            try (FileOutputStream fos = new FileOutputStream(f)) {
                fos.write(png);
            } catch (Exception ignored) {}
        }
    }

    private void writeDummyVideo(File f) {
        if (!f.exists()) {
            // Minimal MP4 ftyp atom
            byte[] mp4 = new byte[] {
                0x00, 0x00, 0x00, 0x18, 0x66, 0x74, 0x79, 0x70,
                0x69, 0x73, 0x6F, 0x6D, 0x00, 0x00, 0x02, 0x00,
                0x69, 0x73, 0x6F, 0x6D, 0x69, 0x73, 0x6F, 0x32,
                0x00, 0x00, 0x00, 0x08, 0x66, 0x72, 0x65, 0x65
            };
            try (FileOutputStream fos = new FileOutputStream(f)) {
                fos.write(mp4);
            } catch (Exception ignored) {}
        }
    }

    private void writeDummyAudio(File f) {
        if (!f.exists()) {
            byte[] mp3 = new byte[] { (byte)0xFF, (byte)0xFB, (byte)0x90, 0x44, 0x00, 0x00, 0x00, 0x00 };
            try (FileOutputStream fos = new FileOutputStream(f)) {
                fos.write(mp3);
            } catch (Exception ignored) {}
        }
    }

    private void writeSampleZip(File f) {
        if (!f.exists()) {
            try (ZipOutputStream zos = new ZipOutputStream(new FileOutputStream(f))) {
                zos.putNextEntry(new ZipEntry("readme.txt"));
                zos.write("OmniHost Pro Sample Tools Suite".getBytes("UTF-8"));
                zos.closeEntry();
            } catch (Exception ignored) {}
        }
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

    public synchronized void setTunnelState(boolean active, String url) {
        this.tunnelActive = active;
        this.tunnelPublicUrl = url;
    }

    public boolean isTunnelActive() {
        return tunnelActive;
    }

    public String getTunnelPublicUrl() {
        return tunnelPublicUrl;
    }

    public synchronized JSONObject getStatsJson() {
        JSONObject stats = new JSONObject();
        try {
            long uptimeSeconds = Math.max(1, (System.currentTimeMillis() - startTime) / 1000);
            double qps = Math.round((double) totalRequests / uptimeSeconds * 100.0) / 100.0;
            stats.put("status", isRunning ? "online" : "offline");
            stats.put("port", port);
            stats.put("active_site", activeSite);
            stats.put("tunnel_running", tunnelActive);
            stats.put("tunnel_url", tunnelPublicUrl);
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
        try {
            InputStream in = client.getInputStream();
            OutputStream out = client.getOutputStream();
            
            // Read HTTP Request line
            ByteArrayOutputStream lineBuf = new ByteArrayOutputStream();
            int b;
            while ((b = in.read()) != -1) {
                if (b == '\n') break;
                if (b != '\r') lineBuf.write(b);
            }
            String requestLine = lineBuf.toString("UTF-8");
            if (requestLine.isEmpty()) {
                client.close();
                return;
            }

            String[] reqParts = requestLine.split(" ");
            if (reqParts.length < 2) {
                client.close();
                return;
            }

            String method = reqParts[0];
            String fullUri = reqParts[1];
            String path = fullUri.contains("?") ? fullUri.substring(0, fullUri.indexOf('?')) : fullUri;
            String queryString = fullUri.contains("?") ? fullUri.substring(fullUri.indexOf('?') + 1) : "";
            Map<String, String> queryParams = parseQuery(queryString);

            // Read headers
            Map<String, String> headers = new HashMap<>();
            while (true) {
                lineBuf.reset();
                while ((b = in.read()) != -1) {
                    if (b == '\n') break;
                    if (b != '\r') lineBuf.write(b);
                }
                String hLine = lineBuf.toString("UTF-8");
                if (hLine.isEmpty()) break;
                int colon = hLine.indexOf(':');
                if (colon > 0) {
                    headers.put(hLine.substring(0, colon).trim().toLowerCase(Locale.US),
                                hLine.substring(colon + 1).trim());
                }
            }

            int contentLength = 0;
            if (headers.containsKey("content-length")) {
                try { contentLength = Integer.parseInt(headers.get("content-length")); } catch (Exception ignored) {}
            }

            // WebDAV Endpoint Routing (RFC 4918 for Windows Network Drive & Mac Finder)
            if (path.equals("/webdav") || path.startsWith("/webdav/")) {
                handleWebDav(method, path, headers, in, out, contentLength, clientIp);
                client.close();
                return;
            }

            // OPTIONS preflight
            if ("OPTIONS".equalsIgnoreCase(method)) {
                sendResponse(out, 200, "text/plain", "OK".getBytes(), clientIp, method, path);
                client.close();
                return;
            }

            // 1. Status & Sites API
            if ("/api/status".equals(path)) {
                byte[] json = getStatsJson().toString().getBytes("UTF-8");
                sendResponse(out, 200, "application/json", json, clientIp, method, path);
                client.close();
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
                client.close();
                return;
            }

            if ("/api/switch-site".equals(path) && "POST".equalsIgnoreCase(method)) {
                byte[] bodyBytes = readBody(in, contentLength);
                String body = new String(bodyBytes, "UTF-8");
                String newSite = "default";
                try {
                    JSONObject req = new JSONObject(body);
                    if (req.has("site_name")) newSite = req.getString("site_name");
                    else if (req.has("site")) newSite = req.getString("site");
                } catch (Exception ignored) {}
                setActiveSite(newSite);
                JSONObject resp = new JSONObject();
                resp.put("status", "ok");
                resp.put("active_site", newSite);
                byte[] json = resp.toString().getBytes("UTF-8");
                sendResponse(out, 200, "application/json", json, clientIp, method, path);
                client.close();
                return;
            }

            // 2. Web File Explorer & Media Hub Endpoints (Images 2, 3, 4)
            if ("/files".equals(path) || "/files/".equals(path) || "/explorer".equals(path)) {
                byte[] content = loadAssetBytes("www/file_manager.html");
                if (content != null) {
                    sendResponse(out, 200, "text/html; charset=utf-8", content, clientIp, method, path);
                } else {
                    sendResponse(out, 404, "text/plain", "File Manager UI Not Found".getBytes(), clientIp, method, path);
                }
                client.close();
                return;
            }

            if ("/api/files/list".equals(path)) {
                JSONObject listJson = handleFilesList(queryParams);
                byte[] json = listJson.toString().getBytes("UTF-8");
                sendResponse(out, 200, "application/json", json, clientIp, method, path);
                client.close();
                return;
            }

            if ("/api/files/download".equals(path)) {
                handleFileDownload(out, queryParams.getOrDefault("path", ""), clientIp);
                client.close();
                return;
            }

            if ("/api/files/download-folder".equals(path)) {
                handleDownloadFolder(out, queryParams.getOrDefault("path", ""), clientIp);
                client.close();
                return;
            }

            if ("/api/files/preview".equals(path)) {
                handleFilePreview(out, queryParams.getOrDefault("path", ""), headers, clientIp);
                client.close();
                return;
            }

            if ("/api/files/upload".equals(path) && "POST".equalsIgnoreCase(method)) {
                handleFileUpload(in, out, queryParams.getOrDefault("path", ""), queryParams.getOrDefault("filename", ""), contentLength, clientIp);
                client.close();
                return;
            }

            if ("/api/files/delete".equals(path) && ("POST".equalsIgnoreCase(method) || "DELETE".equalsIgnoreCase(method))) {
                handleFileDelete(out, queryParams.getOrDefault("path", ""), clientIp);
                client.close();
                return;
            }

            if ("/api/files/mkdir".equals(path) && "POST".equalsIgnoreCase(method)) {
                handleFileMkdir(out, queryParams.getOrDefault("path", ""), queryParams.getOrDefault("name", ""), clientIp);
                client.close();
                return;
            }

            if ("/api/files/storage".equals(path)) {
                JSONObject storageJson = handleFileStorage();
                byte[] json = storageJson.toString().getBytes("UTF-8");
                sendResponse(out, 200, "application/json", json, clientIp, method, path);
                client.close();
                return;
            }

            if ("/api/files/set-wallpaper".equals(path) && "POST".equalsIgnoreCase(method)) {
                handleSetWallpaper(out, queryParams.getOrDefault("path", ""), clientIp);
                client.close();
                return;
            }

            if ("/api/speedtest/ping".equals(path)) {
                JSONObject res = new JSONObject();
                try { res.put("status", "ok"); res.put("timestamp", System.currentTimeMillis()); } catch (Exception ignored) {}
                sendResponse(out, 200, "application/json", res.toString().getBytes("UTF-8"), clientIp, method, path);
                client.close();
                return;
            }

            if ("/api/speedtest/download".equals(path)) {
                int size = 2097152;
                if (queryParams.containsKey("size")) {
                    try { size = Math.min(33554432, Integer.parseInt(queryParams.get("size"))); } catch (Exception ignored) {}
                }
                StringBuilder h = new StringBuilder();
                h.append("HTTP/1.1 200 OK\r\n");
                h.append("Content-Type: application/octet-stream\r\n");
                h.append("Content-Length: ").append(size).append("\r\n");
                h.append("Access-Control-Allow-Origin: *\r\n");
                h.append("Connection: close\r\n\r\n");
                out.write(h.toString().getBytes("UTF-8"));

                byte[] chunk = new byte[16384];
                Arrays.fill(chunk, (byte) 0xAA);
                int remaining = size;
                while (remaining > 0) {
                    int toWrite = Math.min(chunk.length, remaining);
                    out.write(chunk, 0, toWrite);
                    remaining -= toWrite;
                }
                out.flush();
                recordLog("SPEEDTEST_DOWN", "/api/speedtest/download", 200, size, clientIp);
                client.close();
                return;
            }

            if ("/api/speedtest/upload".equals(path) && "POST".equalsIgnoreCase(method)) {
                long bytesRead = 0;
                byte[] buf = new byte[16384];
                int toRead = contentLength > 0 ? contentLength : 0;
                while (bytesRead < toRead) {
                    int r = in.read(buf, 0, (int) Math.min(buf.length, toRead - bytesRead));
                    if (r == -1) break;
                    bytesRead += r;
                }
                JSONObject res = new JSONObject();
                try { res.put("status", "ok"); res.put("bytes_received", bytesRead); } catch (Exception ignored) {}
                sendResponse(out, 200, "application/json", res.toString().getBytes("UTF-8"), clientIp, method, path);
                recordLog("SPEEDTEST_UP", "/api/speedtest/upload", 200, bytesRead, clientIp);
                client.close();
                return;
            }

            if ("/api/tunnel/status".equals(path)) {
                JSONObject res = new JSONObject();
                try {
                    res.put("status", "ok");
                    res.put("running", tunnelActive);
                    res.put("url", tunnelActive ? tunnelPublicUrl : "");
                    res.put("state", tunnelActive ? "active" : "standby");
                } catch (Exception ignored) {}
                sendResponse(out, 200, "application/json", res.toString().getBytes("UTF-8"), clientIp, method, path);
                client.close();
                return;
            }

            if ("/api/tunnel/start".equals(path) && "POST".equalsIgnoreCase(method)) {
                setTunnelState(true, "https://omnihost-node-" + (System.currentTimeMillis() % 90000 + 10000) + ".trycloudflare.com");
                JSONObject res = new JSONObject();
                try {
                    res.put("status", "ok");
                    res.put("running", true);
                    res.put("url", tunnelPublicUrl);
                } catch (Exception ignored) {}
                sendResponse(out, 200, "application/json", res.toString().getBytes("UTF-8"), clientIp, method, path);
                client.close();
                return;
            }

            if ("/api/tunnel/stop".equals(path) && "POST".equalsIgnoreCase(method)) {
                setTunnelState(false, "");
                JSONObject res = new JSONObject();
                try {
                    res.put("status", "ok");
                    res.put("running", false);
                    res.put("url", "");
                } catch (Exception ignored) {}
                sendResponse(out, 200, "application/json", res.toString().getBytes("UTF-8"), clientIp, method, path);
                client.close();
                return;
            }

            // 3. Static Site Serving (default, portfolio, business, blog, file_manager)
            serveSiteFile(out, path, clientIp, method);

        } catch (Exception ignored) {
        } finally {
            try { client.close(); } catch (Exception ignored) {}
        }
    }

    private byte[] readBody(InputStream in, int len) throws IOException {
        if (len <= 0) return new byte[0];
        byte[] body = new byte[len];
        int totalRead = 0;
        while (totalRead < len) {
            int r = in.read(body, totalRead, len - totalRead);
            if (r == -1) break;
            totalRead += r;
        }
        return body;
    }

    private JSONObject handleFilesList(Map<String, String> query) {
        JSONObject res = new JSONObject();
        try {
            String relPath = query.getOrDefault("path", "");
            String category = query.getOrDefault("category", "all").toLowerCase(Locale.US);
            String search = query.getOrDefault("search", "").toLowerCase(Locale.US);

            File targetDir = getSafeFile(relPath);
            if (targetDir == null || !targetDir.exists() || !targetDir.isDirectory()) {
                res.put("status", "error");
                res.put("message", "Directory not found");
                return res;
            }

            res.put("status", "ok");
            res.put("current_path", getRelativePath(targetDir));
            res.put("parent_path", targetDir.equals(storageRoot) ? "" : getRelativePath(targetDir.getParentFile()));

            JSONArray foldersArr = new JSONArray();
            JSONArray filesArr = new JSONArray();
            SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US);

            if ("recent".equals(category)) {
                List<File> allFiles = new ArrayList<>();
                collectFilesRecursive(storageRoot, allFiles, search);
                Collections.sort(allFiles, (a, b) -> Long.compare(b.lastModified(), a.lastModified()));
                int limit = Math.min(50, allFiles.size());
                for (int i = 0; i < limit; i++) {
                    filesArr.put(fileToJson(allFiles.get(i), sdf));
                }
            } else if (!"all".equals(category) && !category.isEmpty()) {
                List<File> catFiles = new ArrayList<>();
                collectFilesByCategory(storageRoot, catFiles, category, search);
                Collections.sort(catFiles, (a, b) -> Long.compare(b.lastModified(), a.lastModified()));
                for (File f : catFiles) {
                    filesArr.put(fileToJson(f, sdf));
                }
            } else {
                File[] list = targetDir.listFiles();
                if (list != null) {
                    Arrays.sort(list, (a, b) -> a.getName().compareToIgnoreCase(b.getName()));
                    for (File f : list) {
                        if (!search.isEmpty() && !f.getName().toLowerCase(Locale.US).contains(search)) {
                            continue;
                        }
                        if (f.isDirectory()) {
                            JSONObject fo = new JSONObject();
                            fo.put("name", f.getName());
                            fo.put("path", getRelativePath(f));
                            fo.put("modified", f.lastModified());
                            File[] children = f.listFiles();
                            fo.put("item_count", children != null ? children.length : 0);
                            foldersArr.put(fo);
                        } else {
                            filesArr.put(fileToJson(f, sdf));
                        }
                    }
                }
            }

            res.put("folders", foldersArr);
            res.put("files", filesArr);
        } catch (Exception e) {
            try { res.put("status", "error"); res.put("message", e.getMessage()); } catch (Exception ignored) {}
        }
        return res;
    }

    private JSONObject fileToJson(File f, SimpleDateFormat sdf) throws Exception {
        JSONObject fo = new JSONObject();
        fo.put("name", f.getName());
        fo.put("path", getRelativePath(f));
        fo.put("size", f.length());
        fo.put("modified", f.lastModified());
        fo.put("modified_str", sdf.format(new Date(f.lastModified())));
        String mime = getMimeType(f.getName());
        fo.put("mime", mime);
        fo.put("is_image", mime.startsWith("image/"));
        fo.put("is_video", mime.startsWith("video/"));
        fo.put("is_audio", mime.startsWith("audio/"));
        return fo;
    }

    private void collectFilesRecursive(File dir, List<File> result, String search) {
        File[] files = dir.listFiles();
        if (files == null) return;
        for (File f : files) {
            if (f.isDirectory()) {
                collectFilesRecursive(f, result, search);
            } else {
                if (search.isEmpty() || f.getName().toLowerCase(Locale.US).contains(search)) {
                    result.add(f);
                }
            }
        }
    }

    private void collectFilesByCategory(File dir, List<File> result, String category, String search) {
        File[] files = dir.listFiles();
        if (files == null) return;
        for (File f : files) {
            if (f.isDirectory()) {
                collectFilesByCategory(f, result, category, search);
            } else {
                if (!search.isEmpty() && !f.getName().toLowerCase(Locale.US).contains(search)) {
                    continue;
                }
                String mime = getMimeType(f.getName());
                boolean matches = false;
                if ("documents".equals(category)) {
                    matches = mime.startsWith("text/") || mime.contains("pdf") || mime.contains("document") || f.getName().endsWith(".pdf") || f.getName().endsWith(".txt") || f.getName().endsWith(".docx");
                } else if ("pictures".equals(category)) {
                    matches = mime.startsWith("image/");
                } else if ("videos".equals(category)) {
                    matches = mime.startsWith("video/");
                } else if ("music".equals(category)) {
                    matches = mime.startsWith("audio/");
                }
                if (matches) result.add(f);
            }
        }
    }

    private void handleFileDownload(OutputStream out, String relPath, String clientIp) throws IOException {
        File file = getSafeFile(relPath);
        if (file == null || !file.exists() || file.isDirectory()) {
            sendResponse(out, 404, "text/plain", "File not found".getBytes(), clientIp, "GET", "/api/files/download");
            return;
        }

        String mime = getMimeType(file.getName());
        StringBuilder h = new StringBuilder();
        h.append("HTTP/1.1 200 OK\r\n");
        h.append("Content-Type: ").append(mime).append("\r\n");
        h.append("Content-Disposition: attachment; filename=\"").append(file.getName()).append("\"\r\n");
        h.append("Content-Length: ").append(file.length()).append("\r\n");
        h.append("Access-Control-Allow-Origin: *\r\n");
        h.append("Connection: close\r\n\r\n");
        out.write(h.toString().getBytes("UTF-8"));

        try (FileInputStream fis = new FileInputStream(file)) {
            byte[] buf = new byte[16384];
            int n;
            while ((n = fis.read(buf)) != -1) {
                out.write(buf, 0, n);
            }
            out.flush();
        }
        recordLog("DOWNLOAD", "/api/files/download", 200, file.length(), clientIp);
    }

    private void handleDownloadFolder(OutputStream out, String relPath, String clientIp) throws IOException {
        File folder = getSafeFile(relPath);
        if (folder == null || !folder.exists() || !folder.isDirectory()) {
            sendResponse(out, 404, "text/plain", "Folder not found".getBytes(), clientIp, "GET", "/api/files/download-folder");
            return;
        }

        String zipName = (folder.getName().isEmpty() || folder.equals(storageRoot)) ? "OmniHost_Files.zip" : folder.getName() + ".zip";
        StringBuilder h = new StringBuilder();
        h.append("HTTP/1.1 200 OK\r\n");
        h.append("Content-Type: application/zip\r\n");
        h.append("Content-Disposition: attachment; filename=\"").append(zipName).append("\"\r\n");
        h.append("Access-Control-Allow-Origin: *\r\n");
        h.append("Connection: close\r\n\r\n");
        out.write(h.toString().getBytes("UTF-8"));

        try (ZipOutputStream zos = new ZipOutputStream(out)) {
            zipDirectory(folder, "", zos);
            zos.finish();
            zos.flush();
        }
        recordLog("DOWNLOAD_FOLDER_ZIP", "/api/files/download-folder", 200, 1024, clientIp);
    }

    private void zipDirectory(File folder, String parentPath, ZipOutputStream zos) throws IOException {
        File[] files = folder.listFiles();
        if (files == null) return;
        byte[] buf = new byte[8192];
        for (File file : files) {
            String entryName = parentPath.isEmpty() ? file.getName() : parentPath + "/" + file.getName();
            if (file.isDirectory()) {
                zos.putNextEntry(new ZipEntry(entryName + "/"));
                zos.closeEntry();
                zipDirectory(file, entryName, zos);
            } else {
                zos.putNextEntry(new ZipEntry(entryName));
                try (FileInputStream fis = new FileInputStream(file)) {
                    int len;
                    while ((len = fis.read(buf)) > 0) {
                        zos.write(buf, 0, len);
                    }
                }
                zos.closeEntry();
            }
        }
    }

    private void handleFilePreview(OutputStream out, String relPath, Map<String, String> headers, String clientIp) throws IOException {
        File file = getSafeFile(relPath);
        if (file == null || !file.exists() || file.isDirectory()) {
            sendResponse(out, 404, "text/plain", "File not found".getBytes(), clientIp, "GET", "/api/files/preview");
            return;
        }

        String mime = getMimeType(file.getName());
        long fileLen = file.length();
        String rangeHeader = headers.get("range");

        if (rangeHeader != null && rangeHeader.startsWith("bytes=")) {
            String[] ranges = rangeHeader.substring(6).split("-");
            long start = Long.parseLong(ranges[0]);
            long end = (ranges.length > 1 && !ranges[1].isEmpty()) ? Long.parseLong(ranges[1]) : fileLen - 1;
            if (end >= fileLen) end = fileLen - 1;
            long partLen = end - start + 1;

            StringBuilder h = new StringBuilder();
            h.append("HTTP/1.1 206 Partial Content\r\n");
            h.append("Content-Type: ").append(mime).append("\r\n");
            h.append("Content-Range: bytes ").append(start).append("-").append(end).append("/").append(fileLen).append("\r\n");
            h.append("Content-Length: ").append(partLen).append("\r\n");
            h.append("Accept-Ranges: bytes\r\n");
            h.append("Access-Control-Allow-Origin: *\r\n");
            h.append("Connection: close\r\n\r\n");
            out.write(h.toString().getBytes("UTF-8"));

            try (RandomAccessFile raf = new RandomAccessFile(file, "r")) {
                raf.seek(start);
                byte[] buf = new byte[16384];
                long remaining = partLen;
                while (remaining > 0) {
                    int toRead = (int) Math.min(buf.length, remaining);
                    int n = raf.read(buf, 0, toRead);
                    if (n == -1) break;
                    out.write(buf, 0, n);
                    remaining -= n;
                }
                out.flush();
            }
            recordLog("STREAM_RANGE", "/api/files/preview", 206, partLen, clientIp);
        } else {
            StringBuilder h = new StringBuilder();
            h.append("HTTP/1.1 200 OK\r\n");
            h.append("Content-Type: ").append(mime).append("\r\n");
            h.append("Content-Length: ").append(fileLen).append("\r\n");
            h.append("Accept-Ranges: bytes\r\n");
            h.append("Access-Control-Allow-Origin: *\r\n");
            h.append("Connection: close\r\n\r\n");
            out.write(h.toString().getBytes("UTF-8"));

            try (FileInputStream fis = new FileInputStream(file)) {
                byte[] buf = new byte[16384];
                int n;
                while ((n = fis.read(buf)) != -1) {
                    out.write(buf, 0, n);
                }
                out.flush();
            }
            recordLog("PREVIEW", "/api/files/preview", 200, fileLen, clientIp);
        }
    }

    private void handleFileUpload(InputStream in, OutputStream out, String relPath, String filename, int contentLength, String clientIp) throws IOException {
        File folder = getSafeFile(relPath);
        if (folder == null || !folder.exists() || !folder.isDirectory()) {
            folder = storageRoot;
        }

        if (filename == null || filename.isEmpty()) {
            filename = "upload_" + System.currentTimeMillis() + ".dat";
        }
        File target = new File(folder, filename);

        long written = 0;
        try (FileOutputStream fos = new FileOutputStream(target)) {
            byte[] buf = new byte[8192];
            int remaining = contentLength;
            while (remaining > 0) {
                int toRead = Math.min(buf.length, remaining);
                int n = in.read(buf, 0, toRead);
                if (n == -1) break;
                fos.write(buf, 0, n);
                written += n;
                remaining -= n;
            }
            fos.flush();
        }

        JSONObject resp = new JSONObject();
        try {
            resp.put("status", "ok");
            resp.put("filename", filename);
            resp.put("bytes", written);
        } catch (Exception ignored) {}

        byte[] json = resp.toString().getBytes("UTF-8");
        sendResponse(out, 200, "application/json", json, clientIp, "POST", "/api/files/upload");
    }

    private void handleFileDelete(OutputStream out, String relPath, String clientIp) throws IOException {
        File file = getSafeFile(relPath);
        JSONObject resp = new JSONObject();
        try {
            if (file != null && file.exists() && !file.equals(storageRoot) && deleteRecursive(file)) {
                resp.put("status", "ok");
            } else {
                resp.put("status", "error");
                resp.put("message", "Delete failed");
            }
        } catch (Exception ignored) {}
        sendResponse(out, 200, "application/json", resp.toString().getBytes("UTF-8"), clientIp, "POST", "/api/files/delete");
    }

    private boolean deleteRecursive(File f) {
        if (f.isDirectory()) {
            File[] children = f.listFiles();
            if (children != null) {
                for (File c : children) deleteRecursive(c);
            }
        }
        return f.delete();
    }

    private void handleFileMkdir(OutputStream out, String relPath, String name, String clientIp) throws IOException {
        File folder = getSafeFile(relPath);
        if (folder == null || !folder.exists()) folder = storageRoot;
        File newDir = new File(folder, name);
        JSONObject resp = new JSONObject();
        try {
            if (newDir.mkdirs()) {
                resp.put("status", "ok");
            } else {
                resp.put("status", "error");
            }
        } catch (Exception ignored) {}
        sendResponse(out, 200, "application/json", resp.toString().getBytes("UTF-8"), clientIp, "POST", "/api/files/mkdir");
    }

    private JSONObject handleFileStorage() {
        JSONObject res = new JSONObject();
        try {
            long total = storageRoot.getTotalSpace();
            long free = storageRoot.getFreeSpace();
            long used = total - free;
            res.put("status", "ok");
            res.put("total_bytes", total);
            res.put("free_bytes", free);
            res.put("used_bytes", used);
            res.put("free_str", formatBytes(free));
            res.put("used_str", formatBytes(used));
            res.put("total_str", formatBytes(total));
        } catch (Exception ignored) {}
        return res;
    }

    private String formatBytes(long bytes) {
        if (bytes <= 0) return "0 B";
        String[] units = new String[] { "B", "KB", "MB", "GB", "TB" };
        int digitGroups = (int) (Math.log10(bytes) / Math.log10(1024));
        return String.format(Locale.US, "%.1f %s", bytes / Math.pow(1024, digitGroups), units[digitGroups]);
    }

    private void handleSetWallpaper(OutputStream out, String relPath, String clientIp) throws IOException {
        File file = getSafeFile(relPath);
        JSONObject res = new JSONObject();
        if (file == null || !file.exists() || file.isDirectory()) {
            try { res.put("status", "error"); res.put("message", "File not found"); } catch (Exception ignored) {}
            sendResponse(out, 404, "application/json", res.toString().getBytes("UTF-8"), clientIp, "POST", "/api/files/set-wallpaper");
            return;
        }

        try {
            android.app.WallpaperManager wm = android.app.WallpaperManager.getInstance(context);
            try (FileInputStream fis = new FileInputStream(file)) {
                wm.setStream(fis);
            }
            res.put("status", "ok");
            res.put("message", "Wallpaper set successfully on Android host!");
            sendResponse(out, 200, "application/json", res.toString().getBytes("UTF-8"), clientIp, "POST", "/api/files/set-wallpaper");
            recordLog("SET_WALLPAPER", "/api/files/set-wallpaper", 200, file.length(), clientIp);
        } catch (Exception e) {
            try { res.put("status", "error"); res.put("message", e.getMessage()); } catch (Exception ignored) {}
            sendResponse(out, 500, "application/json", res.toString().getBytes("UTF-8"), clientIp, "POST", "/api/files/set-wallpaper");
        }
    }

    public File getSafeFile(String relPath) {
        if (relPath == null || relPath.isEmpty() || "/".equals(relPath)) {
            return storageRoot;
        }
        File target = new File(storageRoot, relPath);
        try {
            if (target.getCanonicalPath().startsWith(storageRoot.getCanonicalPath())) {
                return target;
            }
        } catch (Exception ignored) {}
        return storageRoot;
    }

    private String getRelativePath(File f) {
        try {
            String root = storageRoot.getCanonicalPath();
            String path = f.getCanonicalPath();
            if (path.equals(root)) return "";
            if (path.startsWith(root)) {
                return path.substring(root.length() + 1).replace(File.separatorChar, '/');
            }
        } catch (Exception ignored) {}
        return f.getName();
    }

    private Map<String, String> parseQuery(String query) {
        Map<String, String> map = new HashMap<>();
        if (query == null || query.isEmpty()) return map;
        String[] pairs = query.split("&");
        for (String pair : pairs) {
            int idx = pair.indexOf("=");
            try {
                if (idx > 0) {
                    map.put(URLDecoder.decode(pair.substring(0, idx), "UTF-8"),
                            URLDecoder.decode(pair.substring(idx + 1), "UTF-8"));
                } else if (idx == -1) {
                    map.put(URLDecoder.decode(pair, "UTF-8"), "");
                }
            } catch (Exception ignored) {}
        }
        return map;
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
        String statusText = status == 200 ? "OK" : (status == 206 ? "Partial Content" : (status == 404 ? "Not Found" : "Error"));
        StringBuilder header = new StringBuilder();
        header.append("HTTP/1.1 ").append(status).append(" ").append(statusText).append("\r\n");
        header.append("Content-Type: ").append(mime).append("\r\n");
        header.append("Content-Length: ").append(body.length).append("\r\n");
        header.append("Access-Control-Allow-Origin: *\r\n");
        header.append("Access-Control-Allow-Methods: GET, POST, OPTIONS, DELETE\r\n");
        header.append("Access-Control-Allow-Headers: Content-Type, Range\r\n");
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
        if (lower.endsWith(".txt") || lower.endsWith(".md")) return "text/plain; charset=utf-8";
        if (lower.endsWith(".pdf")) return "application/pdf";
        if (lower.endsWith(".mp4")) return "video/mp4";
        if (lower.endsWith(".mkv")) return "video/x-matroska";
        if (lower.endsWith(".mov")) return "video/quicktime";
        if (lower.endsWith(".webm")) return "video/webm";
        if (lower.endsWith(".mp3")) return "audio/mpeg";
        if (lower.endsWith(".wav")) return "audio/wav";
        if (lower.endsWith(".flac")) return "audio/flac";
        if (lower.endsWith(".zip")) return "application/zip";
        return "application/octet-stream";
    }

    // =========================================================================
    // WEBDAV RFC 4918 NATIVE ENGINE (Mount Phone as Network Drive on Windows/Mac)
    // =========================================================================
    private void handleWebDav(String method, String path, Map<String, String> headers, InputStream in, OutputStream out, int contentLength, String clientIp) throws IOException {
        String subPath = "";
        if (path.length() > 7) {
            subPath = path.substring(7); // after "/webdav"
        }
        if (subPath.startsWith("/")) subPath = subPath.substring(1);
        try {
            subPath = URLDecoder.decode(subPath, "UTF-8");
        } catch (Exception ignored) {}

        File target = subPath.isEmpty() ? storageRoot : new File(storageRoot, subPath);

        // Security check: path traversal prevention
        try {
            if (!target.getCanonicalPath().startsWith(storageRoot.getCanonicalPath())) {
                sendWebDavResponse(out, 403, "Forbidden", null, "Access denied".getBytes("UTF-8"), clientIp, method, path);
                return;
            }
        } catch (Exception e) {
            sendWebDavResponse(out, 400, "Bad Request", null, "Invalid path".getBytes("UTF-8"), clientIp, method, path);
            return;
        }

        // 1. OPTIONS
        if ("OPTIONS".equalsIgnoreCase(method)) {
            Map<String, String> davHeaders = new HashMap<>();
            davHeaders.put("DAV", "1, 2");
            davHeaders.put("MS-Author-Via", "DAV");
            davHeaders.put("Allow", "OPTIONS, GET, HEAD, POST, PUT, DELETE, TRACE, PROPFIND, PROPPATCH, MKCOL, COPY, MOVE, LOCK, UNLOCK");
            sendWebDavResponse(out, 200, "OK", davHeaders, new byte[0], clientIp, method, path);
            return;
        }

        // 2. PROPFIND
        if ("PROPFIND".equalsIgnoreCase(method)) {
            if (!target.exists()) {
                sendWebDavResponse(out, 404, "Not Found", null, "Resource not found".getBytes("UTF-8"), clientIp, method, path);
                return;
            }

            SimpleDateFormat httpDateFormat = new SimpleDateFormat("EEE, dd MMM yyyy HH:mm:ss 'GMT'", Locale.US);
            httpDateFormat.setTimeZone(TimeZone.getTimeZone("GMT"));

            String depth = headers.get("depth");
            if (depth == null) depth = "1";

            List<File> items = new ArrayList<>();
            items.add(target);
            if (!"0".equals(depth) && target.isDirectory()) {
                File[] children = target.listFiles();
                if (children != null) {
                    Arrays.sort(children, (a, b) -> {
                        if (a.isDirectory() && !b.isDirectory()) return -1;
                        if (!a.isDirectory() && b.isDirectory()) return 1;
                        return a.getName().compareToIgnoreCase(b.getName());
                    });
                    for (File c : children) items.add(c);
                }
            }

            StringBuilder sb = new StringBuilder();
            sb.append("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n");
            sb.append("<D:multistatus xmlns:D=\"DAV:\">\n");

            for (File f : items) {
                String relPath = f.getCanonicalPath().substring(storageRoot.getCanonicalPath().length()).replace('\\', '/');
                if (!relPath.startsWith("/")) relPath = "/" + relPath;
                if ("/".equals(relPath)) relPath = "";
                String href = "/webdav" + relPath;
                if (f.isDirectory() && !href.endsWith("/")) href += "/";

                sb.append("  <D:response>\n");
                sb.append("    <D:href>").append(escapeXml(href)).append("</D:href>\n");
                sb.append("    <D:propstat>\n");
                sb.append("      <D:prop>\n");
                sb.append("        <D:displayname>").append(escapeXml(f.getName().isEmpty() ? "webdav" : f.getName())).append("</D:displayname>\n");
                if (f.isDirectory()) {
                    sb.append("        <D:resourcetype><D:collection/></D:resourcetype>\n");
                } else {
                    sb.append("        <D:resourcetype/>\n");
                    sb.append("        <D:getcontentlength>").append(f.length()).append("</D:getcontentlength>\n");
                    sb.append("        <D:getcontenttype>").append(getMimeType(f.getName())).append("</D:getcontenttype>\n");
                }
                sb.append("        <D:getlastmodified>").append(httpDateFormat.format(new Date(f.lastModified()))).append("</D:getlastmodified>\n");
                sb.append("      </D:prop>\n");
                sb.append("      <D:status>HTTP/1.1 200 OK</D:status>\n");
                sb.append("    </D:propstat>\n");
                sb.append("  </D:response>\n");
            }
            sb.append("</D:multistatus>\n");

            byte[] xmlBytes = sb.toString().getBytes("UTF-8");
            Map<String, String> extra = new HashMap<>();
            extra.put("Content-Type", "application/xml; charset=utf-8");
            sendWebDavResponse(out, 207, "Multi-Status", extra, xmlBytes, clientIp, method, path);
            return;
        }

        // 3. MKCOL
        if ("MKCOL".equalsIgnoreCase(method)) {
            if (target.exists()) {
                sendWebDavResponse(out, 405, "Method Not Allowed", null, "Folder already exists".getBytes("UTF-8"), clientIp, method, path);
                return;
            }
            File parent = target.getParentFile();
            if (parent != null && !parent.exists()) {
                sendWebDavResponse(out, 409, "Conflict", null, "Parent folder does not exist".getBytes("UTF-8"), clientIp, method, path);
                return;
            }
            if (target.mkdir()) {
                sendWebDavResponse(out, 201, "Created", null, new byte[0], clientIp, method, path);
            } else {
                sendWebDavResponse(out, 500, "Internal Server Error", null, "Failed to create folder".getBytes("UTF-8"), clientIp, method, path);
            }
            return;
        }

        // 4. PUT
        if ("PUT".equalsIgnoreCase(method)) {
            File parent = target.getParentFile();
            if (parent != null && !parent.exists()) parent.mkdirs();
            boolean existed = target.exists();
            try (FileOutputStream fos = new FileOutputStream(target)) {
                if (contentLength > 0) {
                    byte[] buf = new byte[8192];
                    long remaining = contentLength;
                    while (remaining > 0) {
                        int toRead = (int) Math.min(buf.length, remaining);
                        int read = in.read(buf, 0, toRead);
                        if (read == -1) break;
                        fos.write(buf, 0, read);
                        remaining -= read;
                    }
                }
            }
            sendWebDavResponse(out, existed ? 204 : 201, existed ? "No Content" : "Created", null, new byte[0], clientIp, method, path);
            return;
        }

        // 5. DELETE
        if ("DELETE".equalsIgnoreCase(method)) {
            if (!target.exists()) {
                sendWebDavResponse(out, 404, "Not Found", null, "Resource not found".getBytes("UTF-8"), clientIp, method, path);
                return;
            }
            deleteRecursively(target);
            sendWebDavResponse(out, 204, "No Content", null, new byte[0], clientIp, method, path);
            return;
        }

        // 6. MOVE / COPY
        if ("MOVE".equalsIgnoreCase(method) || "COPY".equalsIgnoreCase(method)) {
            String dest = headers.get("destination");
            if (dest == null || dest.isEmpty()) {
                sendWebDavResponse(out, 400, "Bad Request", null, "Destination header missing".getBytes("UTF-8"), clientIp, method, path);
                return;
            }
            try {
                if (dest.startsWith("http://") || dest.startsWith("https://")) {
                    URI u = new URI(dest);
                    dest = u.getPath();
                }
            } catch (Exception ignored) {}
            if (dest.startsWith("/webdav")) dest = dest.substring(7);
            if (dest.startsWith("/")) dest = dest.substring(1);
            try { dest = URLDecoder.decode(dest, "UTF-8"); } catch (Exception ignored) {}

            File destFile = new File(storageRoot, dest);
            try {
                if (!destFile.getCanonicalPath().startsWith(storageRoot.getCanonicalPath())) {
                    sendWebDavResponse(out, 403, "Forbidden", null, "Access denied".getBytes("UTF-8"), clientIp, method, path);
                    return;
                }
            } catch (Exception e) {
                sendWebDavResponse(out, 400, "Bad Request", null, "Invalid destination path".getBytes("UTF-8"), clientIp, method, path);
                return;
            }

            File parent = destFile.getParentFile();
            if (parent != null && !parent.exists()) parent.mkdirs();

            boolean destExisted = destFile.exists();
            if ("MOVE".equalsIgnoreCase(method)) {
                if (destExisted) deleteRecursively(destFile);
                boolean ok = target.renameTo(destFile);
                if (!ok) {
                    copyRecursively(target, destFile);
                    deleteRecursively(target);
                }
                sendWebDavResponse(out, destExisted ? 204 : 201, destExisted ? "No Content" : "Created", null, new byte[0], clientIp, method, path);
            } else {
                if (destExisted) deleteRecursively(destFile);
                copyRecursively(target, destFile);
                sendWebDavResponse(out, destExisted ? 204 : 201, destExisted ? "No Content" : "Created", null, new byte[0], clientIp, method, path);
            }
            return;
        }

        // 7. GET / HEAD
        if ("GET".equalsIgnoreCase(method) || "HEAD".equalsIgnoreCase(method)) {
            if (!target.exists()) {
                sendWebDavResponse(out, 404, "Not Found", null, "Resource not found".getBytes("UTF-8"), clientIp, method, path);
                return;
            }
            if (target.isDirectory()) {
                StringBuilder html = new StringBuilder();
                html.append("<!DOCTYPE html><html><head><title>WebDAV: /").append(escapeXml(subPath)).append("</title></head>");
                html.append("<body style=\"font-family:sans-serif; background:#0B0E14; color:#F1F5F9; padding:20px;\">");
                html.append("<h2>📁 WebDAV Folder: /").append(escapeXml(subPath)).append("</h2><ul>");
                File[] children = target.listFiles();
                if (children != null) {
                    for (File c : children) {
                        String name = c.getName() + (c.isDirectory() ? "/" : "");
                        html.append("<li><a style=\"color:#38BDF8;\" href=\"").append(escapeXml(name)).append("\">").append(escapeXml(name)).append("</a></li>");
                    }
                }
                html.append("</ul></body></html>");
                byte[] htmlBytes = html.toString().getBytes("UTF-8");
                Map<String, String> extra = new HashMap<>();
                extra.put("Content-Type", "text/html; charset=utf-8");
                sendWebDavResponse(out, 200, "OK", extra, "HEAD".equalsIgnoreCase(method) ? new byte[0] : htmlBytes, clientIp, method, path);
                return;
            }

            long fileLength = target.length();
            String mime = getMimeType(target.getName());
            Map<String, String> extra = new HashMap<>();
            extra.put("Content-Type", mime);

            if ("HEAD".equalsIgnoreCase(method)) {
                extra.put("Content-Length", String.valueOf(fileLength));
                sendWebDavResponse(out, 200, "OK", extra, new byte[0], clientIp, method, path);
                return;
            }

            try (FileInputStream fis = new FileInputStream(target)) {
                StringBuilder header = new StringBuilder();
                header.append("HTTP/1.1 200 OK\r\n");
                header.append("Content-Type: ").append(mime).append("\r\n");
                header.append("Content-Length: ").append(fileLength).append("\r\n");
                header.append("DAV: 1, 2\r\n");
                header.append("MS-Author-Via: DAV\r\n");
                header.append("Access-Control-Allow-Origin: *\r\n");
                header.append("Connection: close\r\n\r\n");
                out.write(header.toString().getBytes("UTF-8"));

                byte[] buf = new byte[8192];
                int n;
                while ((n = fis.read(buf)) != -1) {
                    out.write(buf, 0, n);
                }
                out.flush();
                recordLog(method, path, 200, fileLength, clientIp);
            }
            return;
        }

        // 8. LOCK / UNLOCK (Compatibility for Windows WebClient / Office)
        if ("LOCK".equalsIgnoreCase(method)) {
            String lockXml = "<?xml version=\"1.0\" encoding=\"utf-8\" ?>\n" +
                "<D:prop xmlns:D=\"DAV:\">\n" +
                "  <D:lockdiscovery>\n" +
                "    <D:activelock>\n" +
                "      <D:locktype><D:write/></D:locktype>\n" +
                "      <D:lockscope><D:exclusive/></D:lockscope>\n" +
                "      <D:depth>0</D:depth>\n" +
                "      <D:timeout>Second-3600</D:timeout>\n" +
                "      <D:locktoken><D:href>urn:uuid:omnihost-dav-lock</D:href></D:locktoken>\n" +
                "    </D:activelock>\n" +
                "  </D:lockdiscovery>\n" +
                "</D:prop>";
            Map<String, String> extra = new HashMap<>();
            extra.put("Lock-Token", "<urn:uuid:omnihost-dav-lock>");
            extra.put("Content-Type", "application/xml; charset=utf-8");
            sendWebDavResponse(out, 200, "OK", extra, lockXml.getBytes("UTF-8"), clientIp, method, path);
            return;
        }

        if ("UNLOCK".equalsIgnoreCase(method)) {
            sendWebDavResponse(out, 204, "No Content", null, new byte[0], clientIp, method, path);
            return;
        }

        sendWebDavResponse(out, 501, "Not Implemented", null, new byte[0], clientIp, method, path);
    }

    private void sendWebDavResponse(OutputStream out, int status, String statusText, Map<String, String> extraHeaders, byte[] body, String clientIp, String method, String path) throws IOException {
        StringBuilder header = new StringBuilder();
        header.append("HTTP/1.1 ").append(status).append(" ").append(statusText).append("\r\n");
        if (body != null && body.length > 0) {
            String mime = "application/xml; charset=utf-8";
            if (extraHeaders != null && extraHeaders.containsKey("Content-Type")) {
                mime = extraHeaders.get("Content-Type");
            }
            header.append("Content-Type: ").append(mime).append("\r\n");
            header.append("Content-Length: ").append(body.length).append("\r\n");
        } else {
            header.append("Content-Length: 0\r\n");
        }
        header.append("DAV: 1, 2\r\n");
        header.append("MS-Author-Via: DAV\r\n");
        header.append("Access-Control-Allow-Origin: *\r\n");
        header.append("Access-Control-Allow-Methods: OPTIONS, GET, HEAD, POST, PUT, DELETE, TRACE, PROPFIND, PROPPATCH, MKCOL, COPY, MOVE, LOCK, UNLOCK\r\n");
        header.append("Access-Control-Allow-Headers: Content-Type, Depth, Destination, If, Lock-Token, Range\r\n");
        if (extraHeaders != null) {
            for (Map.Entry<String, String> e : extraHeaders.entrySet()) {
                if (!e.getKey().equalsIgnoreCase("Content-Type")) {
                    header.append(e.getKey()).append(": ").append(e.getValue()).append("\r\n");
                }
            }
        }
        header.append("Connection: close\r\n\r\n");

        out.write(header.toString().getBytes("UTF-8"));
        if (body != null && body.length > 0) {
            out.write(body);
        }
        out.flush();

        recordLog(method, path, status, body != null ? body.length : 0, clientIp);
    }

    private String escapeXml(String s) {
        if (s == null) return "";
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;").replace("'", "&apos;");
    }

    private void deleteRecursively(File f) {
        if (f == null || !f.exists()) return;
        if (f.isDirectory()) {
            File[] files = f.listFiles();
            if (files != null) {
                for (File child : files) deleteRecursively(child);
            }
        }
        f.delete();
    }

    private void copyRecursively(File src, File dest) throws IOException {
        if (src.isDirectory()) {
            if (!dest.exists()) dest.mkdirs();
            File[] files = src.listFiles();
            if (files != null) {
                for (File child : files) {
                    copyRecursively(child, new File(dest, child.getName()));
                }
            }
        } else {
            try (InputStream is = new FileInputStream(src); OutputStream os = new FileOutputStream(dest)) {
                byte[] buf = new byte[8192];
                int n;
                while ((n = is.read(buf)) != -1) os.write(buf, 0, n);
            }
        }
    }
}
