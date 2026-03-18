#!/usr/bin/env python3
# ===========================================================
#           PRO AUTO DECODER GUI — FULL MIXED LAYER
#           Fixed & Improved Version
# ===========================================================

import time
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import base64, binascii, string, json, os
import urllib.parse
import html
from datetime import datetime

# History configuration
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "decoder_history.json")
HISTORY_LIMIT = 100
history = []

# Theme definitions
THEMES = {
    'Light': {
        'bg': '#f0f0f0',
        'text_bg': '#ffffff',
        'button_bg': '#1A7F3B',
        'clear_button_bg': '#8B0000',
        'accent': '#0D47A1',
        'text': '#333333',
        'sidebar_bg': '#e0e0e0',
        'frame_bg': '#ffffff',
        'highlight': '#e3f2fd',
        'button_hover': '#145C2B',
        'clear_hover': '#6B0000',
        'label_fg': '#333333',
    },
    'Dark': {
        'bg': '#2d2d2d',
        'text_bg': '#1e1e1e',
        'button_bg': '#1E90FF',
        'clear_button_bg': '#E63E3E',
        'accent': '#0A3D7A',
        'text': '#e0e0e0',
        'disabled': '#757575',
        'sidebar_bg': '#252526',
        'frame_bg': '#333333',
        'highlight': '#44475a',
        'button_hover': '#1C86EE',
        'clear_hover': '#4B0000',
        'label_fg': '#e0e0e0',
    },
    'Solarized': {
        'bg': '#fdf6e3',
        'text_bg': '#eee8d5',
        'button_bg': '#4A4A8F',
        'clear_button_bg': '#A51C1C',
        'accent': '#268bd2',
        'text': '#586e75',
        'disabled': '#93a1a1',
        'sidebar_bg': '#eee8d5',
        'frame_bg': '#fdf6e3',
        'highlight': '#b58900',
        'button_hover': '#2A8E43',
        'clear_hover': '#B83030',
        'label_fg': '#586e75',
    },
    'Dracula': {
        'bg': '#282a36',
        'text_bg': '#44475a',
        'button_bg': '#3DC55D',
        'clear_button_bg': '#E63E3E',
        'accent': '#bd93f9',
        'text': '#f8f8f2',
        'disabled': '#6272a4',
        'sidebar_bg': '#21222C',
        'frame_bg': '#343746',
        'highlight': '#44475a',
        'button_hover': '#2A8E43',
        'clear_hover': '#B83030',
        'label_fg': '#f8f8f2',
    }
}

current_theme = 'Light'

# ===========================================================
# UTILITY
# ===========================================================

def is_good_text(s):
    """Check if a string is mostly printable ASCII."""
    try:
        printable = sum(c in string.printable for c in s)
        return printable / max(len(s), 1) > 0.85
    except:
        return False


def looks_like_plain_text(s):
    """Check if input already looks like readable English."""
    common_words = [
        "the", "and", "hello", "world", "this", "that",
        "flag", "ctf", "you", "have", "are", "is", "was",
        "for", "not", "with", "from", "they", "will"
    ]
    words = s.lower().split()
    matches = sum(1 for w in words if w in common_words)
    return matches >= 1


def is_likely_encoded(s):
    """Returns True if the string is plausibly encoded (not already readable plain text)."""
    if not s:
        return False
    if any(c in '+/=\\.%&;-_' for c in s):
        return True
    clean = s.replace(' ', '').replace('\n', '')
    if all(c in '0123456789abcdefABCDEF' for c in clean) and len(clean) >= 4 and len(clean) % 2 == 0:
        return True
    if is_good_text(s) and len(s) > 20 and looks_like_plain_text(s):
        return False
    return True

ENCODING_HINT_CHARS = set('+/=.%&;-_')


def has_encoding_hints(s):
    """Returns True if string still contains characters suggesting further encoding."""
    return any(c in ENCODING_HINT_CHARS for c in s)


def decode_hex(s):
    try:
        clean = s.replace(" ", "").replace("\n", "")
        if len(clean) < 4:
            return None
        if len(clean) % 2 != 0:
            return None
        # Must be ALL hex characters
        if not all(c in '0123456789abcdefABCDEF' for c in clean):
            return None
        result = binascii.unhexlify(clean).decode('latin-1')
        # Result can be another encoded string (multi-layer) or plain text
        printable = sum(c in string.printable for c in result)
        if printable / max(len(result), 1) < 0.85:
            return None
        return result
    except:
        return None
def decode_ascii_decimal(s):
    try:
        nums = s.strip().split()
        if not nums or len(nums) < 2:
            return None
        # All tokens must be digit strings
        if not all(n.isdigit() for n in nums):
            return None
        # Reject if ALL tokens are exactly 7 or 8 chars of only 0s/1s — that's binary
        if all(len(n) in (7, 8) and set(n) <= {'0', '1'} for n in nums):
            return None
        values = [int(n) for n in nums]
        # ASCII decimal values must be in printable range
        if not all(32 <= v <= 126 for v in values):
            return None
        result = "".join(chr(v) for v in values)
        if not is_good_text(result):
            return None
        return result
    except:
        return None


def decode_binary(s):
    try:
        bits = s.strip().split()
        if not bits or len(bits) < 2:
            return None
        if not all(set(b) <= {'0', '1'} for b in bits):
            return None
        if not all(len(b) in (7, 8) for b in bits):
            return None
        # Allow mixed 7-bit and 8-bit tokens
        result = "".join(chr(int(b, 2)) for b in bits)
        return result if is_good_text(result) else None
    except:
        return None

def decode_base64(s):
    try:
        s = s.strip()
        if len(s) < 4:
            return None
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r")
        if not set(s) <= allowed:
            return None
        # If the string looks like a pure hex string (all hex chars, even length,
        # no +/= padding chars), let the Hex decoder handle it instead
        hex_only = set("0123456789abcdefABCDEF")
        if set(s) <= hex_only and len(s) % 2 == 0:
            return None
        padding = len(s) % 4
        if padding:
            s += "=" * (4 - padding)
        decoded = base64.b64decode(s).decode("utf-8", errors="ignore")
        if decoded.strip() == s.strip():
            return None
        if not is_good_text(decoded):
            return None
        return decoded
    except:
        return None


def decode_base32(s):
    try:
        s_upper = s.upper().strip()
        if len(s_upper) < 4:
            return None
        if not set(s_upper) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567="):
            return None
        if not any(c in s_upper for c in "234567="):
            return None
        padded = s_upper + "=" * ((8 - (len(s_upper) % 8)) % 8)
        decoded = base64.b32decode(padded).decode('latin-1')
        printable = sum(c in string.printable for c in decoded)
        return decoded if printable / max(len(decoded), 1) >= 0.85 else None
    except:
        return None

def decode_base58(s):
    try:
        s = s.strip()
        if not s:
            return None
        if not all(c in BASE58_CHARS for c in s):
            return None
        num = 0
        for c in s:
            num = num * 58 + BASE58_CHARS.index(c)
        byte_length = (num.bit_length() + 7) // 8
        if byte_length == 0:
            return None
        decoded_bytes = num.to_bytes(byte_length, "big")
        decoded = decoded_bytes.decode("utf-8", errors="ignore")
        if not decoded or not is_good_text(decoded):
            return None
        # Stronger printable check for Base58
        printable_ratio = sum(c in string.printable and c not in '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f' for c in decoded) / max(len(decoded), 1)
        if printable_ratio < 0.95:
            return None
        return decoded
    except:
        return None


def decode_base85(s):
    try:
        s = s.strip()
        allowed = set(
            "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
            "!#$%&()*+-;<=>?@^_`{|}~"
        )
        if not set(s) <= allowed:
            return None
        if len(s) < 5:
            return None
        decoded = base64.a85decode(s, adobe=False, ignorechars=b"")
        text = decoded.decode("utf-8", errors="ignore")
        if not text or not is_good_text(text):
            return None
        return text
    except:
        return None


def decode_url(s):
    try:
        decoded = urllib.parse.unquote(s)
        if decoded != s:
            return decoded
    except:
        pass
    return None


def decode_html_entities(s):
    try:
        decoded = html.unescape(s)
        if decoded != s:
            return decoded
    except:
        pass
    return None


def decode_rot13(s):
    # Don't decode already readable English
    if looks_like_plain_text(s):
        return None
    letters = sum(c.isalpha() for c in s)
    if len(s) == 0 or letters / len(s) < 0.6:
        return None
    rot = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm"
    )
    decoded = s.translate(rot)
    if decoded.lower() == s.lower():
        return None
    # Output must actually look like English words, not just printable chars.
    # is_good_text alone is too weak — every letter-only string passes it.
    if not looks_like_plain_text(decoded):
        return None
    return decoded


def decode_rot47(s):
    if looks_like_plain_text(s):
        return None
    printable = sum(33 <= ord(c) <= 126 for c in s)
    if len(s) == 0 or printable / len(s) < 0.9:
        return None
    result = ""
    for c in s:
        o = ord(c)
        if 33 <= o <= 126:
            result += chr(33 + ((o - 33 + 47) % 94))
        else:
            result += c
    if result == s:
        return None
    if not is_good_text(result):
        return None
    # Same guard as ROT13 — output must contain actual English words
    if not looks_like_plain_text(result):
        return None
    return result


MORSE = {
    '.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E',
    '..-.': 'F', '--.': 'G', '....': 'H', '..': 'I', '.---': 'J',
    '-.-': 'K', '.-..': 'L', '--': 'M', '-.': 'N', '---': 'O',
    '.--.': 'P', '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T',
    '..-': 'U', '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y',
    '--..': 'Z', '-----': '0', '.----': '1', '..---': '2',
    '...--': '3', '....-': '4', '.....': '5', '-....': '6',
    '--...': '7', '---..': '8', '----.': '9'
}

def decode_morse(s):
    s_clean = ' '.join(s.split())
    if not set(s_clean) <= {'.', '-', ' ', '/'}:
        return None
    try:
        words = s_clean.strip().split(' / ')
        out = " ".join("".join(MORSE.get(l, "?") for l in w.split()) for w in words)
        return out if len(out) > 1 and '?' not in out else None
    except:
        return None

def decode_caesar(s):
    """Brute-force Caesar cipher — tries all 25 shifts except 13 (that is ROT13)."""
    if not s:
        return None
    # Need at least 2 words to avoid false positives on single letters/short strings
    if len(s.split()) < 2:
        return None
    # Skip if already readable plain English
    if looks_like_plain_text(s):
        return None
    common_words = [
        "the", "and", "hello", "world", "flag", "ctf",
        "you", "are", "this", "that", "from", "have",
        "there", "is", "secret", "a", "was", "not", "with",
        "for", "they", "will", "been", "has", "had", "but",
    ]
    # Skip shift 13 — ROT13 handles that case
    for shift in [n for n in range(1, 26) if n != 13]:
        result = ""
        for c in s:
            if c.isalpha():
                base = ord('A') if c.isupper() else ord('a')
                result += chr((ord(c) - base + shift) % 26 + base)
            else:
                result += c
        if sum(1 for w in result.lower().split() if w in common_words) >= 1:
            return result
    return None


def decode_octal(s):
    """Decode space-separated octal values."""
    try:
        parts = s.strip().split()
        if not parts:
            return None
        if not all(all(c in '01234567' for c in p) for p in parts):
            return None
        chars = [chr(int(p, 8)) for p in parts]
        result = "".join(chars)
        if not is_good_text(result):
            return None
        return result
    except:
        return None


def decode_base64_url(s):
    """Decode URL-safe Base64 (uses - and _ instead of + and /)."""
    try:
        s = s.strip()
        if len(s) < 2:
            return None
        if '-' not in s and '_' not in s:
            return None
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=")
        if not set(s) <= allowed:
            return None
        converted = s.replace('-', '+').replace('_', '/')
        padding = len(converted) % 4
        if padding:
            converted += "=" * (4 - padding)
        decoded = base64.b64decode(converted).decode("utf-8", errors="ignore")
        if decoded.strip() == s.strip():
            return None
        return decoded if is_good_text(decoded) and len(decoded.strip()) >= 1 else None
    except:
        return None



# ===========================================================
# AUTO DETECTION
# ===========================================================

DECODERS = [
    ("Morse",         decode_morse),
    ("Binary",        decode_binary),
    ("ASCII Decimal", decode_ascii_decimal),
    ("Hex",           decode_hex),
    ("Base64",        decode_base64),
    ("Base64 URL",    decode_base64_url),
    ("Base32",        decode_base32),
    ("Base58",        decode_base58),
    ("URL",           decode_url),
    ("HTML",          decode_html_entities),
    ("Caesar",        decode_caesar),
    ("ROT13",         decode_rot13),
    ("ROT47",         decode_rot47),
]


def auto_decode(s):
    """Try each decoder and return the first successful (name, result) pair."""
    if not is_likely_encoded(s):
        return None

    for name, func in DECODERS:
        try:
            result = func(s)
            if result is None:
                continue
            if result.strip() == s.strip():
                continue
            return name, result
        except:
            continue

    return None


def auto_decode_multi_layer(s, max_layers=10):
    """Recursively decode until plain clean text or no decoder matches."""
    layers = []
    current = s.strip()
    seen = set()
    start_time = time.time()

    for _ in range(max_layers):
        if time.time() - start_time > 2.5:
            break
        if current in seen:
            break
        seen.add(current)

        decoded = auto_decode(current)
        if decoded is None:
            break

        enc_type, result = decoded
        if not result:
            break

        result = result.strip()
        if result in seen:
            break

        layers.append((enc_type, result))

        # Stop only when result is readable AND free of encoding hint characters
        if looks_like_plain_text(result) and is_good_text(result) and not has_encoding_hints(result):
            break

        current = result

    return layers


# ===========================================================
# HISTORY
# ===========================================================

def load_history():
    global history
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = []
    return history


def save_history():
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Warning: Could not save history: {e}")


def add_to_history(input_text, result, enc_type):
    global history
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        'timestamp': timestamp,
        'input': input_text,
        'result': result,
        'type': enc_type
    }
    history.insert(0, entry)
    if len(history) > HISTORY_LIMIT:
        history = history[:HISTORY_LIMIT]
    save_history()

# ===========================================================
# DECODER NAME LIST (for Manual Mode dropdown)
# ===========================================================

DECODER_NAMES = [n for n, _ in DECODERS]

MANUAL_DECODER_MAP = {
    "Base64":        decode_base64,
    "Base64 URL":    decode_base64_url,
    "Base32":        decode_base32,
    "Base58":        decode_base58,
    "Base85":        decode_base85,
    "Hex":           decode_hex,
    "Binary":        decode_binary,
    "Octal":         decode_octal,
    "ASCII Decimal": decode_ascii_decimal,
    "URL":           decode_url,
    "HTML":          decode_html_entities,
    "ROT13":         decode_rot13,
    "ROT47":         decode_rot47,
    "Caesar":        decode_caesar,
    "Morse":         decode_morse,
}


# ===========================================================
# DECODER NAME LIST (for Manual Mode dropdown)
# ===========================================================

DECODER_NAMES = [n for n, _ in DECODERS]

MANUAL_DECODER_MAP = {
    "Base64":        decode_base64,
    "Base64 URL":    decode_base64_url,
    "Base32":        decode_base32,
    "Base58":        decode_base58,
    "Base85":        decode_base85,
    "Hex":           decode_hex,
    "Binary":        decode_binary,
    "Octal":         decode_octal,
    "ASCII Decimal": decode_ascii_decimal,
    "URL":           decode_url,
    "HTML":          decode_html_entities,
    "ROT13":         decode_rot13,
    "ROT47":         decode_rot47,
    "Caesar":        decode_caesar,
    "Morse":         decode_morse,
}

# ===========================================================
# THEME HELPERS
# ===========================================================

def apply_theme(theme_name):
    global current_theme
    current_theme = theme_name
    theme = THEMES[theme_name]

    root.config(bg=theme['bg'])
    menubar.config(bg=theme['bg'], fg=theme['text'])

    for frame in [main_frame, input_frame, result_frame, button_frame, sidebar_frame]:
        try:
            frame.config(style=f"{theme_name}.TFrame")
        except:
            pass

    text_input.config(
        bg=theme['text_bg'], fg=theme['text'],
        insertbackground=theme['text'], selectbackground=theme['accent']
    )

    decode_btn.config(style=f"{theme_name}.TButton")
    clear_btn.config(style=f"{theme_name}.Clear.TButton")
    copy_btn.config(style=f"{theme_name}.TButton")

    status_bar.config(bg=theme['accent'], fg='white')

    for lbl in sidebar_labels:
        lbl.config(bg=theme['bg'], fg=theme['label_fg'])

    for name, btn in theme_buttons.items():
        if name == theme_name:
            btn.config(style=f"{theme_name}.Active.TButton")
        else:
            btn.config(style=f"{theme_name}.TButton")

    text_input.tag_configure("highlight", background=theme['highlight'])
    _refresh_result_display()
    update_status(f"Theme changed to {theme_name}", "info")


# ===========================================================
# RESULT DISPLAY — shared render engine
# ===========================================================

_last_layers = []


def _refresh_result_display():
    """Re-render the result display using _last_layers with current theme colors."""
    theme = THEMES[current_theme]
    result_display.config(state='normal')
    result_display.delete("1.0", tk.END)

    result_display.tag_configure(
        "header", font=('Segoe UI', 10, 'bold'), foreground=theme['accent'])
    result_display.tag_configure(
        "output", font=('Consolas', 10), foreground=theme['text'])
    result_display.tag_configure(
        "error", font=('Segoe UI', 10), foreground='#cc0000')

    for widget in layer_buttons_frame.winfo_children():
        widget.destroy()

    if not _last_layers:
        result_display.config(state='disabled')
        return

    for i, (enc, res) in enumerate(_last_layers, 1):
        header_text = f"Layer {i} ({enc}):\n"
        result_display.insert(tk.END, header_text, "header")
        result_display.insert(tk.END, res + "\n\n", "output")

        btn_text = f"Copy Layer {i}"
        btn = tk.Button(
            layer_buttons_frame,
            text=btn_text,
            font=('Segoe UI', 8),
            bg=theme['button_bg'],
            fg='white',
            activebackground=theme.get('button_hover', theme['button_bg']),
            activeforeground='white',
            relief='flat',
            padx=6, pady=2,
            cursor='hand2',
            command=lambda r=res: _copy_text(r)
        )
        btn.pack(side=tk.LEFT, padx=3, pady=2)

    result_display.config(state='disabled')


def _copy_text(text):
    root.clipboard_clear()
    root.clipboard_append(text)
    preview = text[:40] + ('...' if len(text) > 40 else '')
    update_status(f"Copied: {preview}", "success")


# ===========================================================
# GUI ACTIONS — AUTO MODE
# ===========================================================

def decode_input(event=None):
    global _last_layers
    # Don't fire when Enter is pressed inside a Combobox
    if event and hasattr(event, 'widget'):
        wclass = event.widget.winfo_class()
        if wclass in ('TCombobox', 'Entry'):
            return

    user_text = text_input.get("1.0", tk.END).strip()
    if not user_text:
        update_status("No input provided.", "error")
        return

    update_status("Decoding...", "info")
    root.update()

    try:
        layers = auto_decode_multi_layer(user_text)
        _last_layers = layers
        _refresh_result_display()

        if layers:
            result = layers[-1][1]
            enc_type = " \u2192 ".join(e for e, _ in layers)
            update_status(f"Decoded {len(layers)} layer(s): {enc_type}", "success")
            add_to_history(user_text, result, enc_type)
        else:
            result_display.config(state='normal')
            result_display.insert(tk.END, "[!] Unable to decode automatically.\n\n", "error")
            result_display.insert(
                tk.END,
                "Tried: " + ", ".join(n for n, _ in DECODERS) + "\n",
                "output"
            )
            result_display.config(state='disabled')
            update_status("Could not decode input.", "error")

    except Exception as e:
        update_status(f"Error: {str(e)}", "error")
        messagebox.showerror("Error", f"An error occurred: {str(e)}")


# ===========================================================
# GUI ACTIONS — MANUAL MODE
# ===========================================================

def manual_decode():
    global _last_layers
    user_text = text_input.get("1.0", tk.END).strip()
    if not user_text:
        update_status("No input provided.", "error")
        return

    chosen = manual_decoder_var.get()
    fn = MANUAL_DECODER_MAP.get(chosen)
    if not fn:
        update_status(f"Unknown decoder: {chosen}", "error")
        return

    try:
        result = fn(user_text)
        if result is None:
            _last_layers = []
            result_display.config(state='normal')
            result_display.delete("1.0", tk.END)
            result_display.tag_configure("error", font=('Segoe UI', 10), foreground='#cc0000')
            result_display.insert(
                tk.END,
                f"[!] {chosen} decoder could not decode this input.\n", "error"
            )
            result_display.config(state='disabled')
            update_status(f"{chosen}: failed to decode.", "error")
        else:
            _last_layers = [(chosen, result)]
            _refresh_result_display()
            update_status(f"Manual decode via {chosen} succeeded.", "success")
            add_to_history(user_text, result, chosen)
    except Exception as e:
        update_status(f"Error: {str(e)}", "error")
        messagebox.showerror("Error", str(e))


# ===========================================================
# GUI ACTIONS — PIPELINE MODE
# ===========================================================

def run_pipeline():
    global _last_layers
    user_text = text_input.get("1.0", tk.END).strip()
    if not user_text:
        update_status("No input provided.", "error")
        return

    steps = []
    for var in pipeline_step_vars:
        v = var.get().strip()
        if v and v != "\u2014 select \u2014":
            steps.append(v)

    if not steps:
        update_status("Add at least one step to the pipeline.", "error")
        return

    current = user_text
    layers = []
    for step in steps:
        fn = MANUAL_DECODER_MAP.get(step)
        if not fn:
            update_status(f"Unknown step: {step}", "error")
            return
        try:
            result = fn(current)
        except Exception:
            result = None

        if result is None:
            _last_layers = layers
            _refresh_result_display()
            result_display.config(state='normal')
            result_display.tag_configure("error", font=('Segoe UI', 10), foreground='#cc0000')
            result_display.insert(
                tk.END,
                f"\n[!] Pipeline stopped: {step} could not decode at this stage.\n",
                "error"
            )
            result_display.config(state='disabled')
            update_status(f"Pipeline failed at step: {step}", "error")
            return
        layers.append((step, result))
        current = result

    _last_layers = layers
    _refresh_result_display()
    enc_type = " \u2192 ".join(steps)
    update_status(f"Pipeline complete: {enc_type}", "success")
    if layers:
        add_to_history(user_text, layers[-1][1], enc_type)


def add_pipeline_step():
    if len(pipeline_step_vars) >= 8:
        update_status("Maximum 8 pipeline steps.", "error")
        return
    _build_pipeline_step(len(pipeline_step_vars))
    pipeline_canvas.update_idletasks()
    pipeline_canvas.configure(scrollregion=pipeline_canvas.bbox("all"))


def remove_pipeline_step():
    if not pipeline_step_vars:
        return
    pipeline_step_vars.pop()
    step_frames = [w for w in pipeline_steps_inner.winfo_children()
                   if isinstance(w, tk.Frame)]
    if step_frames:
        step_frames[-1].destroy()
    pipeline_canvas.update_idletasks()
    pipeline_canvas.configure(scrollregion=pipeline_canvas.bbox("all"))


def _build_pipeline_step(idx):
    theme = THEMES[current_theme]
    frame = tk.Frame(pipeline_steps_inner, bg=theme['bg'])
    frame.pack(side=tk.LEFT, padx=2, pady=2)

    if idx > 0:
        tk.Label(frame, text="\u2192", font=('Segoe UI', 12, 'bold'),
                 bg=theme['bg'], fg=theme['accent']).pack(side=tk.LEFT, padx=4)

    var = tk.StringVar(value="\u2014 select \u2014")
    pipeline_step_vars.append(var)

    cb = ttk.Combobox(
        frame, textvariable=var,
        values=list(MANUAL_DECODER_MAP.keys()),
        width=13, state='readonly',
        font=('Segoe UI', 9)
    )
    cb.pack(side=tk.LEFT)


# ===========================================================
# OTHER ACTIONS
# ===========================================================

def clear_text(event=None):
    global _last_layers
    _last_layers = []
    text_input.delete("1.0", tk.END)
    result_display.config(state='normal')
    result_display.delete("1.0", tk.END)
    result_display.config(state='disabled')
    for w in layer_buttons_frame.winfo_children():
        w.destroy()
    update_status("Cleared.", "info")
    text_input.focus_set()


def copy_to_clipboard(event=None):
    content = result_display.get("1.0", tk.END).strip()
    if content:
        root.clipboard_clear()
        root.clipboard_append(content)
        update_status("Copied to clipboard.", "success")
    else:
        update_status("Nothing to copy.", "error")


def update_status(message, msg_type="info"):
    if 'status_bar' not in globals():
        return
    try:
        if not status_bar.winfo_exists():
            return
    except:
        return
    status_var.set(message)
    theme = THEMES.get(current_theme, THEMES['Light'])
    colors = {
        "error":   ('#ffcdd2', '#b71c1c'),
        "success": ('#c8e6c9', '#1b5e20'),
        "info":    (theme.get('accent', '#2196F3'), 'white'),
    }
    bg, fg = colors.get(msg_type, colors["info"])
    status_bar.config(bg=bg, fg=fg)


# ===========================================================
# HISTORY WINDOW
# ===========================================================

def show_history():
    history_window = tk.Toplevel(root)
    history_window.title("Decoding History")
    history_window.geometry("820x600")
    history_window.config(bg=THEMES[current_theme]['bg'])

    container = ttk.Frame(history_window, style=f"{current_theme}.TFrame")
    container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    tk.Label(container, text="Decoding History",
             font=('Segoe UI', 14, 'bold'),
             bg=THEMES[current_theme]['bg'],
             fg=THEMES[current_theme]['label_fg']).pack(pady=(0, 10))

    list_frame = ttk.Frame(container, style=f"{current_theme}.TFrame")
    list_frame.pack(fill=tk.BOTH, expand=True)

    scrollbar = ttk.Scrollbar(list_frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    history_list = tk.Listbox(
        list_frame, yscrollcommand=scrollbar.set,
        font=('Segoe UI', 10),
        bg=THEMES[current_theme]['text_bg'],
        fg=THEMES[current_theme]['text'],
        selectbackground=THEMES[current_theme]['accent'],
        selectforeground='white',
        borderwidth=0, highlightthickness=0
    )
    history_list.pack(fill=tk.BOTH, expand=True)
    scrollbar.config(command=history_list.yview)

    if not history:
        history_list.insert(tk.END, "  (No history yet)")
    else:
        for entry in history:
            preview = f"[{entry['timestamp']}]  {entry['type']}:  {entry['input'][:60]}..."
            history_list.insert(tk.END, preview)

    def view_selected():
        selection = history_list.curselection()
        if not selection:
            messagebox.showinfo("Select Entry", "Please select a history entry first.")
            return
        idx = selection[0]
        if idx >= len(history):
            return
        entry = history[idx]

        view_window = tk.Toplevel(history_window)
        view_window.title("History Entry")
        view_window.geometry("700x520")
        view_window.config(bg=THEMES[current_theme]['bg'])

        vc = ttk.Frame(view_window, style=f"{current_theme}.TFrame")
        vc.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for txt in [f"Timestamp: {entry['timestamp']}", f"Encoding: {entry['type']}"]:
            tk.Label(vc, text=txt, font=('Segoe UI', 9),
                     bg=THEMES[current_theme]['bg'],
                     fg=THEMES[current_theme]['label_fg']).pack(anchor='w')

        tk.Label(vc, text="Input:", font=('Segoe UI', 10, 'bold'),
                 bg=THEMES[current_theme]['bg'],
                 fg=THEMES[current_theme]['label_fg']).pack(anchor='w', pady=(8, 0))

        input_box = scrolledtext.ScrolledText(
            vc, height=7, font=("Consolas", 10),
            bg=THEMES[current_theme]['text_bg'],
            fg=THEMES[current_theme]['text'], wrap=tk.WORD)
        input_box.insert('1.0', entry['input'])
        input_box.config(state='disabled')
        input_box.pack(fill=tk.X, pady=(0, 8))

        tk.Label(vc, text="Output:", font=('Segoe UI', 10, 'bold'),
                 bg=THEMES[current_theme]['bg'],
                 fg=THEMES[current_theme]['label_fg']).pack(anchor='w')

        output_box = scrolledtext.ScrolledText(
            vc, height=10, font=("Consolas", 10),
            bg=THEMES[current_theme]['text_bg'],
            fg=THEMES[current_theme]['text'], wrap=tk.WORD)
        output_box.insert('1.0', entry['result'])
        output_box.config(state='disabled')
        output_box.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(vc, style=f"{current_theme}.TFrame")
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        def load_entry():
            global _last_layers
            text_input.delete('1.0', tk.END)
            text_input.insert('1.0', entry['input'])
            _last_layers = [('History', entry['result'])]
            _refresh_result_display()
            view_window.destroy()
            history_window.destroy()
            text_input.focus_set()
            update_status(f"Loaded entry from {entry['timestamp']}", "success")

        ttk.Button(btn_frame, text="Load This Entry", command=load_entry,
                   style=f"{current_theme}.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close", command=view_window.destroy,
                   style=f"{current_theme}.TButton").pack(side=tk.RIGHT, padx=5)

    def clear_all_history():
        global history
        if messagebox.askyesno("Clear History", "Clear all history? This cannot be undone."):
            history = []
            save_history()
            history_list.delete(0, tk.END)
            history_list.insert(tk.END, "  (History cleared)")
            update_status("History cleared.", "info")

    btn_frame = ttk.Frame(container, style=f"{current_theme}.TFrame")
    btn_frame.pack(fill=tk.X, pady=(10, 0))

    ttk.Button(btn_frame, text="View Selected", command=view_selected,
               style=f"{current_theme}.TButton").pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Clear History", command=clear_all_history,
               style=f"{current_theme}.Clear.TButton").pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Close", command=history_window.destroy,
               style=f"{current_theme}.TButton").pack(side=tk.RIGHT, padx=5)

    history_list.bind('<Double-1>', lambda e: view_selected())


def show_about():
    about_text = (
        "PRO AUTO DECODER GUI\n"
        "v3.0.0 — Manual Mode, Pipeline & Per-Layer Copy\n\n"
        "Modes:\n"
        "  Auto     — smart multi-layer auto-detection\n"
        "  Manual   — force a specific decoder\n"
        "  Pipeline — chain decoders in sequence\n\n"
        "Supported encodings:\n"
        "  Base64, Base64-URL, Base32, Base58, Base85\n"
        "  Hex, Binary, Octal, ASCII Decimal\n"
        "  URL, HTML entities\n"
        "  ROT13, ROT47, Caesar, Morse\n\n"
        "Author: Kookiieeyy"
    )
    messagebox.showinfo("About", about_text)


# ===========================================================
# GUI SETUP
# ===========================================================

def create_gui():
    global root, text_input, result_display, status_var, status_bar
    global main_frame, input_frame, result_frame, button_frame, sidebar_frame
    global decode_btn, clear_btn, copy_btn, theme_buttons, menubar, sidebar_labels
    global manual_decoder_var, layer_buttons_frame
    global pipeline_step_vars, pipeline_steps_inner, pipeline_canvas

    pipeline_step_vars = []

    root = tk.Tk()
    root.title("PRO AUTO DECODER  v3")
    root.geometry("1060x760")
    root.minsize(900, 640)
    root.config(bg=THEMES[current_theme]['bg'])

    try:
        root.iconbitmap("icon.ico")
    except:
        pass

    # ---- Styles ----
    style = ttk.Style()
    style.configure('.', font=('Segoe UI', 10))

    for theme_name, theme in THEMES.items():
        style.configure(f"{theme_name}.TFrame", background=theme['bg'])

        style.configure(
            f"{theme_name}.TButton",
            padding=8, relief="raised", borderwidth=2,
            background=theme['button_bg'], foreground='#ffffff',
            font=('Segoe UI', 10, 'bold'), width=15
        )
        style.map(
            f"{theme_name}.TButton",
            background=[('active', theme.get('button_hover', theme['button_bg'])),
                        ('!disabled', theme['button_bg'])],
            foreground=[('active', '#ffffff'), ('!disabled', '#ffffff')],
            relief=[('pressed', 'sunken'), ('!pressed', 'raised')]
        )

        style.configure(
            f"{theme_name}.Clear.TButton",
            padding=8, relief="raised", borderwidth=2,
            background=theme['clear_button_bg'], foreground='#ffffff',
            font=('Segoe UI', 10, 'bold'), width=15
        )
        style.map(
            f"{theme_name}.Clear.TButton",
            background=[('active', theme.get('clear_hover', theme['clear_button_bg'])),
                        ('!disabled', theme['clear_button_bg'])],
            foreground=[('active', '#ffffff'), ('!disabled', '#ffffff')],
            relief=[('pressed', 'sunken'), ('!pressed', 'raised')]
        )

        style.configure(
            f"{theme_name}.Active.TButton",
            padding=6, relief="sunken",
            background=theme['accent'], foreground='#ffffff',
            font=('Segoe UI', 9, 'bold')
        )
        style.map(
            f"{theme_name}.Active.TButton",
            background=[('active', theme['accent']), ('!disabled', theme['accent'])],
            foreground=[('active', '#ffffff'), ('!disabled', '#ffffff')]
        )

        style.configure(
            f"{theme_name}.TLabelframe",
            background=theme['bg'], foreground=theme['text']
        )
        style.configure(
            f"{theme_name}.TLabelframe.Label",
            background=theme['bg'], foreground=theme['accent'],
            font=('Segoe UI', 9, 'bold')
        )

        style.configure(
            f"{theme_name}.TNotebook",
            background=theme['bg'], tabmargins=[2, 5, 2, 0]
        )
        style.configure(
            f"{theme_name}.TNotebook.Tab",
            background=theme['bg'], foreground=theme['text'],
            padding=[12, 4], font=('Segoe UI', 9, 'bold')
        )
        style.map(
            f"{theme_name}.TNotebook.Tab",
            background=[('selected', theme['accent'])],
            foreground=[('selected', '#ffffff')]
        )

    # ---- Menu Bar ----
    menubar = tk.Menu(root, bg=THEMES[current_theme]['bg'], fg=THEMES[current_theme]['text'])

    file_menu = tk.Menu(menubar, tearoff=0,
                        bg=THEMES[current_theme]['bg'], fg=THEMES[current_theme]['text'])
    file_menu.add_command(label="Clear All", command=clear_text, accelerator="Ctrl+L")
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=root.quit)
    menubar.add_cascade(label="File", menu=file_menu)

    edit_menu = tk.Menu(menubar, tearoff=0,
                        bg=THEMES[current_theme]['bg'], fg=THEMES[current_theme]['text'])
    edit_menu.add_command(label="Copy All Output", command=copy_to_clipboard,
                          accelerator="Ctrl+Shift+C")
    edit_menu.add_separator()
    edit_menu.add_command(label="History", command=show_history, accelerator="Ctrl+H")
    menubar.add_cascade(label="Edit", menu=edit_menu)

    view_menu = tk.Menu(menubar, tearoff=0,
                        bg=THEMES[current_theme]['bg'], fg=THEMES[current_theme]['text'])
    for theme in THEMES:
        view_menu.add_command(label=theme, command=lambda t=theme: apply_theme(t))
    menubar.add_cascade(label="Themes", menu=view_menu)

    help_menu = tk.Menu(menubar, tearoff=0,
                        bg=THEMES[current_theme]['bg'], fg=THEMES[current_theme]['text'])
    help_menu.add_command(label="About", command=show_about)
    menubar.add_cascade(label="Help", menu=help_menu)

    root.config(menu=menubar)

    # ---- Main container ----
    main_container = ttk.Frame(root)
    main_container.pack(fill=tk.BOTH, expand=True)

    # ---- Sidebar ----
    sidebar_frame = ttk.Frame(main_container, width=165, style=f"{current_theme}.TFrame")
    sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
    sidebar_frame.pack_propagate(False)

    sidebar_labels = []

    def make_sidebar_label(parent, text, bold=False):
        font = ('Segoe UI', 10, 'bold') if bold else ('Segoe UI', 8)
        lbl = tk.Label(parent, text=text, font=font,
                       bg=THEMES[current_theme]['bg'],
                       fg=THEMES[current_theme]['label_fg'])
        lbl.pack(pady=(6, 2) if bold else (0, 0), anchor='w', padx=5)
        sidebar_labels.append(lbl)
        return lbl

    make_sidebar_label(sidebar_frame, "Themes", bold=True)

    theme_buttons = {}
    for theme in THEMES:
        btn = ttk.Button(
            sidebar_frame, text=theme,
            command=lambda t=theme: apply_theme(t),
            style=f"{current_theme}.TButton"
        )
        btn.pack(fill=tk.X, pady=2, padx=5)
        theme_buttons[theme] = btn

    ttk.Separator(sidebar_frame, orient='horizontal').pack(fill=tk.X, pady=8)
    make_sidebar_label(sidebar_frame, "Shortcuts", bold=True)
    for s in ["Enter: Auto Decode", "Ctrl+M: Manual", "Ctrl+P: Pipeline",
              "Esc / Ctrl+L: Clear", "Ctrl+Shift+C: Copy", "Ctrl+H: History"]:
        make_sidebar_label(sidebar_frame, s)

    ttk.Separator(sidebar_frame, orient='horizontal').pack(fill=tk.X, pady=8)
    make_sidebar_label(sidebar_frame, "Encodings", bold=True)
    for enc in ["Base64 / URL / 32 / 58 / 85", "Hex, Binary, Octal",
                "ASCII Decimal", "URL, HTML", "ROT13, ROT47", "Morse, Caesar"]:
        make_sidebar_label(sidebar_frame, enc)

    history_btn = ttk.Button(
        sidebar_frame, text="History (Ctrl+H)",
        command=show_history, style=f"{current_theme}.TButton"
    )
    history_btn.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0, 8))

    # ---- Main content area ----
    main_frame = ttk.Frame(main_container, padding="10", style=f"{current_theme}.TFrame")
    main_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    # ---- Input ----
    input_frame = ttk.LabelFrame(
        main_frame, text=" Input Text ",
        padding=10, style=f"{current_theme}.TLabelframe"
    )
    input_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 5))

    text_input = scrolledtext.ScrolledText(
        input_frame, height=6, font=("Consolas", 11),
        bg=THEMES[current_theme]['text_bg'],
        fg=THEMES[current_theme]['text'],
        insertbackground=THEMES[current_theme]['text'],
        selectbackground=THEMES[current_theme]['accent'],
        padx=10, pady=8, wrap=tk.WORD
    )
    text_input.pack(fill=tk.BOTH, expand=True)

    # ---- Mode Notebook ----
    notebook = ttk.Notebook(main_frame, style=f"{current_theme}.TNotebook")
    notebook.pack(fill=tk.X, pady=(0, 5))

    # ── TAB 1: AUTO ──────────────────────────────────────────────────────────
    tab_auto = ttk.Frame(notebook, style=f"{current_theme}.TFrame", padding=6)
    notebook.add(tab_auto, text="  Auto  ")

    button_frame = ttk.Frame(tab_auto, style=f"{current_theme}.TFrame")
    button_frame.pack(fill=tk.X)

    decode_btn = ttk.Button(
        button_frame, text="\u25b6  DECODE (Enter)",
        command=decode_input, style=f"{current_theme}.TButton"
    )
    decode_btn.pack(side=tk.LEFT, padx=4, ipadx=10, ipady=2)

    clear_btn = ttk.Button(
        button_frame, text="\u2715  CLEAR (Esc)",
        command=clear_text, style=f"{current_theme}.Clear.TButton"
    )
    clear_btn.pack(side=tk.LEFT, padx=4, ipadx=10, ipady=2)

    copy_btn = ttk.Button(
        button_frame, text="\u2398  Copy All",
        command=copy_to_clipboard, style=f"{current_theme}.TButton"
    )
    copy_btn.pack(side=tk.LEFT, padx=4, ipadx=10, ipady=2)

    tk.Label(
        tab_auto,
        text="Smart multi-layer auto-detection. Tries all decoders and chains layers automatically.",
        font=('Segoe UI', 8),
        bg=THEMES[current_theme]['bg'],
        fg=THEMES[current_theme]['label_fg']
    ).pack(anchor='w', pady=(4, 0))
    sidebar_labels.append(tab_auto.winfo_children()[-1])

    # ── TAB 2: MANUAL ────────────────────────────────────────────────────────
    tab_manual = ttk.Frame(notebook, style=f"{current_theme}.TFrame", padding=6)
    notebook.add(tab_manual, text="  Manual  ")

    manual_row = ttk.Frame(tab_manual, style=f"{current_theme}.TFrame")
    manual_row.pack(fill=tk.X, pady=4)

    manual_lbl = tk.Label(
        manual_row, text="Decode as:",
        font=('Segoe UI', 10),
        bg=THEMES[current_theme]['bg'],
        fg=THEMES[current_theme]['label_fg']
    )
    manual_lbl.pack(side=tk.LEFT, padx=(0, 8))
    sidebar_labels.append(manual_lbl)

    manual_decoder_var = tk.StringVar(value="Base64")
    manual_cb = ttk.Combobox(
        manual_row, textvariable=manual_decoder_var,
        values=list(MANUAL_DECODER_MAP.keys()),
        width=16, state='readonly', font=('Segoe UI', 10)
    )
    manual_cb.pack(side=tk.LEFT, padx=(0, 10))

    ttk.Button(
        manual_row, text="\u25b6  Run Manual Decode",
        command=manual_decode, style=f"{current_theme}.TButton"
    ).pack(side=tk.LEFT, ipadx=8, ipady=2)

    ttk.Button(
        manual_row, text="\u2715  Clear",
        command=clear_text, style=f"{current_theme}.Clear.TButton"
    ).pack(side=tk.LEFT, padx=6, ipadx=6, ipady=2)

    manual_hint = tk.Label(
        tab_manual,
        text="Force a specific decoder — great for CTF challenges where you know the encoding type.",
        font=('Segoe UI', 8),
        bg=THEMES[current_theme]['bg'],
        fg=THEMES[current_theme]['label_fg']
    )
    manual_hint.pack(anchor='w', pady=(2, 0))
    sidebar_labels.append(manual_hint)

    # ── TAB 3: PIPELINE ──────────────────────────────────────────────────────
    tab_pipeline = ttk.Frame(notebook, style=f"{current_theme}.TFrame", padding=6)
    notebook.add(tab_pipeline, text="  Pipeline  ")

    pipe_ctrl = ttk.Frame(tab_pipeline, style=f"{current_theme}.TFrame")
    pipe_ctrl.pack(fill=tk.X, pady=(0, 4))

    ttk.Button(
        pipe_ctrl, text="\u25b6  Run Pipeline",
        command=run_pipeline, style=f"{current_theme}.TButton"
    ).pack(side=tk.LEFT, padx=(0, 6), ipadx=8, ipady=2)

    ttk.Button(
        pipe_ctrl, text="+ Add Step",
        command=add_pipeline_step, style=f"{current_theme}.TButton"
    ).pack(side=tk.LEFT, padx=3, ipadx=6, ipady=2)

    ttk.Button(
        pipe_ctrl, text="\u2212 Remove",
        command=remove_pipeline_step, style=f"{current_theme}.Clear.TButton"
    ).pack(side=tk.LEFT, padx=3, ipadx=6, ipady=2)

    ttk.Button(
        pipe_ctrl, text="\u2715  Clear",
        command=clear_text, style=f"{current_theme}.Clear.TButton"
    ).pack(side=tk.LEFT, padx=6, ipadx=6, ipady=2)

    # Scrollable pipeline steps
    pipe_scroll_frame = tk.Frame(tab_pipeline, bg=THEMES[current_theme]['bg'])
    pipe_scroll_frame.pack(fill=tk.X, pady=2)

    pipeline_canvas = tk.Canvas(
        pipe_scroll_frame, height=44,
        bg=THEMES[current_theme]['bg'],
        highlightthickness=0
    )
    pipe_hscroll = ttk.Scrollbar(
        pipe_scroll_frame, orient='horizontal',
        command=pipeline_canvas.xview
    )
    pipeline_canvas.configure(xscrollcommand=pipe_hscroll.set)
    pipe_hscroll.pack(side=tk.BOTTOM, fill=tk.X)
    pipeline_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    pipeline_steps_inner = tk.Frame(pipeline_canvas, bg=THEMES[current_theme]['bg'])
    pipeline_canvas.create_window((0, 0), window=pipeline_steps_inner, anchor='nw')

    # Seed with 3 default steps
    for i in range(3):
        _build_pipeline_step(i)

    pipeline_canvas.update_idletasks()
    pipeline_canvas.configure(scrollregion=pipeline_canvas.bbox("all"))

    pipe_hint = tk.Label(
        tab_pipeline,
        text=(
            "Chain decoders in order, e.g.  Base64 \u2192 ROT13 \u2192 Hex.  "
            "Use + / \u2212 to add or remove steps. Pipeline stops and shows partial results on failure."
        ),
        font=('Segoe UI', 8),
        bg=THEMES[current_theme]['bg'],
        fg=THEMES[current_theme]['label_fg']
    )
    pipe_hint.pack(anchor='w', pady=(2, 0))
    sidebar_labels.append(pipe_hint)

    # ---- Output section ----
    result_frame = ttk.LabelFrame(
        main_frame, text=" Decoded Output ",
        padding=8, style=f"{current_theme}.TLabelframe"
    )
    result_frame.pack(fill=tk.BOTH, expand=True)

    # Per-layer copy button bar (populated dynamically)
    layer_buttons_frame = tk.Frame(result_frame, bg=THEMES[current_theme]['bg'])
    layer_buttons_frame.pack(fill=tk.X, pady=(0, 4))

    result_display = scrolledtext.ScrolledText(
        result_frame, height=13, font=("Consolas", 11),
        bg=THEMES[current_theme]['text_bg'],
        fg=THEMES[current_theme]['text'],
        state='disabled',
        insertbackground=THEMES[current_theme]['text'],
        selectbackground=THEMES[current_theme]['accent'],
        padx=10, pady=8, wrap=tk.WORD
    )
    result_display.pack(fill=tk.BOTH, expand=True)

    # ---- Status bar ----
    status_var = tk.StringVar(value="Ready")
    status_bar = tk.Label(
        root, textvariable=status_var,
        bd=1, relief=tk.SUNKEN, anchor=tk.W,
        bg=THEMES[current_theme]['accent'],
        fg="white", font=("Segoe UI", 9), padx=8
    )
    status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # ---- Keyboard bindings ----
    root.bind("<Return>", decode_input)
    root.bind("<Escape>", clear_text)
    root.bind("<Control-l>", lambda e: clear_text())
    root.bind("<Control-L>", lambda e: clear_text())
    root.bind("<Control-Shift-C>", lambda e: copy_to_clipboard())
    root.bind("<Control-h>", lambda e: show_history())
    root.bind("<Control-H>", lambda e: show_history())
    root.bind("<Control-m>", lambda e: notebook.select(1))
    root.bind("<Control-M>", lambda e: notebook.select(1))
    root.bind("<Control-p>", lambda e: notebook.select(2))
    root.bind("<Control-P>", lambda e: notebook.select(2))

    text_input.focus_set()
    apply_theme(current_theme)
    update_status("Ready — Auto / Manual / Pipeline modes available.", "info")
    load_history()


# ===========================================================
# ENTRY POINT
# ===========================================================

if __name__ == "__main__":
    create_gui()
    root.mainloop()
