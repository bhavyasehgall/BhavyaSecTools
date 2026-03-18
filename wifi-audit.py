#!/usr/bin/env python3
"""
Wi-Fi Audit Tool — for authorized use only.
Run with: sudo python3 wifi_audit_tool.py
"""

import os
import sys
import shutil
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext

# ================= ROOT CHECK =================
if os.getuid() != 0:
    print("[ERROR] This tool requires root. Run with: sudo python3 wifi_audit_tool.py")
    sys.exit(1)

# ================= DEPENDENCY CHECK =================
REQUIRED_TOOLS = ["airmon-ng", "nmcli", "hcxpcapngtool", "john"]

def check_dependencies():
    missing = [t for t in REQUIRED_TOOLS if shutil.which(t) is None]
    return missing

# ================= HELPERS =================
def run(cmd, output_widget=None):
    """Run a shell command and optionally stream output to a ScrolledText widget."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        text = result.stdout or "(No output)\n"
        if output_widget:
            output_widget.insert(tk.END, text + "\n")
            output_widget.see(tk.END)
        return text
    except FileNotFoundError:
        msg = f"[ERROR] Command not found: {cmd[0]}\n"
        if output_widget:
            output_widget.insert(tk.END, msg)
        return msg
    except Exception as e:
        msg = f"[ERROR] {e}\n"
        if output_widget:
            output_widget.insert(tk.END, msg)
        return msg

def get_wireless_interfaces():
    """Return a list of available wireless interfaces."""
    try:
        out = subprocess.check_output(["iw", "dev"], text=True)
        ifaces = []
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("Interface"):
                ifaces.append(line.split()[-1])
        return ifaces if ifaces else ["wlan0"]
    except Exception:
        return ["wlan0"]

def is_monitor(iface):
    out = subprocess.getoutput("iw dev")
    # Check if the specific interface is in monitor mode
    lines = out.splitlines()
    in_iface_block = False
    for line in lines:
        if f"Interface {iface}" in line:
            in_iface_block = True
        if in_iface_block and "type monitor" in line:
            return True
        if in_iface_block and line.strip().startswith("Interface") and f"Interface {iface}" not in line:
            in_iface_block = False
    return False

# ================= DISCLAIMER DIALOG =================
def show_disclaimer():
    dlg = tk.Toplevel()
    dlg.title("⚠ Legal Disclaimer")
    dlg.geometry("560x400")
    dlg.resizable(False, False)
    dlg.grab_set()  # Modal

    frame = ttk.Frame(dlg, padding=20)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="⚠  IMPORTANT — READ BEFORE CONTINUING",
              font=("TkDefaultFont", 12, "bold"), foreground="red").pack(pady=(0, 12))

    text = (
        "This tool is intended ONLY for:\n\n"
        "  • Testing Wi-Fi networks you OWN, or\n"
        "  • Networks you have EXPLICIT WRITTEN AUTHORIZATION to test.\n\n"
        "Unauthorized use is illegal in most jurisdictions, including:\n"
        "  • India: IT Act 2000, Section 43/66\n"
        "  • USA: Computer Fraud and Abuse Act (CFAA)\n"
        "  • UK: Computer Misuse Act 1990\n\n"
        "By clicking 'I Agree', you confirm that:\n"
        "  1. You are the owner or have written authorization.\n"
        "  2. You accept full legal responsibility for your actions.\n"
        "  3. This tool is being used for legitimate security research only."
    )

    txt = scrolledtext.ScrolledText(frame, height=12, wrap=tk.WORD, state=tk.NORMAL,
                                     font=("TkDefaultFont", 10))
    txt.insert(tk.END, text)
    txt.configure(state=tk.DISABLED)
    txt.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

    agreed = tk.BooleanVar(value=False)

    def on_agree():
        agreed.set(True)
        dlg.destroy()

    def on_decline():
        agreed.set(False)
        dlg.destroy()

    btn_frame = ttk.Frame(frame)
    btn_frame.pack()
    ttk.Button(btn_frame, text="I Agree — Continue", command=on_agree).grid(row=0, column=0, padx=10)
    ttk.Button(btn_frame, text="Decline — Exit", command=on_decline).grid(row=0, column=1, padx=10)

    dlg.protocol("WM_DELETE_WINDOW", on_decline)
    dlg.wait_window()
    return agreed.get()

# ================= MAIN APP =================
class WifiAuditApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wi-Fi Audit Tool  |  Authorized Use Only")
        self.root.geometry("920x680")
        self.root.resizable(False, False)

        self.crack_proc = None  # Track running crack process

        self._build_ui()

    def _build_ui(self):
        # Status bar at top
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, padx=10, pady=(8, 0))

        ttk.Label(status_frame, text="Interface:").pack(side=tk.LEFT, padx=(0, 4))
        self.iface_var = tk.StringVar()
        ifaces = get_wireless_interfaces()
        self.iface_combo = ttk.Combobox(status_frame, textvariable=self.iface_var,
                                         values=ifaces, width=14, state="readonly")
        self.iface_combo.pack(side=tk.LEFT)
        if ifaces:
            self.iface_combo.current(0)

        ttk.Button(status_frame, text="↻ Refresh Interfaces",
                   command=self._refresh_ifaces).pack(side=tk.LEFT, padx=8)

        self.status_label = ttk.Label(status_frame, text="", foreground="gray")
        self.status_label.pack(side=tk.RIGHT)

        # Notebook tabs
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        self._build_scanner_tab()
        self._build_converter_tab()
        self._build_cracker_tab()
        self._build_about_tab()

    def _refresh_ifaces(self):
        ifaces = get_wireless_interfaces()
        self.iface_combo["values"] = ifaces
        if ifaces:
            self.iface_combo.current(0)
        self._set_status(f"Found {len(ifaces)} interface(s)")

    def _set_status(self, msg):
        self.status_label.config(text=msg)

    # --------------------------------------------------
    # TAB 1 — SCANNER
    # --------------------------------------------------
    def _build_scanner_tab(self):
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text="  Wi-Fi Scanner  ")

        self.scan_out = scrolledtext.ScrolledText(tab, height=22, font=("Courier", 10))
        self.scan_out.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        btns = ttk.Frame(tab)
        btns.pack(pady=5)

        ttk.Button(btns, text="Scan Wi-Fi Networks", width=22,
                   command=self._scan_wifi).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Enable Monitor Mode", width=22,
                   command=self._monitor_on).grid(row=0, column=1, padx=6)
        ttk.Button(btns, text="Disable Monitor Mode", width=22,
                   command=self._monitor_off).grid(row=0, column=2, padx=6)

    def _scan_wifi(self):
        iface = self.iface_var.get()
        self.scan_out.delete(1.0, tk.END)
        if is_monitor(iface):
            messagebox.showwarning(
                "Monitor Mode Active",
                f"Interface {iface} is in monitor mode.\nDisable it before scanning."
            )
            return
        self._set_status("Scanning…")
        self.scan_out.insert(tk.END, f"[INFO] Scanning on {iface}...\n\n")
        run(["nmcli", "-f", "SSID,BSSID,CHAN,SIGNAL,SECURITY", "dev", "wifi", "list",
             "ifname", iface], self.scan_out)
        self._set_status("Scan complete.")

    def _monitor_on(self):
        iface = self.iface_var.get()
        self.scan_out.delete(1.0, tk.END)
        self.scan_out.insert(tk.END, f"[INFO] Enabling monitor mode on {iface}...\n\n")
        run(["airmon-ng", "start", iface], self.scan_out)
        self._set_status(f"Monitor mode enabled on {iface}.")
        self._refresh_ifaces()

    def _monitor_off(self):
        iface = self.iface_var.get()
        self.scan_out.delete(1.0, tk.END)
        self.scan_out.insert(tk.END, f"[INFO] Disabling monitor mode on {iface}...\n\n")
        run(["airmon-ng", "stop", iface], self.scan_out)
        self._set_status(f"Monitor mode disabled on {iface}.")
        self._refresh_ifaces()

    # --------------------------------------------------
    # TAB 2 — WPA CONVERTER
    # --------------------------------------------------
    def _build_converter_tab(self):
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text="  WPA Converter  ")

        pad = {"padx": 14, "pady": 4}

        ttk.Label(tab, text="Capture File (.cap / .pcapng)").pack(anchor=tk.W, **pad)
        cap_row = ttk.Frame(tab)
        cap_row.pack(fill=tk.X, padx=14)
        self.cap_entry = ttk.Entry(cap_row, width=80)
        self.cap_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(cap_row, text="Browse…", command=self._browse_cap).pack(side=tk.LEFT, padx=6)

        ttk.Label(tab, text="Output Hash File (leave blank for default)").pack(anchor=tk.W, **pad)
        out_row = ttk.Frame(tab)
        out_row.pack(fill=tk.X, padx=14)
        self.out_entry = ttk.Entry(out_row, width=80)
        self.out_entry.insert(0, os.path.expanduser("~/wifi_hash.hc22000"))
        self.out_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(out_row, text="Browse…", command=self._browse_out).pack(side=tk.LEFT, padx=6)

        ttk.Button(tab, text="Convert to WPA Hash", width=28,
                   command=self._convert).pack(pady=16)

        self.conv_out = scrolledtext.ScrolledText(tab, height=14, font=("Courier", 10))
        self.conv_out.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 10))

    def _browse_cap(self):
        f = filedialog.askopenfilename(filetypes=[("Capture Files", "*.cap *.pcapng"), ("All", "*.*")])
        if f:
            self.cap_entry.delete(0, tk.END)
            self.cap_entry.insert(0, f)

    def _browse_out(self):
        f = filedialog.asksaveasfilename(defaultextension=".hc22000",
                                          filetypes=[("HC22000", "*.hc22000"), ("All", "*.*")])
        if f:
            self.out_entry.delete(0, tk.END)
            self.out_entry.insert(0, f)

    def _convert(self):
        cap = self.cap_entry.get().strip()
        out = self.out_entry.get().strip()

        if not cap or not os.path.isfile(cap):
            messagebox.showerror("Error", "Please select a valid capture file.")
            return
        if not out:
            out = os.path.expanduser("~/wifi_hash.hc22000")

        self.conv_out.delete(1.0, tk.END)
        self.conv_out.insert(tk.END, f"[INFO] Converting {cap} → {out}\n\n")
        self._set_status("Converting…")

        def task():
            result = subprocess.run(
                ["hcxpcapngtool", "-o", out, cap],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            self.conv_out.insert(tk.END, result.stdout or "(No output)\n")
            self.conv_out.see(tk.END)
            if result.returncode == 0 and os.path.isfile(out):
                self._set_status("Conversion complete.")
                messagebox.showinfo("Success", f"Hash file saved to:\n{out}")
                # Auto-populate cracker tab
                self.hash_entry.delete(0, tk.END)
                self.hash_entry.insert(0, out)
            else:
                self._set_status("Conversion failed.")
                messagebox.showerror("Error", "Conversion failed. Check the output log.")

        threading.Thread(target=task, daemon=True).start()

    # --------------------------------------------------
    # TAB 3 — PASSWORD CRACKER
    # --------------------------------------------------
    def _build_cracker_tab(self):
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text="  Password Cracker  ")

        pad = {"padx": 14, "pady": 4}

        ttk.Label(tab, text="WPA Hash File (.hc22000 or similar)").pack(anchor=tk.W, **pad)
        hash_row = ttk.Frame(tab)
        hash_row.pack(fill=tk.X, padx=14)
        self.hash_entry = ttk.Entry(hash_row, width=80)
        self.hash_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(hash_row, text="Browse…", command=self._browse_hash).pack(side=tk.LEFT, padx=6)

        ttk.Label(tab, text="Wordlist").pack(anchor=tk.W, **pad)
        word_row = ttk.Frame(tab)
        word_row.pack(fill=tk.X, padx=14)
        self.word_entry = ttk.Entry(word_row, width=80)
        self.word_entry.insert(0, "/usr/share/wordlists/rockyou.txt")
        self.word_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(word_row, text="Browse…", command=self._browse_word).pack(side=tk.LEFT, padx=6)

        btn_row = ttk.Frame(tab)
        btn_row.pack(pady=12)
        ttk.Button(btn_row, text="▶  Start Cracking", width=20,
                   command=self._crack_start).grid(row=0, column=0, padx=8)
        ttk.Button(btn_row, text="■  Stop", width=12,
                   command=self._crack_stop).grid(row=0, column=1, padx=8)

        self.crack_out = scrolledtext.ScrolledText(tab, height=16, font=("Courier", 10))
        self.crack_out.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 10))

    def _browse_hash(self):
        f = filedialog.askopenfilename()
        if f:
            self.hash_entry.delete(0, tk.END)
            self.hash_entry.insert(0, f)

    def _browse_word(self):
        f = filedialog.askopenfilename()
        if f:
            self.word_entry.delete(0, tk.END)
            self.word_entry.insert(0, f)

    def _crack_start(self):
        h = self.hash_entry.get().strip()
        w = self.word_entry.get().strip()

        if not h or not os.path.isfile(h):
            messagebox.showerror("Error", "Invalid hash file.")
            return
        if not w or not os.path.isfile(w):
            messagebox.showerror("Error", "Invalid wordlist file.")
            return

        self.crack_out.delete(1.0, tk.END)
        self.crack_out.insert(tk.END, f"[INFO] Starting john with:\n  Hash:     {h}\n  Wordlist: {w}\n\n")
        self._set_status("Cracking in progress…")

        def task():
            try:
                self.crack_proc = subprocess.Popen(
                    ["john", f"--wordlist={w}", h],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                for line in self.crack_proc.stdout:
                    self.crack_out.insert(tk.END, line)
                    self.crack_out.see(tk.END)
                self.crack_proc.wait()
                rc = self.crack_proc.returncode
                self.crack_out.insert(tk.END, f"\n[INFO] john exited with code {rc}\n")
                self.crack_out.see(tk.END)
                self._set_status("Cracking finished.")
            except FileNotFoundError:
                self.crack_out.insert(tk.END, "[ERROR] 'john' not found. Install: sudo apt install john\n")
                self._set_status("Error.")

        threading.Thread(target=task, daemon=True).start()

    def _crack_stop(self):
        if self.crack_proc and self.crack_proc.poll() is None:
            self.crack_proc.terminate()
            self.crack_out.insert(tk.END, "\n[INFO] Crack job terminated by user.\n")
            self._set_status("Stopped.")
        else:
            self._set_status("No active crack job.")

    # --------------------------------------------------
    # TAB 4 — ABOUT
    # --------------------------------------------------
    def _build_about_tab(self):
        tab = ttk.Frame(self.tabs)
        self.tabs.add(tab, text="  About  ")

        info = (
            "Wi-Fi Audit Tool\n"
            "────────────────────────────────────────\n\n"
            "Purpose:\n"
            "  Security research and authorized penetration testing of Wi-Fi networks.\n\n"
            "Required Tools:\n"
            + "".join(f"  • {t}\n" for t in REQUIRED_TOOLS) +
            "\nInstall on Debian/Ubuntu:\n"
            "  sudo apt install aircrack-ng hcxtools john\n\n"
            "Workflow:\n"
            "  1. Scanner tab  → find target SSID and enable monitor mode\n"
            "  2. Use airodump-ng / aireplay-ng in a terminal to capture a handshake\n"
            "  3. WPA Converter → convert .cap to .hc22000 hash\n"
            "  4. Password Cracker → run dictionary attack with john\n\n"
            "Legal Reminder:\n"
            "  Only test networks you own or have written authorization to test.\n"
            "  Unauthorized testing is a criminal offence.\n"
        )

        txt = scrolledtext.ScrolledText(tab, font=("Courier", 10), wrap=tk.WORD)
        txt.insert(tk.END, info)
        txt.configure(state=tk.DISABLED)
        txt.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)


# ================= ENTRY POINT =================
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide main window until disclaimer is accepted

    # Dependency check
    missing = check_dependencies()
    if missing:
        messagebox.showwarning(
            "Missing Tools",
            "The following tools were not found in PATH:\n\n"
            + "\n".join(f"  • {t}" for t in missing)
            + "\n\nSome features may not work.\n"
              "Install with: sudo apt install aircrack-ng hcxtools john"
        )

    # Disclaimer — user must agree to continue
    if not show_disclaimer():
        root.destroy()
        sys.exit(0)

    root.deiconify()  # Show main window
    app = WifiAuditApp(root)
    root.mainloop()
