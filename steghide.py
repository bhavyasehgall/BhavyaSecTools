#!/usr/bin/env python3
# ===========================================================
#   PRO STEGHIDE GUI — UNIVERSAL EDITION
#   Supports: Images, Audio, Video, PDF, Any Binary
#   Tools: steghide, ffmpeg, LSB engine (built-in)
#   Author: Bhavya Sehgal  |  Extended for universal support
# ===========================================================

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess
import os
import base64
import hashlib
import struct
import json
from cryptography.fernet import Fernet

# ===========================================================
# ENCRYPTION
# ===========================================================

def derive_key(password: str) -> bytes:
    return base64.urlsafe_b64encode(hashlib.sha256(password.encode()).digest())

def encrypt_data(text: str, password: str) -> bytes:
    return Fernet(derive_key(password)).encrypt(text.encode())

def decrypt_data(data: bytes, password: str):
    try:
        return Fernet(derive_key(password)).decrypt(data).decode()
    except Exception:
        return None

# ===========================================================
# FILE TYPE DETECTION
# ===========================================================

STEGHIDE_EXTS  = {".jpg", ".jpeg", ".bmp", ".wav", ".au"}
VIDEO_EXTS     = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}
LSB_IMAGE_EXTS = {".png", ".gif", ".tiff", ".tif", ".ppm", ".pgm"}

def classify(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    if ext in STEGHIDE_EXTS:
        return "steghide"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in LSB_IMAGE_EXTS:
        return "lsb_image"
    return "lsb_binary"   # PDF, MP3, FLAC, OGG, EXE, ZIP, ...

# ===========================================================
# LSB ENGINE  (pure Python — works on any byte stream)
# ===========================================================

MAGIC = b"LSTEG"   # 5-byte magic to tag embedded data

def lsb_embed(carrier: bytes, payload: bytes) -> bytes:
    header  = MAGIC + struct.pack(">I", len(payload))
    message = header + payload
    bits    = "".join(f"{b:08b}" for b in message)

    if len(bits) > len(carrier):
        raise ValueError(
            f"Carrier too small: need {len(bits)} byte-slots, have {len(carrier)}."
        )
    arr = bytearray(carrier)
    for i, bit in enumerate(bits):
        arr[i] = (arr[i] & 0xFE) | int(bit)
    return bytes(arr)


def lsb_extract(carrier: bytes) -> bytes:
    def read_byte(offset):
        return int("".join(str(carrier[offset * 8 + b] & 1) for b in range(8)), 2)

    header = bytes(read_byte(i) for i in range(9))
    if header[:5] != MAGIC:
        raise ValueError("No LSB-embedded data found (magic header missing).")

    payload_len = struct.unpack(">I", header[5:9])[0]
    if (9 + payload_len) * 8 > len(carrier):
        raise ValueError("Embedded length exceeds file — data may be corrupt.")

    return bytes(read_byte(9 + i) for i in range(payload_len))

# ===========================================================
# LSB IMAGE (uses Pillow if available, else raw bytes)
# ===========================================================

def lsb_image_embed(cover_path: str, payload: bytes, out_path: str):
    try:
        from PIL import Image
        img    = Image.open(cover_path).convert("RGB")
        result = lsb_embed(img.tobytes(), payload)
        Image.frombytes("RGB", img.size, result).save(out_path)
    except ImportError:
        with open(cover_path, "rb") as f:
            raw = f.read()
        with open(out_path, "wb") as f:
            f.write(lsb_embed(raw, payload))


def lsb_image_extract(cover_path: str) -> bytes:
    try:
        from PIL import Image
        return lsb_extract(Image.open(cover_path).convert("RGB").tobytes())
    except ImportError:
        with open(cover_path, "rb") as f:
            return lsb_extract(f.read())

# ===========================================================
# VIDEO — embed payload in ffmpeg 'comment' metadata tag
# ===========================================================

def video_embed(cover_path: str, payload: bytes, out_path: str):
    encoded = base64.b64encode(payload).decode()
    result  = subprocess.run(
        ["ffmpeg", "-y", "-i", cover_path,
         "-metadata", f"comment={encoded}",
         "-codec", "copy", out_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg embed failed:\n{result.stderr[-600:]}")


def video_extract(cover_path: str) -> bytes:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", cover_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed:\n{result.stderr[-600:]}")

    comment = (json.loads(result.stdout)
               .get("format", {})
               .get("tags", {})
               .get("comment", ""))
    if not comment:
        raise ValueError("No embedded data found in video metadata.")
    try:
        return base64.b64decode(comment)
    except Exception:
        raise ValueError("'comment' metadata does not contain valid embedded data.")

# ===========================================================
# STEGHIDE WRAPPERS
# ===========================================================

def run_steghide_embed(cover: str, ef: str, password: str):
    r = subprocess.run(
        ["steghide", "embed", "-cf", cover, "-ef", ef, "-p", password, "-f"],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        raise RuntimeError(f"steghide embed failed:\n{r.stderr}")


def run_steghide_extract(cover: str, password: str) -> bytes:
    r = subprocess.run(
        ["steghide", "extract", "-sf", cover, "-xf", "out.bin", "-p", password, "-f"],
        capture_output=True, text=True
    )
    if r.returncode != 0:
        raise RuntimeError(f"steghide extract failed:\n{r.stderr}")
    with open("out.bin", "rb") as f:
        data = f.read()
    os.remove("out.bin")
    return data

# ===========================================================
# UNIFIED EMBED / EXTRACT
# ===========================================================

def universal_embed(cover: str, payload: bytes, password: str, log_box=None):
    kind = classify(cover)
    _log(log_box, f"[Engine] {os.path.basename(cover)}  →  {kind}")

    if kind == "steghide":
        tmp = "temp_payload.bin"
        with open(tmp, "wb") as f:
            f.write(payload)
        try:
            run_steghide_embed(cover, tmp, password)
            _log(log_box, f"[steghide] Embedded in-place: {cover}")
        finally:
            _rm(tmp)

    elif kind == "video":
        ext = os.path.splitext(cover)[1]
        out = cover + ".steg" + ext
        video_embed(cover, payload, out)
        _log(log_box, f"[ffmpeg] Output: {out}")

    elif kind == "lsb_image":
        out = cover + ".steg.png"
        lsb_image_embed(cover, payload, out)
        _log(log_box, f"[LSB image] Output: {out}")

    else:   # lsb_binary — PDF, MP3, FLAC, OGG, ZIP, any file
        with open(cover, "rb") as f:
            raw = f.read()
        out = cover + ".steg"
        with open(out, "wb") as f:
            f.write(lsb_embed(raw, payload))
        _log(log_box, f"[LSB binary] Output: {out}")


def universal_extract(cover: str, password: str, log_box=None) -> bytes:
    kind = classify(cover)
    _log(log_box, f"[Engine] {os.path.basename(cover)}  →  {kind}")

    if kind == "steghide":
        return run_steghide_extract(cover, password)
    if kind == "video":
        return video_extract(cover)
    if kind == "lsb_image":
        return lsb_image_extract(cover)
    # lsb_binary
    with open(cover, "rb") as f:
        raw = f.read()
    return lsb_extract(raw)

# ===========================================================
# HELPERS
# ===========================================================

def _log(widget, msg):
    if widget is None:
        return
    widget.config(state="normal")
    widget.insert(tk.END, msg + "\n")
    widget.config(state="disabled")
    widget.see(tk.END)

def _rm(path):
    if path and os.path.exists(path):
        os.remove(path)

# ===========================================================
# THEMES
# ===========================================================

THEMES = {
    "dark": {
        "BG":           "#0D0D0D",
        "PANEL":        "#161616",
        "BORDER":       "#2A2A2A",
        "ACCENT":       "#00FF7F",
        "ACCENT2":      "#00CC66",
        "RED":          "#FF3333",
        "RED2":         "#CC0000",
        "FG":           "#E8E8E8",
        "MUTED":        "#888888",
        "ENTRY_BG":     "#161616",
        "ENTRY_FG":     "#E8E8E8",
        "LOG_BG":       "#090909",
        "LOG_FG":       "#00FF7F",
        "STATUS_BG":    "#111111",
        "STATUS_FG":    "#00FF7F",
        "BTN_BROWSE_FG":"#AAAAAA",
        "BTN_BROWSE_H": "#888888",
        "TOGGLE_ICON":  "☀  Light Mode",
        "TAB_SEL_BG":   "#0D0D0D",
        "TAB_SEL_FG":   "#00FF7F",
        "TAB_BG":       "#161616",
        "TAB_FG":       "#888888",
    },
    "light": {
        "BG":           "#F4F6F8",
        "PANEL":        "#FFFFFF",
        "BORDER":       "#CBD5E1",
        "ACCENT":       "#0070F3",
        "ACCENT2":      "#0051B3",
        "RED":          "#DC2626",
        "RED2":         "#B91C1C",
        "FG":           "#1E293B",
        "MUTED":        "#64748B",
        "ENTRY_BG":     "#FFFFFF",
        "ENTRY_FG":     "#1E293B",
        "LOG_BG":       "#F8FAFC",
        "LOG_FG":       "#0F172A",
        "STATUS_BG":    "#E2E8F0",
        "STATUS_FG":    "#0070F3",
        "BTN_BROWSE_FG":"#475569",
        "BTN_BROWSE_H": "#334155",
        "TOGGLE_ICON":  "🌙  Dark Mode",
        "TAB_SEL_BG":   "#F4F6F8",
        "TAB_SEL_FG":   "#0070F3",
        "TAB_BG":       "#E2E8F0",
        "TAB_FG":       "#64748B",
    },
}

# ===========================================================
# GUI
# ===========================================================

def create_gui():
    root = tk.Tk()
    root.title("PRO STEGHIDE GUI — Universal Edition")
    root.geometry("980x720")

    FONT      = ("Consolas", 10)
    FONT_BOLD = ("Consolas", 10, "bold")

    current_theme = tk.StringVar(value="dark")

    style = ttk.Style()
    style.theme_use("clam")

    # ── all mutable widget references for re-theming ──
    # We collect them after building, then apply theme
    themed_widgets = []   # list of (widget, role)

    # ── helper: register widget for re-theming ──
    def reg(w, role):
        themed_widgets.append((w, role))
        return w

    # ===========================================================
    # APPLY THEME
    # ===========================================================
    def apply_theme(name=None):
        if name:
            current_theme.set(name)
        T = THEMES[current_theme.get()]

        root.configure(bg=T["BG"])

        # ttk styles
        style.configure("TNotebook",         background=T["BG"],    borderwidth=0)
        style.configure("TNotebook.Tab",     background=T["TAB_BG"], foreground=T["TAB_FG"],
                        font=FONT_BOLD, padding=[14, 6])
        style.map("TNotebook.Tab",
                  background=[("selected", T["TAB_SEL_BG"])],
                  foreground=[("selected", T["TAB_SEL_FG"])])
        style.configure("TFrame",            background=T["BG"])
        style.configure("TLabel",            background=T["BG"],    foreground=T["FG"],    font=FONT)
        style.configure("TLabelframe",       background=T["BG"],    foreground=T["ACCENT"],
                        bordercolor=T["BORDER"], font=FONT_BOLD)
        style.configure("TLabelframe.Label", background=T["BG"],    foreground=T["ACCENT"])
        style.configure("TCheckbutton",      background=T["BG"],    foreground=T["FG"],    font=FONT)

        style.configure("Green.TButton",  background=T["PANEL"], foreground=T["ACCENT"],
                        font=FONT_BOLD, padding=[10, 5], relief="flat", borderwidth=1)
        style.map("Green.TButton", foreground=[("active", T["ACCENT2"])])

        style.configure("Red.TButton",    background=T["PANEL"], foreground=T["RED"],
                        font=FONT_BOLD, padding=[10, 5], relief="flat", borderwidth=1)
        style.map("Red.TButton",   foreground=[("active", T["RED2"])])

        style.configure("Gray.TButton",   background=T["PANEL"], foreground=T["BTN_BROWSE_FG"],
                        font=FONT_BOLD, padding=[10, 5], relief="flat", borderwidth=1)
        style.map("Gray.TButton",  foreground=[("active", T["BTN_BROWSE_H"])])

        style.configure("Toggle.TButton", background=T["PANEL"], foreground=T["MUTED"],
                        font=("Consolas", 9), padding=[8, 4], relief="flat", borderwidth=1)
        style.map("Toggle.TButton", foreground=[("active", T["ACCENT"])])

        # plain tk widgets
        for w, role in themed_widgets:
            try:
                if role == "bg":
                    w.configure(bg=T["BG"])
                elif role == "panel":
                    w.configure(bg=T["PANEL"])
                elif role == "title":
                    w.configure(bg=T["BG"], fg=T["ACCENT"])
                elif role == "subtitle":
                    w.configure(bg=T["BG"], fg=T["MUTED"])
                elif role == "label":
                    w.configure(bg=T["BG"], fg=T["MUTED"])
                elif role == "entry":
                    w.configure(bg=T["ENTRY_BG"], fg=T["ENTRY_FG"],
                                insertbackground=T["ACCENT"],
                                highlightbackground=T["BORDER"],
                                highlightcolor=T["ACCENT"])
                elif role == "text":
                    w.configure(bg=T["ENTRY_BG"], fg=T["ENTRY_FG"],
                                insertbackground=T["ACCENT"])
                elif role == "log":
                    w.configure(bg=T["LOG_BG"], fg=T["LOG_FG"])
                elif role == "result":
                    w.configure(bg=T["LOG_BG"], fg=T["ACCENT"],
                                insertbackground=T["ACCENT"])
                elif role == "help":
                    w.configure(bg=T["PANEL"], fg=T["FG"])
                elif role == "about":
                    w.configure(bg=T["PANEL"], fg=T["ACCENT"])
                elif role == "status":
                    w.configure(bg=T["STATUS_BG"], fg=T["STATUS_FG"])
                elif role == "chk":
                    w.configure(bg=T["BG"], fg=T["FG"],
                                selectcolor=T["PANEL"],
                                activebackground=T["BG"],
                                activeforeground=T["ACCENT"])
                elif role == "chk_frame":
                    w.configure(bg=T["BG"])
                elif role == "btn_row":
                    w.configure(bg=T["BG"])
                elif role == "title_bar":
                    w.configure(bg=T["BG"])
            except tk.TclError:
                pass

        # update toggle button label
        toggle_btn.configure(text=T["TOGGLE_ICON"])

    def toggle_theme():
        apply_theme("light" if current_theme.get() == "dark" else "dark")

    # ===========================================================
    # TITLE BAR
    # ===========================================================
    T = THEMES["dark"]

    title_bar = reg(tk.Frame(root, bg=T["BG"]), "title_bar")
    title_bar.pack(fill=tk.X, padx=12, pady=(10, 0))

    reg(tk.Label(title_bar, text="◈ PRO STEGHIDE",
                 bg=T["BG"], fg=T["ACCENT"],
                 font=("Consolas", 16, "bold")), "title").pack(side=tk.LEFT)

    reg(tk.Label(title_bar, text="  UNIVERSAL EDITION",
                 bg=T["BG"], fg=T["MUTED"],
                 font=("Consolas", 10)), "subtitle").pack(side=tk.LEFT, pady=4)

    toggle_btn = ttk.Button(title_bar, text=T["TOGGLE_ICON"],
                            style="Toggle.TButton", command=toggle_theme)
    toggle_btn.pack(side=tk.RIGHT, padx=6)

    reg(tk.Label(root,
                 text="Images · Audio · Video · PDF · Any File  |  steghide + ffmpeg + LSB",
                 bg=T["BG"], fg=T["MUTED"],
                 font=("Consolas", 9)), "subtitle").pack(anchor="w", padx=16, pady=(0, 4))

    # ===========================================================
    # NOTEBOOK
    # ===========================================================
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

    tab_main  = ttk.Frame(notebook)
    tab_log   = ttk.Frame(notebook)
    tab_help  = ttk.Frame(notebook)
    tab_about = ttk.Frame(notebook)

    for tab, label in [
        (tab_main,  "  Main  "),
        (tab_log,   "  Log   "),
        (tab_help,  "  Help  "),
        (tab_about, "  About "),
    ]:
        notebook.add(tab, text=label)

    # ===========================================================
    # MAIN TAB
    # ===========================================================
    main = reg(tk.Frame(tab_main, bg=T["BG"], padx=12, pady=8), "bg")
    main.pack(fill=tk.BOTH, expand=True)

    entries = []   # keep refs for re-theme

    def mk_entry(parent, row, label_text, show=None):
        lbl = reg(tk.Label(parent, text=label_text, bg=T["BG"], fg=T["MUTED"],
                           font=("Consolas", 9)), "label")
        lbl.grid(row=row, column=0, sticky="w", pady=3)
        e = tk.Entry(parent, bg=T["ENTRY_BG"], fg=T["ENTRY_FG"],
                     insertbackground=T["ACCENT"], font=FONT, relief="flat",
                     highlightthickness=1, highlightbackground=T["BORDER"],
                     highlightcolor=T["ACCENT"], show=show or "")
        e.grid(row=row, column=1, sticky="ew", padx=6, pady=3)
        reg(e, "entry")
        return e

    fi = ttk.LabelFrame(main, text=" Inputs ", padding=10)
    fi.pack(fill=tk.X)

    BROWSE_TYPES = ("All Supported",
                    "*.jpg *.jpeg *.bmp *.wav *.au *.png *.gif *.tiff "
                    "*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv "
                    "*.pdf *.mp3 *.flac *.ogg *.zip *.bin *.dat *.*")

    def browse(entry, save=False):
        if save:
            path = filedialog.asksaveasfilename()
        else:
            path = filedialog.askopenfilename(
                filetypes=[BROWSE_TYPES, ("All Files", "*.*")])
        if path:
            entry.delete(0, tk.END)
            entry.insert(0, path)

    cover_entry = mk_entry(fi, 0, "Cover File")
    ttk.Button(fi, text="Browse", style="Gray.TButton",
               command=lambda: browse(cover_entry)).grid(row=0, column=2, padx=4)

    out_entry = mk_entry(fi, 1, "Save Extracted To (optional)")
    ttk.Button(fi, text="Browse", style="Gray.TButton",
               command=lambda: browse(out_entry, save=True)).grid(row=1, column=2, padx=4)

    data_entry = mk_entry(fi, 2, "Data File (for embed)")
    ttk.Button(fi, text="Browse", style="Gray.TButton",
               command=lambda: browse(data_entry)).grid(row=2, column=2, padx=4)

    pwd_entry = mk_entry(fi, 3, "Password (required)", show="*")

    fi.columnconfigure(1, weight=1)

    # checkboxes
    chk_row = reg(tk.Frame(fi, bg=T["BG"]), "chk_frame")
    chk_row.grid(row=4, column=0, columnspan=3, sticky="w", pady=6)

    use_text_var = tk.BooleanVar()
    encrypt_var  = tk.BooleanVar()
    decrypt_var  = tk.BooleanVar()

    chk_widgets = []
    for text, var in [
        ("Embed Direct Text",     use_text_var),
        ("Encrypt Before Embed",  encrypt_var),
        ("Decrypt After Extract", decrypt_var),
    ]:
        c = tk.Checkbutton(chk_row, text=text, variable=var,
                           bg=T["BG"], fg=T["FG"], selectcolor=T["PANEL"],
                           activebackground=T["BG"], activeforeground=T["ACCENT"],
                           font=FONT)
        c.pack(side=tk.LEFT, padx=10)
        reg(c, "chk")

    reg(tk.Label(fi, text="Direct Text:", bg=T["BG"], fg=T["MUTED"],
                 font=("Consolas", 9)), "label").grid(row=5, column=0, sticky="nw")

    text_input = scrolledtext.ScrolledText(fi, height=4,
                                           bg=T["ENTRY_BG"], fg=T["ENTRY_FG"],
                                           insertbackground=T["ACCENT"],
                                           font=FONT, relief="flat",
                                           highlightthickness=1,
                                           highlightbackground=T["BORDER"])
    text_input.grid(row=5, column=1, columnspan=2, sticky="ew", pady=4)
    reg(text_input, "text")

    # action buttons
    btn_row = reg(tk.Frame(main, bg=T["BG"]), "btn_row")
    btn_row.pack(fill=tk.X, pady=8)

    status_var = tk.StringVar(value="Ready")

    def require_pwd():
        p = pwd_entry.get().strip()
        if not p:
            messagebox.showwarning("Password Required",
                                   "A password is required for all operations.")
            pwd_entry.focus_set()
            return None
        return p

    def do_embed():
        pwd = require_pwd()
        if not pwd:
            return
        cover = cover_entry.get().strip()
        if not cover or not os.path.exists(cover):
            messagebox.showerror("Error", "Select a valid cover file.")
            return
        if use_text_var.get():
            text = text_input.get("1.0", tk.END).strip()
            if not text:
                messagebox.showerror("Error", "No text entered.")
                return
            payload = encrypt_data(text, pwd) if encrypt_var.get() else text.encode()
        else:
            ef = data_entry.get().strip()
            if not ef or not os.path.exists(ef):
                messagebox.showerror("Error", "Select a valid data file.")
                return
            with open(ef, "rb") as f:
                raw = f.read()
            payload = encrypt_data(raw.decode(errors="replace"), pwd) \
                      if encrypt_var.get() else raw
        try:
            universal_embed(cover, payload, pwd, log_box)
            status_var.set("✓  Embed complete")
            notebook.select(tab_log)
        except Exception as exc:
            messagebox.showerror("Embed Error", str(exc))
            _log(log_box, f"[ERR] {exc}")

    def do_extract():
        pwd = require_pwd()
        if not pwd:
            return
        cover = cover_entry.get().strip()
        if not cover or not os.path.exists(cover):
            messagebox.showerror("Error", "Select a valid cover / stego file.")
            return
        try:
            data = universal_extract(cover, pwd, log_box)
        except Exception as exc:
            messagebox.showerror("Extract Error", str(exc))
            _log(log_box, f"[ERR] {exc}")
            return
        if decrypt_var.get():
            text = decrypt_data(data, pwd)
            if text is None:
                messagebox.showerror("Decrypt Failed",
                                     "Decryption failed — wrong password or not encrypted.")
                return
            display = text
        else:
            display = data.decode(errors="ignore")

        result_box.config(state="normal")
        result_box.delete("1.0", tk.END)
        result_box.insert(tk.END, display)
        result_box.config(state="disabled")

        out = out_entry.get().strip()
        if out:
            with open(out, "wb") as f:
                f.write(data)
            _log(log_box, f"[OK] Saved extracted data → {out}")
        status_var.set("✓  Extraction complete")

    def do_save():
        content = result_box.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo("Nothing to save", "No extracted data in output box.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            with open(path, "w") as f:
                f.write(content)
            status_var.set(f"✓  Saved → {os.path.basename(path)}")

    def do_clear(event=None):
        for e in (cover_entry, data_entry, pwd_entry, out_entry):
            e.delete(0, tk.END)
        text_input.delete("1.0", tk.END)
        use_text_var.set(False)
        encrypt_var.set(False)
        decrypt_var.set(False)
        result_box.config(state="normal")
        result_box.delete("1.0", tk.END)
        result_box.config(state="disabled")
        status_var.set("⟳  Reset")

    for label, cmd, s in [
        ("EMBED",       do_embed,   "Green.TButton"),
        ("EXTRACT",     do_extract, "Green.TButton"),
        ("SAVE OUTPUT", do_save,    "Gray.TButton"),
        ("CLEAR / ESC", do_clear,   "Red.TButton"),
    ]:
        ttk.Button(btn_row, text=label, command=cmd, style=s).pack(side=tk.LEFT, padx=5)

    rf = ttk.LabelFrame(main, text=" Extracted Output ", padding=8)
    rf.pack(fill=tk.BOTH, expand=True, pady=6)
    result_box = scrolledtext.ScrolledText(rf, state="disabled",
                                           bg=T["LOG_BG"], fg=T["ACCENT"],
                                           font=("Consolas", 10), relief="flat",
                                           insertbackground=T["ACCENT"])
    result_box.pack(fill=tk.BOTH, expand=True)
    reg(result_box, "result")

    status_lbl = reg(tk.Label(root, textvariable=status_var,
                              bg=T["STATUS_BG"], fg=T["STATUS_FG"],
                              font=("Consolas", 9), anchor="w", padx=10), "status")
    status_lbl.pack(side=tk.BOTTOM, fill=tk.X)

    root.bind("<Escape>", do_clear)

    # ===========================================================
    # LOG TAB
    # ===========================================================
    lf = reg(tk.Frame(tab_log, bg=T["BG"]), "bg")
    lf.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

    log_box = scrolledtext.ScrolledText(lf, state="disabled",
                                        bg=T["LOG_BG"], fg=T["LOG_FG"],
                                        font=("Consolas", 10), relief="flat")
    log_box.pack(fill=tk.BOTH, expand=True)
    reg(log_box, "log")

    ttk.Button(lf, text="Clear Log", style="Red.TButton",
               command=lambda: (
                   log_box.config(state="normal"),
                   log_box.delete("1.0", tk.END),
                   log_box.config(state="disabled"),
               )).pack(anchor="e", pady=4)

    # ===========================================================
    # HELP TAB
    # ===========================================================
    help_txt = """
PRO STEGHIDE GUI — Universal Edition
══════════════════════════════════════════════════════

SUPPORTED FORMATS & ENGINES
────────────────────────────
  .jpg .jpeg .bmp .wav .au  →  steghide        (modifies file in-place)
  .mp4 .mkv .avi .mov .webm →  ffmpeg metadata (writes new .steg.ext file)
  .png .gif .tiff .ppm      →  LSB pixel engine (writes new .steg.png)
  .pdf .mp3 .flac .ogg      →  LSB binary      (writes new .steg file)
  .zip .bin .dat  + any     →  LSB binary      (writes new .steg file)

HOW TO EMBED
────────────
  1. Cover File  — pick the carrier (image / audio / video / pdf / any file)
  2. Data File   — pick the secret file to hide   OR
     tick "Embed Direct Text" and type/paste the message below
  3. Password    — mandatory; used for steghide AND optional encryption
  4. Encrypt     — tick "Encrypt Before Embed" for AES-256 encryption
  5. Click EMBED — watch the Log tab for the output path

HOW TO EXTRACT
──────────────
  1. Cover File  — open the stego file (original or .steg copy)
  2. Password    — same password used during embed
  3. Decrypt     — tick "Decrypt After Extract" if data was encrypted
  4. Click EXTRACT — result appears in the output box below
  5. Use SAVE OUTPUT or set "Save Extracted To" to write to disk

NOTES
─────
  • steghide modifies the original file in-place.
  • All other engines produce a new file alongside the original.
  • Pillow (PIL) improves PNG/GIF/TIFF LSB quality:
      pip install pillow
  • ESC or CLEAR resets all fields.
  • Passwords are never stored or logged.
  • Click ☀ / 🌙 button in the title bar to toggle dark/light theme.

INSTALL DEPENDENCIES
────────────────────
  sudo apt install steghide ffmpeg
  pip install cryptography pillow
"""
    hb = scrolledtext.ScrolledText(tab_help, bg=T["PANEL"], fg=T["FG"],
                                    font=("Consolas", 10), relief="flat")
    hb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    hb.insert(tk.END, help_txt)
    hb.config(state="disabled")
    reg(hb, "help")

    # ===========================================================
    # ABOUT TAB
    # ===========================================================
    about_txt = """

  PRO STEGHIDE GUI — Universal Edition
  ─────────────────────────────────────────────

  Version   : 3.0
  Platform  : Kali Linux / Debian / Ubuntu
  Author    : Bhavya Sehgal

  Engines included
  ────────────────
  ✦ steghide      — JPEG, BMP, WAV, AU
  ✦ ffmpeg        — MP4, MKV, AVI, MOV, WEBM (metadata)
  ✦ LSB Image     — PNG, GIF, TIFF, PPM (pixel LSB)
  ✦ LSB Binary    — PDF, MP3, FLAC, OGG, ZIP, any file

  Security
  ────────
  ✦ AES-256 encryption (Fernet) with SHA-256 key derivation
  ✦ Custom LSTEG magic header for reliable detection
  ✦ Password never stored or logged

  Theme
  ─────
  ✦ Dark mode  (green-on-black terminal aesthetic)
  ✦ Light mode (clean slate / professional)
  Toggle via the ☀ / 🌙 button in the title bar.

  Use this tool for authorized security research,
  CTF challenges, and lawful privacy purposes only.

"""
    ab = scrolledtext.ScrolledText(tab_about, bg=T["PANEL"], fg=T["ACCENT"],
                                    font=("Consolas", 11), relief="flat")
    ab.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    ab.insert(tk.END, about_txt)
    ab.config(state="disabled")
    reg(ab, "about")

    # apply initial theme to paint everything correctly
    apply_theme("dark")

    root.mainloop()

# ===========================================================
if __name__ == "__main__":
    create_gui()
