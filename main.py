#!/usr/bin/env python3
"""
KaliToolkit Dashboard
Central GUI to launch all modules
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os

# Paths to tools (update if needed)
TOOLS = {
    "Wi-Fi Audit Tool": "wifi-audit.py",
    "Decoder Tool": "decoder.py",
    "Steganography Tool": "steghide.py",
    "Web Scanner": "webdetection2.py"
}

class Dashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("KaliToolkit Dashboard")
        self.root.geometry("800x560")
        self.root.resizable(False, False)

        self._build_ui()

    def _build_ui(self):
        # Notebook for tabs
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill=tk.BOTH, expand=True)

        # Main tab
        self.main_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.main_tab, text=" Dashboard ")

        # Help tab
        self.help_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.help_tab, text=" Help ")

        # About tab
        self.about_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.about_tab, text=" About ")

        self._build_main_tab()
        self._build_help_tab()
        self._build_about_tab()

    def _build_main_tab(self):
        title = tk.Label(self.main_tab, text="🔐 KaliToolkit", font=("Arial", 20, "bold"))
        title.pack(pady=20)

        subtitle = tk.Label(self.main_tab, text="All-in-One Cybersecurity Toolkit", font=("Arial", 12))
        subtitle.pack(pady=5)

        frame = ttk.Frame(self.main_tab)
        frame.pack(pady=30)

        row = 0
        for tool_name, script in TOOLS.items():
            btn = ttk.Button(frame, text=tool_name, width=30,
                             command=lambda s=script: self.launch_tool(s))
            btn.grid(row=row, column=0, padx=10, pady=10)
            row += 1

        ttk.Button(self.main_tab, text="Exit", command=self.root.quit).pack(pady=20)

        # Status bar
        self.status = tk.StringVar()
        self.status.set("Ready")
        status_bar = ttk.Label(self.main_tab, textvariable=self.status, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_help_tab(self):
        text = tk.Text(self.help_tab, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        help_content = (
            "KaliToolkit Help Guide\n"
            "────────────────────────────\n\n"
            "1. Dashboard:\n"
            "   Launch different tools from the main screen.\n\n"
            "2. Wi-Fi Audit Tool:\n"
            "   - Scan networks\n"
            "   - Enable monitor mode\n"
            "   - Convert captures and crack passwords\n\n"
            "3. Decoder Tool:\n"
            "   - Decode Base64, Hex, Binary\n"
            "   - Supports multi-layer decoding\n\n"
            "4. Steganography Tool:\n"
            "   - Hide and extract data from files\n\n"
            "5. Web Scanner:\n"
            "   - Perform recon and vulnerability scans\n\n"
            "⚠ Use responsibly and only on authorized systems.\n"
        )

        text.insert(tk.END, help_content)
        text.config(state=tk.DISABLED)

    def _build_about_tab(self):
        text = tk.Text(self.about_tab, wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        about_content = (
            "KaliToolkit Dashboard\n"
            "────────────────────────────\n\n"
            "Version: 1.0\n"
            "Author: Bhavya Sehgal\n\n"
            "A GUI-based cybersecurity toolkit combining multiple tools into one interface.\n"
            "Designed for ethical hacking, learning, and security research.\n\n"
            "Features:\n"
            "- Wi-Fi Auditing\n"
            "- Network Scanning\n"
            "- Decoding Tools\n"
            "- Steganography\n"
            "- Automation\n\n"
            "⚠ This tool is for educational and authorized use only.\n"
        )

        text.insert(tk.END, about_content)
        text.config(state=tk.DISABLED)

    def launch_tool(self, script):
        if not os.path.exists(script):
            messagebox.showerror("Error", f"{script} not found!")
            return

        try:
            self.status.set(f"Launching {script}...")
            subprocess.Popen(["python3", script])
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status.set("Error launching tool")


if __name__ == "__main__":
    root = tk.Tk()
    app = Dashboard(root)
    root.mainloop()
