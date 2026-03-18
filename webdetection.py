#!/usr/bin/env python3
# ===========================================================
#        WEB DETECTION v3.0 — GUI Terminal for Kali Linux
#        Author: Bhavya Sehgal
#        Features: Live streaming output, parallel scans,
#                  fast flags, risk highlighting, reports
# ===========================================================

import tkinter as tk
from tkinter import ttk, scrolledtext, simpledialog, filedialog
import subprocess
import threading
import shlex
import shutil
import datetime
import os
import queue
import concurrent.futures
import re

# ================== THEMES ==================
THEMES = {
    'Light': {
        'bg': '#f4f6f9', 'text_bg': '#ffffff', 'button_bg': '#1A7F3B',
        'accent': '#0D47A1', 'text': '#2c2c2c', 'sidebar_bg': '#e3e8f0',
        'frame_bg': '#ffffff', 'button_hover': '#145C2B',
        'success_bg': '#c8e6c9', 'success_fg': '#1b5e20',
        'error_bg': '#ffcdd2', 'error_fg': '#b71c1c',
        'header_fg': '#0D47A1', 'sep': '#c0c8d8',
        'log_bg': '#f0f4ff', 'log_fg': '#1a237e',
        'tag_bg': '#e8eaf6', 'stream_bg': '#fafafa',
    },
    'Dark': {
        'bg': '#1a1b2e', 'text_bg': '#16213e', 'button_bg': '#1E90FF',
        'accent': '#0f3460', 'text': '#e0e0e0', 'sidebar_bg': '#16213e',
        'frame_bg': '#0f3460', 'button_hover': '#e94560',
        'success_bg': '#4CAF50', 'success_fg': '#ffffff',
        'error_bg': '#e94560', 'error_fg': '#ffffff',
        'header_fg': '#1E90FF', 'sep': '#0f3460',
        'log_bg': '#0a0a1a', 'log_fg': '#00d4ff',
        'tag_bg': '#0f3460', 'stream_bg': '#0d0d1a',
    },
    'Solarized': {
        'bg': '#fdf6e3', 'text_bg': '#eee8d5', 'button_bg': '#268bd2',
        'accent': '#b58900', 'text': '#586e75', 'sidebar_bg': '#eee8d5',
        'frame_bg': '#fdf6e3', 'button_hover': '#2aa198',
        'success_bg': '#859900', 'success_fg': '#fdf6e3',
        'error_bg': '#dc322f', 'error_fg': '#fdf6e3',
        'header_fg': '#268bd2', 'sep': '#d3cbb8',
        'log_bg': '#e8e2d0', 'log_fg': '#b58900',
        'tag_bg': '#eee8d5', 'stream_bg': '#fdf6e3',
    },
    'Dracula': {
        'bg': '#282a36', 'text_bg': '#1e1f29', 'button_bg': '#50fa7b',
        'accent': '#6272a4', 'text': '#f8f8f2', 'sidebar_bg': '#21222c',
        'frame_bg': '#44475a', 'button_hover': '#ff79c6',
        'success_bg': '#50fa7b', 'success_fg': '#282a36',
        'error_bg': '#ff5555', 'error_fg': '#f8f8f2',
        'header_fg': '#bd93f9', 'sep': '#44475a',
        'log_bg': '#191a21', 'log_fg': '#50fa7b',
        'tag_bg': '#44475a', 'stream_bg': '#1e1f29',
    },
    'Cyberpunk': {
        'bg': '#0d0d0d', 'text_bg': '#111111', 'button_bg': '#ff00ff',
        'accent': '#00ffff', 'text': '#f0f0f0', 'sidebar_bg': '#0a0a0a',
        'frame_bg': '#1a001a', 'button_hover': '#00ffff',
        'success_bg': '#00ff41', 'success_fg': '#000000',
        'error_bg': '#ff003c', 'error_fg': '#ffffff',
        'header_fg': '#ff00ff', 'sep': '#ff00ff',
        'log_bg': '#000000', 'log_fg': '#00ff41',
        'tag_bg': '#1a001a', 'stream_bg': '#050505',
    },
}
current_theme = "Dark"

# ================== RISK PATTERNS ==================
# (regex, tag_name) — matched line gets coloured in stream output
RISK_PATTERNS = [
    (r'\bopen\b',                          'risk_open'),
    (r'\b(VULNERABLE|EXPLOIT|CVE-\d)',     'risk_vuln'),
    (r'\b(error|failed|refused|denied)\b', 'risk_error'),
    (r'\b(filtered|closed)\b',             'risk_closed'),
    (r'\b(http|https|ftp|ssh|smtp|rdp)\b', 'risk_proto'),
    (r'\b(\d{1,3}\.){3}\d{1,3}\b',        'risk_ip'),
    (r'^\[.*?\]',                          'risk_bracket'),
]

# ================== TOOL DEFINITIONS ==================
# (name, cmd_template, needs_input, prompt, category, description, fast_flag)
# fast_flag = extra args prepended when "Fast Mode" is ON
TOOLS = [
    # ── System ──────────────────────────────────────────────────────
    ("System Info",          "uname -a",                                              False, "",                                         "System",  "Kernel & OS details",               ""),
    ("Disk Usage",           "df -h",                                                 False, "",                                         "System",  "Free/used disk space",              ""),
    ("Memory Usage",         "free -h",                                               False, "",                                         "System",  "RAM and swap info",                 ""),
    ("Running Processes",    "ps aux --sort=-%cpu | head -20",                        False, "",                                         "System",  "Top CPU processes",                 ""),
    ("Network Interfaces",   "ip a",                                                  False, "",                                         "System",  "All IP interfaces",                 ""),
    ("Open Files/Sockets",   "lsof -i -n -P | head -40",                             False, "",                                         "System",  "Open network connections",          ""),
    # ── Network ─────────────────────────────────────────────────────
    ("Routing Table",        "ip route",                                              False, "",                                         "Network", "Network routing info",              ""),
    ("ARP Scan",             "arp-scan --localnet",                                   False, "",                                         "Network", "Devices on local network",          ""),
    ("Local Port Monitor",   "ss -tulnp",                                             False, "",                                         "Network", "Listening ports & PIDs",            ""),
    ("MAC Address Viewer",   "ip link",                                               False, "",                                         "Network", "Interfaces & MACs",                 ""),
    ("Netstat Summary",      "ss -s",                                                 False, "",                                         "Network", "Socket statistics summary",         ""),
    ("WiFi Networks",        "nmcli dev wifi list",                                   False, "",                                         "Network", "Nearby WiFi SSIDs",                 ""),
    # ── Recon ───────────────────────────────────────────────────────
    ("Ping Host",            "ping -c 4 {target}",                                   True,  "Enter IP or domain:",                      "Recon",   "ICMP connectivity check",           "-c 2"),
    ("Fast Ping",            "fping -a -g {target}",                                 True,  "Enter subnet (e.g. 192.168.1.0/24):",      "Recon",   "Ping sweep — all live hosts",        ""),
    ("Traceroute",           "traceroute -m 15 {target}",                            True,  "Enter target:",                            "Recon",   "Packet path (max 15 hops)",         "-m 8"),
    ("Whois Recon",          "whois {target}",                                        True,  "Enter domain:",                            "Recon",   "Domain registration info",          ""),
    ("DNS Enumeration",      "dig {target} ANY +noall +answer",                      True,  "Enter domain:",                            "Recon",   "All DNS records (fast)",            ""),
    ("DNS Brute Force",      "fierce --domain {target}",                             True,  "Enter domain:",                            "Recon",   "Subdomain brute force",             ""),
    ("Reverse DNS",          "dig -x {target} +short",                               True,  "Enter IP address:",                        "Recon",   "PTR record lookup",                 ""),
    ("Subdomain Finder",     "subfinder -d {target} -silent",                        True,  "Enter domain:",                            "Recon",   "Passive subdomain enumeration",     ""),
    ("HTTP Headers",         "curl -sI --max-time 10 http://{target}",               True,  "Enter target (no http://):",               "Recon",   "Server response headers",           "--max-time 5"),
    ("SSL Cert Info",        "echo | openssl s_client -connect {target}:443 -brief 2>/dev/null | openssl x509 -noout -text 2>/dev/null | head -30", True, "Enter domain:", "Recon", "TLS certificate details", ""),
    # ── Scan ────────────────────────────────────────────────────────
    ("Network Discovery",    "nmap -sn --min-rate 1000 {target}",                    True,  "Enter subnet (e.g. 192.168.1.0/24):",      "Scan",    "Live hosts — no port scan",         "--min-rate 5000"),
    ("Nmap Fast Scan",       "nmap -T4 -F --open {target}",                          True,  "Enter target:",                            "Scan",    "Top 100 ports, fast",               "-T5 --min-rate 5000"),
    ("Nmap Basic Scan",      "nmap -T4 --open {target}",                             True,  "Enter target:",                            "Scan",    "Top 1000 ports",                    "-T5 --min-rate 3000"),
    ("Nmap Full Port Scan",  "nmap -T4 -p- --open --min-rate 1000 {target}",         True,  "Enter target:",                            "Scan",    "All 65535 ports",                   "-T5 --min-rate 5000"),
    ("Nmap Intense Scan",    "nmap -A -T4 {target}",                                 True,  "Enter target:",                            "Scan",    "OS + scripts + traceroute",         "-T5"),
    ("Service Version Scan", "nmap -sV -T4 --open {target}",                         True,  "Enter target:",                            "Scan",    "Detect service versions",           "-T5 --min-rate 3000"),
    ("UDP Scan",             "nmap -sU -T4 --top-ports 50 {target}",                 True,  "Enter target:",                            "Scan",    "Top 50 UDP ports",                  "-T5"),
    ("Vuln Assessment",      "nmap --script vuln -T4 {target}",                      True,  "Enter target:",                            "Scan",    "NSE vulnerability scripts",         "-T5"),
    ("SMB Enumeration",      "nmap --script smb-enum-shares,smb-enum-users -p 445 {target}", True, "Enter target:", "Scan", "SMB shares & users", ""),
    # ── Web ─────────────────────────────────────────────────────────
    ("Website Tech Scan",    "whatweb -a 3 http://{target}",                         True,  "Enter website (no http://):",              "Web",     "CMS, server, plugins",              "-a 1"),
    ("Nikto Web Scan",       "nikto -h {target} -maxtime 120",                       True,  "Enter target URL or IP:",                  "Web",     "Web server vulnerabilities",        "-maxtime 30 -Tuning 13"),
    ("Dir Brute Force",      "gobuster dir -u http://{target} -w /usr/share/wordlists/dirb/common.txt -t 50 -q", True, "Enter target (no http://):", "Web", "Hidden directories (50 threads)", "-t 100"),
    ("SQL Injection Test",   "sqlmap -u {target} --batch --level=1 --risk=1 --threads=4", True, "Enter URL with parameter:", "Web", "SQLi check (4 threads)", "--threads=8 --level=1"),
    ("XSS Scanner",          "dalfox url http://{target} --silence",                 True,  "Enter target URL:",                        "Web",     "XSS vulnerability scan",            ""),
    ("LFI Scanner",          "ffuf -u http://{target}/FUZZ -w /usr/share/wordlists/wfuzz/Injections/Traversal.txt -mc 200 -t 50 -s", True, "Enter target (no http://):", "Web", "Local file inclusion test", "-t 100"),
    ("WordPress Scan",       "wpscan --url http://{target} --enumerate vp,u --max-threads 10", True, "Enter WordPress site (no http://):", "Web", "WP plugins, themes, users", "--max-threads 20"),
    ("Robots & Sitemap",     "curl -sL --max-time 10 http://{target}/robots.txt && echo '---SITEMAP---' && curl -sL --max-time 10 http://{target}/sitemap.xml | head -40", True, "Enter target (no http://):", "Web", "robots.txt & sitemap.xml", ""),
]

CATEGORIES = ["All", "System", "Network", "Recon", "Scan", "Web"]

# ================== STATE ==================
current_theme = "Dark"
active_filter  = "All"
fast_mode      = tk.BooleanVar if False else None   # set after root created
parallel_jobs  = []          # list of running threads
reports_dir    = os.path.expanduser("~/web_detection_reports")
os.makedirs(reports_dir, exist_ok=True)

root         = None
sidebar      = None
main_frame   = None
header_label = None
filter_frame = None
grid_outer   = None
grid_frame   = None
log_frame    = None
log_text     = None
log_label    = None
status_var   = None
status_bar   = None
theme_label  = None
sidebar_title= None
theme_buttons= {}
filter_btns  = []
canvas       = None
fast_var     = None
parallel_var = None
active_streams = {}   # name -> StreamWindow


# ================== HELPERS ==================
def get_theme():
    return THEMES[current_theme]

def tool_is_available(cmd_template):
    binary = cmd_template.split()[0]
    return shutil.which(binary) is not None

def log(message):
    if not log_text:
        return
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    t  = get_theme()
    log_text.configure(state='normal')
    log_text.insert(tk.END, f"[{ts}] {message}\n")
    log_text.see(tk.END)
    log_text.configure(state='disabled', fg=t['log_fg'], bg=t['log_bg'])

def update_status(message, msg_type="info"):
    t = get_theme()
    status_var.set(f"  {message}")
    colours = {
        "success": (t['success_bg'], t['success_fg']),
        "error":   (t['error_bg'],   t['error_fg']),
    }
    bg, fg = colours.get(msg_type, (t['accent'], 'white'))
    status_bar.config(bg=bg, fg=fg)

def save_report(name, content):
    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r'[^\w]', '_', name)
    path = os.path.join(reports_dir, f"{safe}_{ts}.txt")
    with open(path, 'w') as f:
        f.write(f"# WEB DETECTION v3.0 — {name}\n")
        f.write(f"# Generated: {datetime.datetime.now()}\n\n")
        f.write(content)
    return path


# ================== STREAM WINDOW ==================
class StreamWindow:
    """Real-time output window — lines stream in as the process runs."""

    def __init__(self, title, cmd, on_close=None):
        t = get_theme()
        self.title    = title
        self.cmd      = cmd
        self.on_close = on_close
        self.output   = []
        self.proc     = None
        self.q        = queue.Queue()

        self.win = tk.Toplevel(root)
        self.win.title(f"  {title}  ")
        self.win.geometry("980x640")
        self.win.configure(bg=t['bg'])
        self.win.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── Title bar ────────────────────────────────
        bar = tk.Frame(self.win, bg=t['accent'])
        bar.pack(fill=tk.X)
        self.title_lbl = tk.Label(bar, text=f"  ▶  {title}", bg=t['accent'], fg='white',
                                   font=("Courier New", 12, "bold"))
        self.title_lbl.pack(side=tk.LEFT, pady=7, padx=4)
        self.status_lbl = tk.Label(bar, text="● RUNNING", bg=t['accent'], fg='#aaffaa',
                                    font=("Segoe UI", 9, "bold"))
        self.status_lbl.pack(side=tk.RIGHT, padx=10)

        # ── Output area ──────────────────────────────
        self.text = scrolledtext.ScrolledText(
            self.win, font=("Courier New", 10),
            bg=t['stream_bg'], fg=t['text'],
            insertbackground=t['text'], relief=tk.FLAT,
            padx=10, pady=8, wrap=tk.NONE
        )
        self.text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8,0))
        self._setup_tags()

        # ── Button row ───────────────────────────────
        row = tk.Frame(self.win, bg=t['bg'])
        row.pack(fill=tk.X, padx=8, pady=6)
        self.stop_btn = tk.Button(row, text="⏹ Stop", bg='#e94560', fg='white',
                                   font=("Segoe UI", 10, "bold"), relief=tk.FLAT,
                                   padx=12, pady=5, cursor="hand2", command=self._stop)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(row, text="⎘ Copy All", bg=t['button_bg'], fg='white',
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT,
                  padx=12, pady=5, cursor="hand2", command=self._copy).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(row, text="💾 Save Report", bg=t['accent'], fg='white',
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT,
                  padx=12, pady=5, cursor="hand2", command=self._save).pack(side=tk.LEFT)
        tk.Button(row, text="✕ Close", bg=t['error_bg'], fg=t['error_fg'],
                  font=("Segoe UI", 10, "bold"), relief=tk.FLAT,
                  padx=12, pady=5, cursor="hand2", command=self._on_close).pack(side=tk.RIGHT)

        # ── Start process ────────────────────────────
        threading.Thread(target=self._run, daemon=True).start()
        self._poll()

    def _setup_tags(self):
        t = get_theme()
        self.text.tag_configure('risk_open',    foreground='#00ff41', font=("Courier New", 10, "bold"))
        self.text.tag_configure('risk_vuln',    foreground='#ff3c3c', font=("Courier New", 10, "bold"))
        self.text.tag_configure('risk_error',   foreground='#ffaa00')
        self.text.tag_configure('risk_closed',  foreground='#888888')
        self.text.tag_configure('risk_proto',   foreground='#00d4ff')
        self.text.tag_configure('risk_ip',      foreground='#bd93f9')
        self.text.tag_configure('risk_bracket', foreground='#f1fa8c')

    def _run(self):
        try:
            self.proc = subprocess.Popen(
                self.cmd, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            for line in self.proc.stdout:
                self.output.append(line)
                self.q.put(('line', line))
            self.proc.wait()
            rc = self.proc.returncode
            self.q.put(('done', rc))
        except Exception as e:
            self.q.put(('error', str(e)))

    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                kind, val = item
                if kind == 'line':
                    self._append_line(val)
                elif kind == 'done':
                    self._finish(val)
                    return
                elif kind == 'error':
                    self._append_line(f"[ERROR] {val}\n")
                    self._finish(-1)
                    return
        except queue.Empty:
            pass
        self.win.after(80, self._poll)

    def _append_line(self, line):
        self.text.configure(state='normal')
        start = self.text.index(tk.END)
        self.text.insert(tk.END, line)
        end = self.text.index(tk.END)
        # Apply risk highlights
        for pattern, tag in RISK_PATTERNS:
            for m in re.finditer(pattern, line, re.IGNORECASE):
                ls = f"{start} + {m.start()} chars"
                le = f"{start} + {m.end()} chars"
                try:
                    self.text.tag_add(tag, ls, le)
                except Exception:
                    pass
        self.text.configure(state='disabled')
        self.text.see(tk.END)

    def _finish(self, rc):
        colour = '#00ff41' if rc == 0 else '#ff5555'
        msg    = "● DONE" if rc == 0 else f"● EXIT {rc}"
        self.status_lbl.config(text=msg, fg=colour)
        self.stop_btn.config(state=tk.DISABLED)
        root.after(0, lambda: update_status(f"Completed: {self.title}", "success" if rc == 0 else "error"))
        root.after(0, lambda: log(f"Finished: {self.title} (exit {rc})"))
        if self.on_close:
            active_streams.pop(self.title, None)

    def _stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            log(f"Stopped: {self.title}")

    def _copy(self):
        content = ''.join(self.output)
        self.win.clipboard_clear()
        self.win.clipboard_append(content)
        update_status("Copied to clipboard.", "success")

    def _save(self):
        content = ''.join(self.output)
        path = save_report(self.title, content)
        update_status(f"Saved → {path}", "success")
        log(f"Report saved: {path}")

    def _on_close(self):
        self._stop()
        active_streams.pop(self.title, None)
        if self.on_close:
            self.on_close()
        self.win.destroy()


# ================== PARALLEL RUNNER ==================
def run_command(name, cmd_template, ask_input, input_prompt, fast_flag=""):
    if ask_input:
        target = simpledialog.askstring(name, input_prompt, parent=root)
        if not target or not target.strip():
            update_status("Cancelled — no input provided.", "error")
            return
        safe = shlex.quote(target.strip())
        # Insert fast flags if fast mode active
        if fast_var.get() and fast_flag:
            # inject flags after the binary
            parts = cmd_template.split(" ", 1)
            cmd = f"{parts[0]} {fast_flag} {parts[1].replace('{target}', safe)}"
        else:
            cmd = cmd_template.replace("{target}", safe)
    else:
        cmd = cmd_template

    if name in active_streams:
        update_status(f"Already running: {name}", "error")
        return

    update_status(f"Launching: {name}...", "info")
    log(f"Started: {name}  →  {cmd}")
    sw = StreamWindow(name, cmd, on_close=lambda: active_streams.pop(name, None))
    active_streams[name] = sw


def run_parallel(tools_list):
    """Launch multiple tools at once."""
    for name, cmd, ask_input, input_prompt, cat, desc, fast_flag in tools_list:
        if not ask_input:
            run_command(name, cmd, False, "", fast_flag)
        # input tools skipped in parallel mode (no dialog spam)


def quick_recon():
    """One-click: Ping + DNS + Whois + HTTP headers in parallel."""
    target = simpledialog.askstring("Quick Recon", "Enter target domain or IP:", parent=root)
    if not target or not target.strip():
        return
    safe = shlex.quote(target.strip())
    jobs = [
        ("Ping Host",      f"ping -c 4 {safe}"),
        ("DNS Lookup",     f"dig {safe} ANY +noall +answer"),
        ("Whois",          f"whois {safe}"),
        ("HTTP Headers",   f"curl -sI --max-time 10 http://{safe}"),
        ("Traceroute",     f"traceroute -m 10 {safe}"),
    ]
    for name, cmd in jobs:
        log(f"[Quick Recon] Launching {name}")
        sw = StreamWindow(f"[QR] {name} — {target}", cmd)
        active_streams[f"[QR] {name}"] = sw
    update_status(f"Quick Recon launched for {target} — 5 parallel windows", "success")


def quick_webscan():
    """One-click: HTTP headers + Nikto + WhatWeb + Dir brute in parallel."""
    target = simpledialog.askstring("Quick Web Scan", "Enter target (no http://):", parent=root)
    if not target or not target.strip():
        return
    safe = shlex.quote(target.strip())
    jobs = [
        ("HTTP Headers",    f"curl -sI --max-time 10 http://{safe}"),
        ("WhatWeb",         f"whatweb -a 3 http://{safe}"),
        ("Nikto",           f"nikto -h {safe} -maxtime 60 -Tuning 13"),
        ("Dir Brute",       f"gobuster dir -u http://{safe} -w /usr/share/wordlists/dirb/common.txt -t 50 -q"),
        ("Robots & Sitemap",f"curl -sL http://{safe}/robots.txt; echo ''; curl -sL http://{safe}/sitemap.xml | head -30"),
    ]
    for name, cmd in jobs:
        log(f"[Quick Web] Launching {name}")
        sw = StreamWindow(f"[QW] {name} — {target}", cmd)
        active_streams[f"[QW] {name}"] = sw
    update_status(f"Quick Web Scan launched for {target} — 5 parallel windows", "success")


def quick_portscan():
    """One-click: Fast port + service version + vuln scripts."""
    target = simpledialog.askstring("Quick Port Scan", "Enter target IP or hostname:", parent=root)
    if not target or not target.strip():
        return
    safe = shlex.quote(target.strip())
    jobs = [
        ("Fast Ports",   f"nmap -T4 -F --open {safe}"),
        ("Svc Versions", f"nmap -sV -T4 --open {safe}"),
        ("UDP Top50",    f"nmap -sU -T4 --top-ports 50 {safe}"),
        ("Vuln Scripts", f"nmap --script vuln -T4 {safe}"),
    ]
    for name, cmd in jobs:
        log(f"[Quick Scan] Launching {name}")
        sw = StreamWindow(f"[QS] {name} — {target}", cmd)
        active_streams[f"[QS] {name}"] = sw
    update_status(f"Quick Port Scan launched for {target} — 4 parallel windows", "success")


# ================== THEME ==================
def apply_theme(theme_name):
    global current_theme
    current_theme = theme_name
    t = get_theme()
    root.configure(bg=t['bg'])
    sidebar.configure(bg=t['sidebar_bg'])
    main_frame.configure(bg=t['bg'])
    header_label.configure(bg=t['bg'], fg=t['header_fg'])
    filter_frame.configure(bg=t['bg'])
    grid_outer.configure(bg=t['bg'])
    log_frame.configure(bg=t['bg'])
    log_label.configure(bg=t['bg'], fg=t['text'])
    log_text.configure(bg=t['log_bg'], fg=t['log_fg'])
    status_bar.config(bg=t['accent'], fg='white')
    theme_label.configure(bg=t['sidebar_bg'], fg=t['text'])
    sidebar_title.configure(bg=t['sidebar_bg'], fg=t['header_fg'])
    canvas.configure(bg=t['bg'])
    for btn in theme_buttons.values():
        btn.configure(bg=t['sidebar_bg'], activebackground=t['button_hover'])
    for btn in filter_btns:
        btn.configure(bg=t['accent'], fg='white', activebackground=t['button_hover'])
    refresh_tool_buttons()
    update_status(f"Theme: {theme_name}", "info")
    log(f"Theme → {theme_name}")


# ================== TOOL GRID ==================
def refresh_tool_buttons():
    t = get_theme()
    for w in grid_frame.winfo_children():
        w.destroy()

    filtered = [x for x in TOOLS if active_filter == "All" or x[4] == active_filter]
    tag_colors = {
        "System": "#4fc3f7", "Network": "#81c784",
        "Recon":  "#ffb74d", "Scan":    "#e57373", "Web": "#ce93d8"
    }
    r = col = 0
    for name, cmd, ask_input, prompt, cat, desc, fast_flag in filtered:
        avail  = tool_is_available(cmd)
        bg     = t['button_bg'] if avail else '#666666'
        hover  = t['button_hover'] if avail else '#555555'
        state  = tk.NORMAL if avail else tk.DISABLED
        cursor = "hand2" if avail else "X_cursor"
        tip    = desc if avail else f"NOT INSTALLED — {desc}"

        frame = tk.Frame(grid_frame, bg=t['bg'])
        frame.grid(row=r, column=col, padx=7, pady=5, sticky="nsew")

        btn = tk.Button(
            frame, text=name, width=28,
            bg=bg, fg='white',
            activebackground=hover, activeforeground='white',
            font=("Courier New", 9, "bold"),
            relief=tk.FLAT, cursor=cursor, state=state, pady=9,
            command=lambda n=name, c=cmd, ai=ask_input, p=prompt, ff=fast_flag:
                run_command(n, c, ai, p, ff)
        )
        btn.pack(fill=tk.X)
        tc = tag_colors.get(cat, t['accent'])
        tk.Label(frame, text=f"▸ {cat}  •  {tip}",
                 bg=t['bg'], fg=tc, font=("Segoe UI", 7)).pack(anchor="w", padx=2)
        col += 1
        if col == 3:
            col = 0
            r  += 1
    grid_frame.configure(bg=t['bg'])


def set_filter(cat):
    global active_filter
    active_filter = cat
    refresh_tool_buttons()
    log(f"Filter → {cat}")


# ================== HELP / ABOUT ==================
def show_help():
    txt = (
        "WEB DETECTION v3.0 — Help\n"
        "──────────────────────────────────────────────────\n\n"
        "QUICK SCAN BUTTONS (top of sidebar):\n"
        "  ⚡ Quick Recon   — Ping + DNS + Whois + Headers + Traceroute\n"
        "  🌐 Quick Web     — WhatWeb + Nikto + DirBrute + Robots\n"
        "  🔍 Quick Ports   — Fast Ports + Versions + UDP + Vulns\n"
        "  All open in parallel streaming windows simultaneously.\n\n"
        "FAST MODE (toggle in sidebar):\n"
        "  Injects speed flags into supported tools:\n"
        "  • nmap: -T5 --min-rate 5000\n"
        "  • ping: -c 2  • traceroute: -m 8  • gobuster: -t 100\n"
        "  Use only on networks/systems you own.\n\n"
        "LIVE STREAMING OUTPUT:\n"
        "  Every tool opens a real-time window — lines appear as\n"
        "  they're produced. No waiting for the full output.\n\n"
        "RISK HIGHLIGHTING:\n"
        "  open ports → green bold\n"
        "  VULNERABLE / CVE → red bold\n"
        "  errors/denied   → orange\n"
        "  closed/filtered → grey\n"
        "  protocols       → cyan\n"
        "  IP addresses    → purple\n\n"
        "REPORTS:\n"
        "  Each output window has a 💾 Save Report button.\n"
        f"  Reports saved to: {reports_dir}\n\n"
        "MULTIPLE PARALLEL SCANS:\n"
        "  Click multiple tools — each gets its own window.\n"
        "  Use ⏹ Stop to kill any individual scan.\n"
    )
    sw = StreamWindow("Help", "echo ''")
    sw.text.configure(state='normal')
    sw.text.delete("1.0", tk.END)
    sw.text.insert(tk.END, txt)
    sw.text.configure(state='disabled')


def show_about():
    txt = (
        "WEB DETECTION v3.0\n"
        "──────────────────────────────────────────────────\n"
        "Author  : Bhavya Sehgal\n"
        "Version : 3.0  (major upgrade over v2.0)\n\n"
        "NEW IN v3.0:\n"
        "  ✓ Live streaming output — no waiting for full result\n"
        "  ✓ Risk highlighting — open/vuln/error lines colour-coded\n"
        "  ✓ Fast Mode — injects speed flags into tools automatically\n"
        "  ✓ Quick Recon / Quick Web / Quick Ports — 1-click parallel\n"
        "  ✓ Auto-save reports to ~/web_detection_reports/\n"
        "  ✓ Stop button to kill running processes\n"
        "  ✓ 16 new tools (40 total)\n"
        "  ✓ fping, fierce, subfinder, ffuf, dalfox, wpscan added\n"
        "  ✓ Open file sockets, WiFi list, Netstat, SMB enum added\n"
        "  ✓ Full port scan (-p-), UDP, service version scan added\n\n"
        "TOOL COUNT BY CATEGORY:\n"
    )
    from collections import Counter
    counts = Counter(x[4] for x in TOOLS)
    for cat, n in sorted(counts.items()):
        txt += f"  {cat:<10} {n} tools\n"
    txt += f"\n  TOTAL: {len(TOOLS)} tools\n"
    txt += f"\nREPORTS DIR: {reports_dir}\n"

    sw = StreamWindow("About", "echo ''")
    sw.text.configure(state='normal')
    sw.text.delete("1.0", tk.END)
    sw.text.insert(tk.END, txt)
    sw.text.configure(state='disabled')


def open_reports_dir():
    subprocess.Popen(["xdg-open", reports_dir])


# ================== MAIN GUI ==================
root = tk.Tk()
root.title("WEB DETECTION  v3.0")
root.geometry("1340x860")
root.minsize(960, 640)
fast_var     = tk.BooleanVar(value=False)
parallel_var = tk.BooleanVar(value=False)

t0 = THEMES[current_theme]
root.configure(bg=t0['bg'])

# ── Layout ────────────────────────────────────────
sidebar    = tk.Frame(root, width=200, bg=t0['sidebar_bg'])
sidebar.pack(side=tk.LEFT, fill=tk.Y)
sidebar.pack_propagate(False)
main_frame = tk.Frame(root, bg=t0['bg'])
main_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# ── Sidebar ───────────────────────────────────────
sidebar_title = tk.Label(sidebar, text="⬡ WEB\n  DETECT",
                          bg=t0['sidebar_bg'], fg=t0['header_fg'],
                          font=("Courier New", 15, "bold"), justify=tk.LEFT)
sidebar_title.pack(anchor="w", padx=14, pady=(16, 2))

tk.Label(sidebar, text="v3.0", bg=t0['sidebar_bg'], fg=t0['text'],
          font=("Segoe UI", 8)).pack(anchor="w", padx=16, pady=(0, 6))
tk.Frame(sidebar, bg=t0['sep'], height=1).pack(fill=tk.X, padx=12, pady=4)

# Quick scan buttons
tk.Label(sidebar, text="QUICK SCANS", bg=t0['sidebar_bg'], fg=t0['text'],
          font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=14, pady=(8, 2))
for label, fn, bg in [
    ("⚡ Quick Recon",  quick_recon,    "#e67e22"),
    ("🌐 Quick Web",    quick_webscan,  "#8e44ad"),
    ("🔍 Quick Ports",  quick_portscan, "#c0392b"),
]:
    tk.Button(sidebar, text=label, bg=bg, fg='white',
              font=("Segoe UI", 9, "bold"), relief=tk.FLAT,
              cursor="hand2", pady=6, anchor="w", padx=10,
              command=fn).pack(fill=tk.X, padx=10, pady=2)

tk.Frame(sidebar, bg=t0['sep'], height=1).pack(fill=tk.X, padx=12, pady=8)

# Fast mode toggle
fast_chk = tk.Checkbutton(sidebar, text="⚡ Fast Mode", variable=fast_var,
                            bg=t0['sidebar_bg'], fg='#ffb74d',
                            selectcolor=t0['sidebar_bg'],
                            activebackground=t0['sidebar_bg'],
                            font=("Segoe UI", 9, "bold"),
                            cursor="hand2")
fast_chk.pack(anchor="w", padx=14, pady=(0, 6))
tk.Label(sidebar, text="Injects speed flags\ninto supported tools",
          bg=t0['sidebar_bg'], fg=t0['text'],
          font=("Segoe UI", 7), justify=tk.LEFT).pack(anchor="w", padx=14)

tk.Frame(sidebar, bg=t0['sep'], height=1).pack(fill=tk.X, padx=12, pady=8)

# Theme
theme_label = tk.Label(sidebar, text="THEME", bg=t0['sidebar_bg'], fg=t0['text'],
                         font=("Segoe UI", 8, "bold"))
theme_label.pack(anchor="w", padx=14, pady=(0, 2))
theme_buttons = {}
dots = {"Light": "○", "Dark": "●", "Solarized": "◑", "Dracula": "◈", "Cyberpunk": "◉"}
for tn in THEMES:
    b = tk.Button(sidebar, text=f"  {dots.get(tn,'•')}  {tn}",
                   bg=t0['sidebar_bg'], fg=t0['text'],
                   activebackground=t0['button_hover'], activeforeground='white',
                   font=("Segoe UI", 9), relief=tk.FLAT, anchor="w",
                   cursor="hand2", pady=4,
                   command=lambda x=tn: apply_theme(x))
    b.pack(fill=tk.X, padx=10, pady=1)
    theme_buttons[tn] = b

tk.Frame(sidebar, bg=t0['sep'], height=1).pack(fill=tk.X, padx=12, pady=8)

# Bottom sidebar buttons
for label, fn, bg in [
    ("📁 Open Reports",  open_reports_dir, "#2c7a4b"),
    ("?  Help",          show_help,        "#e67e22"),
    ("ℹ  About",         show_about,       "#8e44ad"),
]:
    tk.Button(sidebar, text=label, bg=bg, fg='white',
              font=("Segoe UI", 10, "bold"), relief=tk.FLAT,
              cursor="hand2", pady=7, command=fn
              ).pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=2)

# ── Main Header ───────────────────────────────────
header_label = tk.Label(main_frame, text="WEB DETECTION TOOLS  v3.0",
                          bg=t0['bg'], fg=t0['header_fg'],
                          font=("Courier New", 18, "bold"))
header_label.pack(anchor="w", padx=20, pady=(14, 4))

# Sub-header: tool count + fast mode indicator
subhdr = tk.Label(main_frame,
    text=f"{len(TOOLS)} tools across 5 categories  •  Live streaming output  •  Risk highlighting",
    bg=t0['bg'], fg=t0['text'], font=("Segoe UI", 9))
subhdr.pack(anchor="w", padx=22, pady=(0, 8))

# ── Category Filter ───────────────────────────────
filter_frame = tk.Frame(main_frame, bg=t0['bg'])
filter_frame.pack(fill=tk.X, padx=20, pady=(0, 6))
filter_btns = []
for cat in CATEGORIES:
    b = tk.Button(filter_frame, text=cat,
                   bg=t0['accent'], fg='white',
                   activebackground=t0['button_hover'], activeforeground='white',
                   font=("Segoe UI", 9, "bold"), relief=tk.FLAT,
                   padx=14, pady=5, cursor="hand2",
                   command=lambda c=cat: set_filter(c))
    b.pack(side=tk.LEFT, padx=3)
    filter_btns.append(b)

# ── Scrollable Tool Grid ──────────────────────────
grid_outer = tk.Frame(main_frame, bg=t0['bg'])
grid_outer.pack(fill=tk.BOTH, expand=True, padx=10)

canvas = tk.Canvas(grid_outer, bg=t0['bg'], highlightthickness=0)
vscroll = ttk.Scrollbar(grid_outer, orient="vertical", command=canvas.yview)
canvas.configure(yscrollcommand=vscroll.set)
vscroll.pack(side=tk.RIGHT, fill=tk.Y)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

grid_frame  = tk.Frame(canvas, bg=t0['bg'])
canvas_win  = canvas.create_window((0, 0), window=grid_frame, anchor="nw")

grid_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.bind("<Configure>",     lambda e: canvas.itemconfig(canvas_win, width=e.width))
canvas.bind_all("<MouseWheel>",lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

# ── Activity Log ──────────────────────────────────
log_frame = tk.Frame(main_frame, bg=t0['bg'])
log_frame.pack(fill=tk.X, padx=10, pady=(4, 0))
log_label = tk.Label(log_frame, text="Activity Log", bg=t0['bg'], fg=t0['text'],
                       font=("Segoe UI", 8, "bold"))
log_label.pack(anchor="w")
log_text = tk.Text(log_frame, height=4, bg=t0['log_bg'], fg=t0['log_fg'],
                    font=("Courier New", 9), state='disabled',
                    relief=tk.FLAT, insertbackground=t0['log_fg'])
log_text.pack(fill=tk.X, pady=(2, 0))

# ── Status Bar ────────────────────────────────────
status_var = tk.StringVar(value="  Ready.")
status_bar = tk.Label(root, textvariable=status_var, bd=0, anchor=tk.W,
                       bg=t0['accent'], fg='white',
                       font=("Courier New", 9), pady=5)
status_bar.pack(side=tk.BOTTOM, fill=tk.X)

# ── Init ─────────────────────────────────────────
apply_theme(current_theme)
refresh_tool_buttons()
update_status("Ready — click a tool or use Quick Scan buttons.", "info")
log("WEB DETECTION v3.0 started.")
log(f"Reports will be saved to: {reports_dir}")

root.mainloop()
