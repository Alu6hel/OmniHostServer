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

    private File getSafeFile(String relPath) {
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
}
