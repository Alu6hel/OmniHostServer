package com.omnihost.pro;

import android.content.Context;
import java.io.*;
import java.net.*;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.*;

public class AndroidFtpServer {
    private final Context context;
    private final int port;
    private ServerSocket serverSocket;
    private ExecutorService threadPool;
    private volatile boolean isRunning = false;
    private File mountDir;
    private String username = "admin";
    private String password = "omnihost";
    private boolean allowAnonymous = true;

    // Event listener for UI
    public interface FtpEventListener {
        void onFtpEvent(String eventType, String details);
    }
    private FtpEventListener eventListener;

    public AndroidFtpServer(Context context, int port) {
        this.context = context;
        this.port = port;
        this.mountDir = new File(context.getFilesDir(), "ftp_root");
        if (!this.mountDir.exists()) this.mountDir.mkdirs();
    }

    public void setEventListener(FtpEventListener listener) {
        this.eventListener = listener;
    }

    public synchronized void setMountDir(File dir) {
        if (dir != null) {
            this.mountDir = dir;
            if (!this.mountDir.exists()) this.mountDir.mkdirs();
        }
    }

    public File getMountDir() {
        return mountDir;
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
                    threadPool.submit(() -> handleFtpClient(client));
                } catch (IOException e) {
                    if (!isRunning) break;
                }
            }
        }, "OmniHostFtpListener").start();

        notifyEvent("START", "WiFi FTP Server active on port " + port);
    }

    public synchronized void stop() {
        isRunning = false;
        if (serverSocket != null && !serverSocket.isClosed()) {
            try { serverSocket.close(); } catch (IOException ignored) {}
        }
        if (threadPool != null && !threadPool.isShutdown()) {
            threadPool.shutdownNow();
        }
        notifyEvent("STOP", "WiFi FTP Server stopped");
    }

    public boolean isRunning() {
        return isRunning;
    }

    private void notifyEvent(String type, String details) {
        if (eventListener != null) {
            eventListener.onFtpEvent(type, details);
        }
    }

    private void handleFtpClient(Socket client) {
        String clientIp = client.getInetAddress() != null ? client.getInetAddress().getHostAddress() : "unknown";
        notifyEvent("CONNECT", "FTP Client connected from " + clientIp);

        try (
            BufferedReader reader = new BufferedReader(new InputStreamReader(client.getInputStream()));
            BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(client.getOutputStream()))
        ) {
            writer.write("220 OmniHost Pro High-Speed WiFi FTP Server Ready\r\n");
            writer.flush();

            File currentDir = mountDir;
            ServerSocket passiveServer = null;
            String user = "";
            boolean isAuthenticated = false;
            String activeHost = null;
            int activePort = -1;
            boolean useActive = false;

            String line;
            while ((line = reader.readLine()) != null) {
                line = line.trim();
                if (line.isEmpty()) continue;

                String cmd = line;
                String arg = "";
                int space = line.indexOf(' ');
                if (space > 0) {
                    cmd = line.substring(0, space).toUpperCase(Locale.US);
                    arg = line.substring(space + 1).trim();
                } else {
                    cmd = cmd.toUpperCase(Locale.US);
                }

                if ("QUIT".equals(cmd)) {
                    writer.write("221 Service closing control connection. Goodbye.\r\n");
                    writer.flush();
                    break;
                } else if ("USER".equals(cmd)) {
                    user = arg;
                    if (allowAnonymous && ("anonymous".equalsIgnoreCase(user) || user.isEmpty())) {
                        isAuthenticated = true;
                        writer.write("230 Anonymous user logged in.\r\n");
                    } else {
                        writer.write("331 User name okay, need password.\r\n");
                    }
                    writer.flush();
                } else if ("PASS".equals(cmd)) {
                    if (isAuthenticated || (username.equals(user) && password.equals(arg))) {
                        isAuthenticated = true;
                        writer.write("230 User logged in, proceed.\r\n");
                    } else {
                        writer.write("530 Not logged in.\r\n");
                    }
                    writer.flush();
                } else if ("SYST".equals(cmd)) {
                    writer.write("215 UNIX Type: L8\r\n");
                    writer.flush();
                } else if ("FEAT".equals(cmd)) {
                    writer.write("211-Features:\r\n PASV\r\n EPSV\r\n UTF8\r\n211 End\r\n");
                    writer.flush();
                } else if ("PWD".equals(cmd)) {
                    String rel = currentDir.getAbsolutePath().replace(mountDir.getAbsolutePath(), "");
                    if (rel.isEmpty()) rel = "/";
                    writer.write("257 \"" + rel + "\" is current directory.\r\n");
                    writer.flush();
                } else if ("TYPE".equals(cmd)) {
                    writer.write("200 Type set to " + arg + ".\r\n");
                    writer.flush();
                } else if ("PORT".equals(cmd)) {
                    try {
                        String[] parts = arg.split(",");
                        if (parts.length == 6) {
                            activeHost = parts[0] + "." + parts[1] + "." + parts[2] + "." + parts[3];
                            activePort = (Integer.parseInt(parts[4]) << 8) + Integer.parseInt(parts[5]);
                            useActive = true;
                            writer.write("200 PORT command successful.\r\n");
                        } else {
                            writer.write("501 Syntax error in parameters.\r\n");
                        }
                    } catch (Exception e) {
                        writer.write("501 Syntax error in parameters.\r\n");
                    }
                    writer.flush();
                } else if ("PASV".equals(cmd)) {
                    if (passiveServer != null && !passiveServer.isClosed()) {
                        try { passiveServer.close(); } catch (Exception ignored) {}
                    }
                    try {
                        passiveServer = new ServerSocket(2122);
                    } catch (Exception e) {
                        passiveServer = new ServerSocket(0);
                    }
                    useActive = false;
                    int pasvPort = passiveServer.getLocalPort();
                    String localIp = client.getLocalAddress().getHostAddress();
                    if ("0.0.0.0".equals(localIp) || "127.0.0.1".equals(localIp)) {
                        localIp = "127.0.0.1";
                    }
                    String[] ipParts = localIp.split("\\.");
                    int p1 = pasvPort / 256;
                    int p2 = pasvPort % 256;
                    writer.write(String.format(Locale.US, "227 Entering Passive Mode (%s,%s,%s,%s,%d,%d).\r\n",
                            ipParts[0], ipParts[1], ipParts[2], ipParts[3], p1, p2));
                    writer.flush();
                } else if ("EPSV".equals(cmd)) {
                    if (passiveServer != null && !passiveServer.isClosed()) {
                        try { passiveServer.close(); } catch (Exception ignored) {}
                    }
                    try {
                        passiveServer = new ServerSocket(2122);
                    } catch (Exception e) {
                        passiveServer = new ServerSocket(0);
                    }
                    useActive = false;
                    int pasvPort = passiveServer.getLocalPort();
                    writer.write(String.format(Locale.US, "229 Entering Extended Passive Mode (|||%d|)\r\n", pasvPort));
                    writer.flush();
                } else if ("LIST".equals(cmd) || "NLST".equals(cmd)) {
                    if (passiveServer == null && !useActive) {
                        writer.write("425 Use PASV or PORT first.\r\n");
                        writer.flush();
                        continue;
                    }
                    writer.write("150 Opening ASCII mode data connection for file list.\r\n");
                    writer.flush();

                    try (Socket dataSocket = useActive ? new Socket(activeHost, activePort) : passiveServer.accept();
                         BufferedWriter dataWriter = new BufferedWriter(new OutputStreamWriter(dataSocket.getOutputStream()))) {
                        File[] files = currentDir.listFiles();
                        if (files != null) {
                            SimpleDateFormat sdf = new SimpleDateFormat("MMM dd HH:mm", Locale.US);
                            for (File f : files) {
                                if ("NLST".equals(cmd)) {
                                    dataWriter.write(f.getName() + "\r\n");
                                } else {
                                    String perms = f.isDirectory() ? "drwxr-xr-x" : "-rw-r--r--";
                                    String lineOut = String.format(Locale.US, "%s 1 owner group %10d %s %s\r\n",
                                            perms, f.length(), sdf.format(new Date(f.lastModified())), f.getName());
                                    dataWriter.write(lineOut);
                                }
                            }
                        }
                        dataWriter.flush();
                    } finally {
                        if (passiveServer != null) {
                            try { passiveServer.close(); } catch (Exception ignored) {}
                            passiveServer = null;
                        }
                        useActive = false;
                    }
                    writer.write("226 Transfer complete.\r\n");
                    writer.flush();
                } else if ("CWD".equals(cmd)) {
                    File target = "/".equals(arg) ? mountDir : new File(currentDir, arg);
                    if (target.exists() && target.isDirectory() && target.getAbsolutePath().startsWith(mountDir.getAbsolutePath())) {
                        currentDir = target;
                        writer.write("250 Directory successfully changed.\r\n");
                    } else {
                        writer.write("550 Failed to change directory.\r\n");
                    }
                    writer.flush();
                } else if ("CDUP".equals(cmd)) {
                    File parent = currentDir.getParentFile();
                    if (parent != null && parent.getAbsolutePath().startsWith(mountDir.getAbsolutePath())) {
                        currentDir = parent;
                        writer.write("200 Directory changed to parent.\r\n");
                    } else {
                        currentDir = mountDir;
                        writer.write("200 Directory changed to root.\r\n");
                    }
                    writer.flush();
                } else if ("RETR".equals(cmd)) {
                    File target = new File(currentDir, arg);
                    if (!target.exists() || target.isDirectory()) {
                        writer.write("550 File not found.\r\n");
                        writer.flush();
                        continue;
                    }
                    if (passiveServer == null && !useActive) {
                        writer.write("425 Use PASV or PORT first.\r\n");
                        writer.flush();
                        continue;
                    }
                    writer.write("150 Opening binary data connection for " + arg + ".\r\n");
                    writer.flush();

                    try (Socket dataSocket = useActive ? new Socket(activeHost, activePort) : passiveServer.accept();
                         InputStream fileIn = new FileInputStream(target);
                         OutputStream dataOut = dataSocket.getOutputStream()) {
                        byte[] buf = new byte[16384];
                        int n;
                        while ((n = fileIn.read(buf)) != -1) {
                            dataOut.write(buf, 0, n);
                        }
                        dataOut.flush();
                    } finally {
                        if (passiveServer != null) {
                            try { passiveServer.close(); } catch (Exception ignored) {}
                            passiveServer = null;
                        }
                        useActive = false;
                    }
                    writer.write("226 Transfer complete.\r\n");
                    writer.flush();
                    notifyEvent("DOWNLOAD", "Downloaded: " + target.getName() + " (" + target.length() + " B)");
                } else if ("STOR".equals(cmd)) {
                    File target = new File(currentDir, arg);
                    if (passiveServer == null && !useActive) {
                        writer.write("425 Use PASV or PORT first.\r\n");
                        writer.flush();
                        continue;
                    }
                    writer.write("150 Ok to send data.\r\n");
                    writer.flush();

                    long uploadedBytes = 0;
                    try (Socket dataSocket = useActive ? new Socket(activeHost, activePort) : passiveServer.accept();
                         InputStream dataIn = dataSocket.getInputStream();
                         OutputStream fileOut = new FileOutputStream(target)) {
                        byte[] buf = new byte[16384];
                        int n;
                        while ((n = dataIn.read(buf)) != -1) {
                            fileOut.write(buf, 0, n);
                            uploadedBytes += n;
                        }
                        fileOut.flush();
                    } finally {
                        if (passiveServer != null) {
                            try { passiveServer.close(); } catch (Exception ignored) {}
                            passiveServer = null;
                        }
                        useActive = false;
                    }
                    writer.write("226 File successfully uploaded.\r\n");
                    writer.flush();
                    notifyEvent("UPLOAD", "Uploaded: " + target.getName() + " (" + uploadedBytes + " B)");
                } else if ("DELE".equals(cmd)) {
                    File target = new File(currentDir, arg);
                    if (target.exists() && target.delete()) {
                        writer.write("250 File deleted.\r\n");
                        notifyEvent("DELETE", "Deleted file: " + target.getName());
                    } else {
                        writer.write("550 Delete operation failed.\r\n");
                    }
                    writer.flush();
                } else if ("MKD".equals(cmd)) {
                    File target = new File(currentDir, arg);
                    if (!target.exists() && target.mkdirs()) {
                        writer.write("257 \"" + arg + "\" created.\r\n");
                        notifyEvent("MKDIR", "Created directory: " + target.getName());
                    } else {
                        writer.write("550 Create directory failed.\r\n");
                    }
                    writer.flush();
                } else {
                    writer.write("502 Command not implemented.\r\n");
                    writer.flush();
                }
            }

            if (passiveServer != null && !passiveServer.isClosed()) {
                passiveServer.close();
            }

        } catch (Exception ignored) {
        } finally {
            try { client.close(); } catch (Exception ignored) {}
            notifyEvent("DISCONNECT", "FTP Client disconnected from " + clientIp);
        }
    }

    private String getLocalIpAddress() {
        try {
            Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
            while (interfaces.hasMoreElements()) {
                NetworkInterface iface = interfaces.nextElement();
                Enumeration<InetAddress> addresses = iface.getInetAddresses();
                while (addresses.hasMoreElements()) {
                    InetAddress addr = addresses.nextElement();
                    if (!addr.isLoopbackAddress() && addr instanceof Inet4Address) {
                        return addr.getHostAddress();
                    }
                }
            }
        } catch (Exception ignored) {}
        return "127.0.0.1";
    }
}
