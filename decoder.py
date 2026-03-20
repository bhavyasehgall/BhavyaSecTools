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
# ENCODERS
# ===========================================================

def encode_base64(s):
    return base64.b64encode(s.encode('utf-8')).decode()

def encode_base64_url(s):
    return base64.urlsafe_b64encode(s.encode('utf-8')).decode().rstrip('=')

def encode_base32(s):
    return base64.b32encode(s.encode('utf-8')).decode()

def encode_base58(s):
    data = s.encode('utf-8')
    num = int.from_bytes(data, 'big')
    if num == 0:
        return BASE58_CHARS[0]
    result = ''
    while num:
        num, rem = divmod(num, 58)
        result = BASE58_CHARS[rem] + result
    # Leading zero bytes
    for byte in data:
        if byte == 0:
            result = BASE58_CHARS[0] + result
        else:
            break
    return result

def encode_base85(s):
    return base64.a85encode(s.encode('utf-8'), adobe=False).decode()

def encode_hex(s):
    return s.encode('utf-8').hex()

def encode_hex_spaced(s):
    h = s.encode('utf-8').hex()
    return ' '.join(h[i:i+2] for i in range(0, len(h), 2))

def encode_binary(s):
    return ' '.join(format(ord(c), '08b') for c in s)

def encode_octal(s):
    return ' '.join(format(ord(c), 'o') for c in s)

def encode_ascii_decimal(s):
    return ' '.join(str(ord(c)) for c in s)

def encode_url(s):
    return urllib.parse.quote(s)

def encode_url_full(s):
    return urllib.parse.quote(s, safe='')

def encode_html_entities(s):
    return html.escape(s)

def encode_rot13(s):
    rot = str.maketrans(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm"
    )
    return s.translate(rot)

def encode_rot47(s):
    result = ''
    for c in s:
        o = ord(c)
        if 33 <= o <= 126:
            result += chr(33 + ((o - 33 + 47) % 94))
        else:
            result += c
    return result

TEXT_TO_MORSE = {v: k for k, v in MORSE.items()}

def encode_morse(s):
    words = s.upper().split()
    encoded_words = []
    for word in words:
        letters = []
        for ch in word:
            code = TEXT_TO_MORSE.get(ch)
            if code is None:
                return None  # unsupported character
            letters.append(code)
        encoded_words.append(' '.join(letters))
    return ' / '.join(encoded_words)

def encode_caesar(s, shift):
    result = ''
    for c in s:
        if c.isalpha():
            base = ord('A') if c.isupper() else ord('a')
            result += chr((ord(c) - base + shift) % 26 + base)
        else:
            result += c
    return result

def encode_md5(s):
    import hashlib
    return hashlib.md5(s.encode('utf-8')).hexdigest()

def encode_sha1(s):
    import hashlib
    return hashlib.sha1(s.encode('utf-8')).hexdigest()

def encode_sha256(s):
    import hashlib
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def encode_sha512(s):
    import hashlib
    return hashlib.sha512(s.encode('utf-8')).hexdigest()


ENCODERS = {
    # Format: display_name -> (function_or_None, has_param, param_label, param_default)
    "Base64":           (encode_base64,       False, None,    None),
    "Base64 URL-safe":  (encode_base64_url,   False, None,    None),
    "Base32":           (encode_base32,       False, None,    None),
    "Base58":           (encode_base58,       False, None,    None),
    "Base85":           (encode_base85,       False, None,    None),
    "Hex (compact)":    (encode_hex,          False, None,    None),
    "Hex (spaced)":     (encode_hex_spaced,   False, None,    None),
    "Binary":           (encode_binary,       False, None,    None),
    "Octal":            (encode_octal,        False, None,    None),
    "ASCII Decimal":    (encode_ascii_decimal,False, None,    None),
    "URL encode":       (encode_url,          False, None,    None),
    "URL encode (full)":(encode_url_full,     False, None,    None),
    "HTML entities":    (encode_html_entities,False, None,    None),
    "ROT13":            (encode_rot13,        False, None,    None),
    "ROT47":            (encode_rot47,        False, None,    None),
    "Morse":            (encode_morse,        False, None,    None),
    "Caesar cipher":    (encode_caesar,       True,  "Shift", "3"),
    "MD5 hash":         (encode_md5,          False, None,    None),
    "SHA-1 hash":       (encode_sha1,         False, None,    None),
    "SHA-256 hash":     (encode_sha256,       False, None,    None),
    "SHA-512 hash":     (encode_sha512,       False, None,    None),
}


# ===========================================================
# DECODER NAME LIST (for Manual Mode dropdown)
# ===========================================================

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

    for frame in [sidebar_frame]:
        try:
            frame.config(style=f"{theme_name}.TFrame")
        except:
            pass

    status_bar.config(bg=theme['accent'], fg='white')

    for lbl in sidebar_labels:
        try:
            lbl.config(bg=theme['bg'], fg=theme['label_fg'])
        except:
            pass

    for name, btn in theme_buttons.items():
        if name == theme_name:
            btn.config(style=f"{theme_name}.Active.TButton")
        else:
            btn.config(style=f"{theme_name}.TButton")

    _refresh_decoder_display()
    _refresh_encoder_display()
    update_status(f"Theme: {theme_name}", "info")


# ===========================================================
# SHARED STATE
# ===========================================================

_decoder_layers = []
_encoder_result = ""


# ===========================================================
# DECODER DISPLAY ENGINE
# ===========================================================

def _refresh_decoder_display():
    theme = THEMES[current_theme]

    dec_result_display.config(state='normal')
    dec_result_display.delete("1.0", tk.END)
    dec_result_display.tag_configure(
        "header", font=('Segoe UI', 10, 'bold'), foreground=theme['accent'])
    dec_result_display.tag_configure(
        "output", font=('Consolas', 10), foreground=theme['text'])
    dec_result_display.tag_configure(
        "error", font=('Segoe UI', 10), foreground='#cc0000')

    dec_input.config(
        bg=theme['text_bg'], fg=theme['text'],
        insertbackground=theme['text'], selectbackground=theme['accent'])
    dec_result_display.config(
        bg=theme['text_bg'], fg=theme['text'])

    for w in dec_layer_btn_frame.winfo_children():
        w.destroy()

    if not _decoder_layers:
        dec_result_display.config(state='disabled')
        return

    for i, (enc, res) in enumerate(_decoder_layers, 1):
        dec_result_display.insert(tk.END, f"Layer {i} ({enc}):\n", "header")
        dec_result_display.insert(tk.END, res + "\n\n", "output")

        btn = tk.Button(
            dec_layer_btn_frame,
            text=f"Copy Layer {i}",
            font=('Segoe UI', 8),
            bg=theme['button_bg'], fg='white',
            activebackground=theme.get('button_hover', theme['button_bg']),
            activeforeground='white',
            relief='flat', padx=6, pady=2, cursor='hand2',
            command=lambda r=res: _copy_text(r)
        )
        btn.pack(side=tk.LEFT, padx=3, pady=2)

    dec_result_display.config(state='disabled')


# ===========================================================
# ENCODER DISPLAY ENGINE
# ===========================================================

def _refresh_encoder_display():
    theme = THEMES[current_theme]

    enc_input.config(
        bg=theme['text_bg'], fg=theme['text'],
        insertbackground=theme['text'], selectbackground=theme['accent'])
    enc_result_display.config(
        bg=theme['text_bg'], fg=theme['text'],
        state='normal')

    enc_result_display.tag_configure(
        "label", font=('Segoe UI', 9, 'bold'), foreground=theme['accent'])
    enc_result_display.tag_configure(
        "value", font=('Consolas', 10), foreground=theme['text'])
    enc_result_display.tag_configure(
        "error", font=('Segoe UI', 9, 'italic'), foreground='#999999')
    enc_result_display.tag_configure(
        "separator", font=('Segoe UI', 6), foreground=theme['bg'])

    enc_result_display.config(state='disabled')


def _copy_text(text):
    root.clipboard_clear()
    root.clipboard_append(text)
    preview = text[:50] + ('...' if len(text) > 50 else '')
    update_status(f"Copied: {preview}", "success")


# ===========================================================
# DECODER ACTIONS
# ===========================================================

def run_auto_decode(event=None):
    global _decoder_layers
    if event:
        wclass = event.widget.winfo_class()
        if wclass in ('TCombobox', 'Entry'):
            return

    text = dec_input.get("1.0", tk.END).strip()
    if not text:
        update_status("No input provided.", "error")
        return

    update_status("Decoding...", "info")
    root.update()

    try:
        layers = auto_decode_multi_layer(text)
        _decoder_layers = layers
        _refresh_decoder_display()

        if layers:
            enc_type = " \u2192 ".join(e for e, _ in layers)
            update_status(f"Decoded {len(layers)} layer(s): {enc_type}", "success")
            add_to_history(text, layers[-1][1], enc_type)
        else:
            dec_result_display.config(state='normal')
            dec_result_display.insert(tk.END, "[!] Unable to decode automatically.\n\n", "error")
            dec_result_display.insert(
                tk.END,
                "Tried: " + ", ".join(n for n, _ in DECODERS) + "\n",
                "output"
            )
            dec_result_display.config(state='disabled')
            update_status("Could not decode input.", "error")
    except Exception as e:
        update_status(f"Error: {str(e)}", "error")
        messagebox.showerror("Error", str(e))


def run_manual_decode():
    global _decoder_layers
    text = dec_input.get("1.0", tk.END).strip()
    if not text:
        update_status("No input provided.", "error")
        return

    chosen = dec_manual_var.get()
    fn = MANUAL_DECODER_MAP.get(chosen)
    if not fn:
        update_status(f"Unknown decoder: {chosen}", "error")
        return

    try:
        result = fn(text)
        if result is None:
            _decoder_layers = []
            dec_result_display.config(state='normal')
            dec_result_display.delete("1.0", tk.END)
            dec_result_display.tag_configure("error", font=('Segoe UI', 10), foreground='#cc0000')
            dec_result_display.insert(
                tk.END, f"[!] {chosen} could not decode this input.\n", "error")
            dec_result_display.config(state='disabled')
            update_status(f"{chosen}: failed.", "error")
        else:
            _decoder_layers = [(chosen, result)]
            _refresh_decoder_display()
            update_status(f"Manual: {chosen} \u2192 success", "success")
            add_to_history(text, result, chosen)
    except Exception as e:
        update_status(f"Error: {str(e)}", "error")


def run_pipeline_decode():
    global _decoder_layers
    text = dec_input.get("1.0", tk.END).strip()
    if not text:
        update_status("No input provided.", "error")
        return

    steps = [v.get() for v in dec_pipeline_vars
             if v.get() and v.get() != "\u2014 select \u2014"]
    if not steps:
        update_status("Add at least one pipeline step.", "error")
        return

    current = text
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
            _decoder_layers = layers
            _refresh_decoder_display()
            dec_result_display.config(state='normal')
            dec_result_display.tag_configure("error", font=('Segoe UI', 10), foreground='#cc0000')
            dec_result_display.insert(
                tk.END, f"\n[!] Pipeline stopped: {step} failed at this stage.\n", "error")
            dec_result_display.config(state='disabled')
            update_status(f"Pipeline failed at: {step}", "error")
            return
        layers.append((step, result))
        current = result

    _decoder_layers = layers
    _refresh_decoder_display()
    enc_type = " \u2192 ".join(steps)
    update_status(f"Pipeline complete: {enc_type}", "success")
    if layers:
        add_to_history(text, layers[-1][1], enc_type)


def add_dec_pipeline_step():
    if len(dec_pipeline_vars) >= 8:
        update_status("Maximum 8 pipeline steps.", "error")
        return
    _build_dec_pipeline_step(len(dec_pipeline_vars))
    dec_pipe_canvas.update_idletasks()
    dec_pipe_canvas.configure(scrollregion=dec_pipe_canvas.bbox("all"))


def remove_dec_pipeline_step():
    if not dec_pipeline_vars:
        return
    dec_pipeline_vars.pop()
    frames = [w for w in dec_pipe_inner.winfo_children() if isinstance(w, tk.Frame)]
    if frames:
        frames[-1].destroy()
    dec_pipe_canvas.update_idletasks()
    dec_pipe_canvas.configure(scrollregion=dec_pipe_canvas.bbox("all"))


def _build_dec_pipeline_step(idx):
    theme = THEMES[current_theme]
    frame = tk.Frame(dec_pipe_inner, bg=theme['bg'])
    frame.pack(side=tk.LEFT, padx=2, pady=2)
    if idx > 0:
        tk.Label(frame, text="\u2192", font=('Segoe UI', 12, 'bold'),
                 bg=theme['bg'], fg=theme['accent']).pack(side=tk.LEFT, padx=4)
    var = tk.StringVar(value="\u2014 select \u2014")
    dec_pipeline_vars.append(var)
    ttk.Combobox(frame, textvariable=var,
                 values=list(MANUAL_DECODER_MAP.keys()),
                 width=13, state='readonly', font=('Segoe UI', 9)).pack(side=tk.LEFT)


def clear_decoder(event=None):
    global _decoder_layers
    _decoder_layers = []
    dec_input.delete("1.0", tk.END)
    dec_result_display.config(state='normal')
    dec_result_display.delete("1.0", tk.END)
    dec_result_display.config(state='disabled')
    for w in dec_layer_btn_frame.winfo_children():
        w.destroy()
    update_status("Decoder cleared.", "info")
    dec_input.focus_set()


def copy_decoder_all(event=None):
    content = dec_result_display.get("1.0", tk.END).strip()
    if content:
        root.clipboard_clear()
        root.clipboard_append(content)
        update_status("Copied all output.", "success")
    else:
        update_status("Nothing to copy.", "error")


# ===========================================================
# ENCODER ACTIONS
# ===========================================================

def run_encode():
    global _encoder_result
    text = enc_input.get("1.0", tk.END).strip()
    if not text:
        update_status("No input provided.", "error")
        return

    chosen = enc_format_var.get()
    entry = ENCODERS.get(chosen)
    if not entry:
        update_status(f"Unknown encoder: {chosen}", "error")
        return

    fn, has_param, param_label, param_default = entry

    try:
        if has_param:
            raw = enc_param_var.get().strip()
            try:
                param = int(raw)
            except ValueError:
                update_status(f"Invalid parameter '{raw}' — must be a number.", "error")
                return
            result = fn(text, param)
        else:
            result = fn(text)

        if result is None:
            update_status(f"{chosen}: could not encode this input.", "error")
            enc_result_display.config(state='normal')
            enc_result_display.delete("1.0", tk.END)
            enc_result_display.tag_configure("error", font=('Segoe UI', 10), foreground='#cc0000')
            enc_result_display.insert(tk.END,
                f"[!] {chosen} could not encode this input.\n"
                "(Some encoders only support ASCII/printable characters.)\n",
                "error")
            enc_result_display.config(state='disabled')
            return

        _encoder_result = result
        enc_result_display.config(state='normal')
        enc_result_display.delete("1.0", tk.END)
        enc_result_display.tag_configure(
            "label", font=('Segoe UI', 9, 'bold'),
            foreground=THEMES[current_theme]['accent'])
        enc_result_display.tag_configure(
            "value", font=('Consolas', 11),
            foreground=THEMES[current_theme]['text'])
        enc_result_display.insert(tk.END, f"{chosen}:\n", "label")
        enc_result_display.insert(tk.END, result + "\n", "value")
        enc_result_display.config(state='disabled')
        update_status(f"Encoded as {chosen} ({len(result)} chars)", "success")

    except Exception as e:
        update_status(f"Error: {str(e)}", "error")
        messagebox.showerror("Encode Error", str(e))


def run_encode_all():
    """Encode input using every encoder and display all results."""
    text = enc_input.get("1.0", tk.END).strip()
    if not text:
        update_status("No input provided.", "error")
        return

    update_status("Encoding with all methods...", "info")
    root.update()

    theme = THEMES[current_theme]
    enc_result_display.config(state='normal')
    enc_result_display.delete("1.0", tk.END)
    enc_result_display.tag_configure(
        "label", font=('Segoe UI', 9, 'bold'), foreground=theme['accent'])
    enc_result_display.tag_configure(
        "value", font=('Consolas', 10), foreground=theme['text'])
    enc_result_display.tag_configure(
        "error", font=('Segoe UI', 9, 'italic'), foreground='#999999')

    count = 0
    for name, (fn, has_param, param_label, param_default) in ENCODERS.items():
        try:
            if has_param:
                result = fn(text, int(param_default))
            else:
                result = fn(text)

            if result is None:
                enc_result_display.insert(tk.END, f"{name}:\n", "label")
                enc_result_display.insert(tk.END, "(not supported for this input)\n\n", "error")
            else:
                enc_result_display.insert(tk.END, f"{name}:\n", "label")
                enc_result_display.insert(tk.END, result + "\n\n", "value")
                count += 1
        except Exception:
            enc_result_display.insert(tk.END, f"{name}:\n", "label")
            enc_result_display.insert(tk.END, "(error)\n\n", "error")

    enc_result_display.config(state='disabled')
    update_status(f"Encoded with {count}/{len(ENCODERS)} methods.", "success")


def on_encoder_select(event=None):
    """Show/hide the parameter field based on selected encoder."""
    chosen = enc_format_var.get()
    entry = ENCODERS.get(chosen)
    if not entry:
        return
    fn, has_param, param_label, param_default = entry
    if has_param:
        enc_param_label.config(text=f"{param_label}:")
        enc_param_var.set(param_default or "")
        enc_param_frame.pack(side=tk.LEFT, padx=(8, 0))
    else:
        enc_param_frame.pack_forget()


def clear_encoder():
    global _encoder_result
    _encoder_result = ""
    enc_input.delete("1.0", tk.END)
    enc_result_display.config(state='normal')
    enc_result_display.delete("1.0", tk.END)
    enc_result_display.config(state='disabled')
    update_status("Encoder cleared.", "info")
    enc_input.focus_set()


def copy_encoder_result():
    content = enc_result_display.get("1.0", tk.END).strip()
    if content:
        root.clipboard_clear()
        root.clipboard_append(content)
        update_status("Copied encoder output.", "success")
    else:
        update_status("Nothing to copy.", "error")



# ===========================================================
# ENCODER PIPELINE ACTIONS
# ===========================================================

_enc_pipeline_layers = []


def run_pipeline_encode():
    """Run input through the encoder pipeline: each step encodes the output of the previous."""
    global _encoder_result, _enc_pipeline_layers
    text = enc_input.get("1.0", tk.END).strip()
    if not text:
        update_status("No input provided.", "error")
        return

    steps = []
    for item in enc_pipeline_vars:
        var, param_var = item
        name = var.get()
        if name and name != "— select —":
            steps.append((name, param_var.get().strip()))

    if not steps:
        update_status("Add at least one pipeline step.", "error")
        return

    current = text
    layers = []

    for step_name, param_raw in steps:
        entry = ENCODERS.get(step_name)
        if not entry:
            update_status(f"Unknown encoder: {step_name}", "error")
            return
        fn, has_param, param_label, param_default = entry
        try:
            if has_param:
                try:
                    param = int(param_raw) if param_raw else int(param_default)
                except ValueError:
                    update_status(f"Invalid parameter for {step_name}: '{param_raw}'", "error")
                    return
                result = fn(current, param)
            else:
                result = fn(current)
        except Exception:
            result = None

        if result is None:
            _enc_pipeline_layers = layers
            _render_enc_pipeline_results(partial=True, failed_at=step_name)
            update_status(f"Pipeline stopped: {step_name} failed.", "error")
            return

        layers.append((step_name, result))
        current = result

    _enc_pipeline_layers = layers
    _encoder_result = layers[-1][1] if layers else ""
    _render_enc_pipeline_results()
    chain = " → ".join(s for s, _ in steps)
    update_status(f"Encoded pipeline: {chain} ({len(_encoder_result)} chars)", "success")


def _render_enc_pipeline_results(partial=False, failed_at=None):
    theme = THEMES[current_theme]
    enc_result_display.config(state='normal')
    enc_result_display.delete("1.0", tk.END)
    enc_result_display.tag_configure("header", font=('Segoe UI', 10, 'bold'),
                                     foreground=theme['accent'])
    enc_result_display.tag_configure("value", font=('Consolas', 10),
                                     foreground=theme['text'])
    enc_result_display.tag_configure("error", font=('Segoe UI', 10), foreground='#cc0000')

    for w in enc_layer_btn_frame.winfo_children():
        w.destroy()

    for i, (name, val) in enumerate(_enc_pipeline_layers, 1):
        header_line = "Step " + str(i) + " (" + name + "):\n"
        enc_result_display.insert(tk.END, header_line, "header")
        enc_result_display.insert(tk.END, val + "\n\n", "value")
        btn = tk.Button(
            enc_layer_btn_frame,
            text="Copy Step " + str(i),
            font=('Segoe UI', 8),
            bg=theme['button_bg'], fg='white',
            activebackground=theme.get('button_hover', theme['button_bg']),
            activeforeground='white',
            relief='flat', padx=6, pady=2, cursor='hand2',
            command=lambda v=val: _copy_text(v)
        )
        btn.pack(side=tk.LEFT, padx=3, pady=2)

    if partial and failed_at:
        msg = "[!] Pipeline stopped: '" + failed_at + "' could not encode at this stage.\n"
        enc_result_display.insert(tk.END, msg, "error")

    enc_result_display.config(state='disabled')


def add_enc_pipeline_step():
    if len(enc_pipeline_vars) >= 8:
        update_status("Maximum 8 pipeline steps.", "error")
        return
    _build_enc_pipeline_step(len(enc_pipeline_vars))
    enc_pipe_canvas.update_idletasks()
    enc_pipe_canvas.configure(scrollregion=enc_pipe_canvas.bbox("all"))


def remove_enc_pipeline_step():
    if not enc_pipeline_vars:
        return
    enc_pipeline_vars.pop()
    frames = [w for w in enc_pipe_inner.winfo_children() if isinstance(w, tk.Frame)]
    if frames:
        frames[-1].destroy()
    enc_pipe_canvas.update_idletasks()
    enc_pipe_canvas.configure(scrollregion=enc_pipe_canvas.bbox("all"))


def _build_enc_pipeline_step(idx):
    theme = THEMES[current_theme]
    frame = tk.Frame(enc_pipe_inner, bg=theme['bg'])
    frame.pack(side=tk.LEFT, padx=2, pady=2)

    if idx > 0:
        tk.Label(frame, text="→", font=('Segoe UI', 12, 'bold'),
                 bg=theme['bg'], fg=theme['accent']).pack(side=tk.LEFT, padx=4)

    var = tk.StringVar(value="— select —")
    param_var = tk.StringVar(value="3")

    cb = ttk.Combobox(frame, textvariable=var,
                      values=list(ENCODERS.keys()),
                      width=14, state='readonly', font=('Segoe UI', 9))
    cb.pack(side=tk.LEFT)

    param_frame = tk.Frame(frame, bg=theme['bg'])
    tk.Label(param_frame, text="n=", font=('Segoe UI', 8),
             bg=theme['bg'], fg=theme['label_fg']).pack(side=tk.LEFT)
    tk.Entry(param_frame, textvariable=param_var,
             width=3, font=('Segoe UI', 9)).pack(side=tk.LEFT)

    def on_select(event=None):
        chosen = var.get()
        entry = ENCODERS.get(chosen)
        if entry and entry[1]:
            param_var.set(entry[3] or "3")
            param_frame.pack(side=tk.LEFT, padx=(3, 0))
        else:
            param_frame.pack_forget()

    cb.bind("<<ComboboxSelected>>", on_select)
    enc_pipeline_vars.append((var, param_var))


# ===========================================================
# SHARED ACTIONS
# ===========================================================

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


def show_history():
    hw = tk.Toplevel(root)
    hw.title("Decoding History")
    hw.geometry("820x600")
    hw.config(bg=THEMES[current_theme]['bg'])

    container = ttk.Frame(hw, style=f"{current_theme}.TFrame")
    container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    tk.Label(container, text="Decoding History",
             font=('Segoe UI', 14, 'bold'),
             bg=THEMES[current_theme]['bg'],
             fg=THEMES[current_theme]['label_fg']).pack(pady=(0, 10))

    lf = ttk.Frame(container, style=f"{current_theme}.TFrame")
    lf.pack(fill=tk.BOTH, expand=True)

    sb = ttk.Scrollbar(lf)
    sb.pack(side=tk.RIGHT, fill=tk.Y)

    hl = tk.Listbox(lf, yscrollcommand=sb.set, font=('Segoe UI', 10),
                    bg=THEMES[current_theme]['text_bg'],
                    fg=THEMES[current_theme]['text'],
                    selectbackground=THEMES[current_theme]['accent'],
                    selectforeground='white', borderwidth=0, highlightthickness=0)
    hl.pack(fill=tk.BOTH, expand=True)
    sb.config(command=hl.yview)

    if not history:
        hl.insert(tk.END, "  (No history yet)")
    else:
        for e in history:
            hl.insert(tk.END, f"[{e['timestamp']}]  {e['type']}:  {e['input'][:60]}...")

    def view_sel():
        sel = hl.curselection()
        if not sel or sel[0] >= len(history):
            return
        e = history[sel[0]]
        vw = tk.Toplevel(hw)
        vw.title("History Entry")
        vw.geometry("700x520")
        vw.config(bg=THEMES[current_theme]['bg'])
        vc = ttk.Frame(vw, style=f"{current_theme}.TFrame")
        vc.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for txt in [f"Timestamp: {e['timestamp']}", f"Encoding: {e['type']}"]:
            tk.Label(vc, text=txt, font=('Segoe UI', 9),
                     bg=THEMES[current_theme]['bg'],
                     fg=THEMES[current_theme]['label_fg']).pack(anchor='w')
        tk.Label(vc, text="Input:", font=('Segoe UI', 10, 'bold'),
                 bg=THEMES[current_theme]['bg'],
                 fg=THEMES[current_theme]['label_fg']).pack(anchor='w', pady=(8, 0))
        ib = scrolledtext.ScrolledText(vc, height=7, font=("Consolas", 10),
                                       bg=THEMES[current_theme]['text_bg'],
                                       fg=THEMES[current_theme]['text'], wrap=tk.WORD)
        ib.insert('1.0', e['input'])
        ib.config(state='disabled')
        ib.pack(fill=tk.X, pady=(0, 8))
        tk.Label(vc, text="Output:", font=('Segoe UI', 10, 'bold'),
                 bg=THEMES[current_theme]['bg'],
                 fg=THEMES[current_theme]['label_fg']).pack(anchor='w')
        ob = scrolledtext.ScrolledText(vc, height=10, font=("Consolas", 10),
                                       bg=THEMES[current_theme]['text_bg'],
                                       fg=THEMES[current_theme]['text'], wrap=tk.WORD)
        ob.insert('1.0', e['result'])
        ob.config(state='disabled')
        ob.pack(fill=tk.BOTH, expand=True)
        bf = ttk.Frame(vc, style=f"{current_theme}.TFrame")
        bf.pack(fill=tk.X, pady=(10, 0))
        def load():
            dec_input.delete('1.0', tk.END)
            dec_input.insert('1.0', e['input'])
            vw.destroy()
            hw.destroy()
            main_notebook.select(0)
            update_status(f"Loaded from {e['timestamp']}", "success")
        ttk.Button(bf, text="Load to Decoder", command=load,
                   style=f"{current_theme}.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(bf, text="Close", command=vw.destroy,
                   style=f"{current_theme}.TButton").pack(side=tk.RIGHT, padx=5)

    def clear_hist():
        global history
        if messagebox.askyesno("Clear History", "Clear all history? Cannot be undone."):
            history = []
            save_history()
            hl.delete(0, tk.END)
            hl.insert(tk.END, "  (History cleared)")
            update_status("History cleared.", "info")

    bf = ttk.Frame(container, style=f"{current_theme}.TFrame")
    bf.pack(fill=tk.X, pady=(10, 0))
    ttk.Button(bf, text="View Selected", command=view_sel,
               style=f"{current_theme}.TButton").pack(side=tk.LEFT, padx=5)
    ttk.Button(bf, text="Clear History", command=clear_hist,
               style=f"{current_theme}.Clear.TButton").pack(side=tk.LEFT, padx=5)
    ttk.Button(bf, text="Close", command=hw.destroy,
               style=f"{current_theme}.TButton").pack(side=tk.RIGHT, padx=5)
    hl.bind('<Double-1>', lambda ev: view_sel())


def show_about():
    messagebox.showinfo("About", (
        "PRO AUTO DECODER / ENCODER\n"
        "v4.0.0\n\n"
        "Two-tab interface:\n"
        "  DECODER — Auto, Manual, Pipeline modes\n"
        "  ENCODER — 21 encoding formats + Encode All\n\n"
        "Decoder supports:\n"
        "  Base64/32/58/85/URL, Hex, Binary, Octal,\n"
        "  ASCII Decimal, URL, HTML, ROT13/47, Caesar, Morse\n\n"
        "Encoder adds:\n"
        "  MD5, SHA-1, SHA-256, SHA-512 hashes\n\n"
        "Author: Bhavya Sehgal."
    ))


# ===========================================================
# GUI SETUP
# ===========================================================

def create_gui():
    global root, status_var, status_bar, sidebar_frame, sidebar_labels
    global theme_buttons, menubar, main_notebook
    global dec_input, dec_result_display, dec_layer_btn_frame
    global dec_manual_var, dec_pipeline_vars, dec_pipe_canvas, dec_pipe_inner
    global enc_input, enc_result_display, enc_format_var, enc_param_var
    global enc_param_frame, enc_param_label
    global enc_pipeline_vars, enc_pipe_canvas, enc_pipe_inner
    global enc_layer_btn_frame, enc_mode_nb

    dec_pipeline_vars = []
    enc_pipeline_vars = []

    root = tk.Tk()
    root.title("PRO AUTO DECODER / ENCODER  v4")
    root.geometry("1080x780")
    root.minsize(900, 660)
    root.config(bg=THEMES[current_theme]['bg'])

    try:
        root.iconbitmap("icon.ico")
    except:
        pass

    # ── Styles ────────────────────────────────────────────────────────────────
    style = ttk.Style()
    style.configure('.', font=('Segoe UI', 10))

    for theme_name, theme in THEMES.items():
        style.configure(f"{theme_name}.TFrame", background=theme['bg'])
        style.configure(
            f"{theme_name}.TButton",
            padding=8, relief="raised", borderwidth=2,
            background=theme['button_bg'], foreground='#ffffff',
            font=('Segoe UI', 10, 'bold'), width=14
        )
        style.map(f"{theme_name}.TButton",
                  background=[('active', theme.get('button_hover', theme['button_bg'])),
                               ('!disabled', theme['button_bg'])],
                  foreground=[('active', '#ffffff'), ('!disabled', '#ffffff')],
                  relief=[('pressed', 'sunken'), ('!pressed', 'raised')])
        style.configure(
            f"{theme_name}.Clear.TButton",
            padding=8, relief="raised", borderwidth=2,
            background=theme['clear_button_bg'], foreground='#ffffff',
            font=('Segoe UI', 10, 'bold'), width=14
        )
        style.map(f"{theme_name}.Clear.TButton",
                  background=[('active', theme.get('clear_hover', theme['clear_button_bg'])),
                               ('!disabled', theme['clear_button_bg'])],
                  foreground=[('active', '#ffffff'), ('!disabled', '#ffffff')],
                  relief=[('pressed', 'sunken'), ('!pressed', 'raised')])
        style.configure(
            f"{theme_name}.Active.TButton",
            padding=6, relief="sunken",
            background=theme['accent'], foreground='#ffffff',
            font=('Segoe UI', 9, 'bold')
        )
        style.map(f"{theme_name}.Active.TButton",
                  background=[('active', theme['accent']), ('!disabled', theme['accent'])],
                  foreground=[('active', '#ffffff'), ('!disabled', '#ffffff')])
        style.configure(
            f"{theme_name}.TLabelframe",
            background=theme['bg'], foreground=theme['text'])
        style.configure(
            f"{theme_name}.TLabelframe.Label",
            background=theme['bg'], foreground=theme['accent'],
            font=('Segoe UI', 9, 'bold'))
        style.configure(
            f"{theme_name}.TNotebook",
            background=theme['bg'], tabmargins=[2, 5, 2, 0])
        style.configure(
            f"{theme_name}.TNotebook.Tab",
            background=theme['bg'], foreground=theme['text'],
            padding=[16, 5], font=('Segoe UI', 10, 'bold'))
        style.map(
            f"{theme_name}.TNotebook.Tab",
            background=[('selected', theme['accent'])],
            foreground=[('selected', '#ffffff')])

    # ── Menu Bar ──────────────────────────────────────────────────────────────
    menubar = tk.Menu(root, bg=THEMES[current_theme]['bg'], fg=THEMES[current_theme]['text'])

    file_menu = tk.Menu(menubar, tearoff=0,
                        bg=THEMES[current_theme]['bg'], fg=THEMES[current_theme]['text'])
    file_menu.add_command(label="Clear Decoder", command=clear_decoder, accelerator="Ctrl+L")
    file_menu.add_command(label="Clear Encoder", command=clear_encoder)
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=root.quit)
    menubar.add_cascade(label="File", menu=file_menu)

    edit_menu = tk.Menu(menubar, tearoff=0,
                        bg=THEMES[current_theme]['bg'], fg=THEMES[current_theme]['text'])
    edit_menu.add_command(label="Copy Decoder Output",
                          command=copy_decoder_all, accelerator="Ctrl+Shift+C")
    edit_menu.add_command(label="Copy Encoder Output", command=copy_encoder_result)
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

    # ── Layout: sidebar + main ────────────────────────────────────────────────
    outer = ttk.Frame(root)
    outer.pack(fill=tk.BOTH, expand=True)

    # Sidebar
    sidebar_frame = ttk.Frame(outer, width=162, style=f"{current_theme}.TFrame")
    sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
    sidebar_frame.pack_propagate(False)

    sidebar_labels = []

    def slbl(text, bold=False):
        lbl = tk.Label(sidebar_frame, text=text,
                       font=('Segoe UI', 10, 'bold') if bold else ('Segoe UI', 8),
                       bg=THEMES[current_theme]['bg'], fg=THEMES[current_theme]['label_fg'])
        lbl.pack(pady=(6, 2) if bold else (0, 0), anchor='w', padx=5)
        sidebar_labels.append(lbl)

    slbl("Themes", bold=True)
    theme_buttons = {}
    for t in THEMES:
        btn = ttk.Button(sidebar_frame, text=t, command=lambda x=t: apply_theme(x),
                         style=f"{current_theme}.TButton")
        btn.pack(fill=tk.X, pady=2, padx=5)
        theme_buttons[t] = btn

    ttk.Separator(sidebar_frame, orient='horizontal').pack(fill=tk.X, pady=8)
    slbl("Decoder shortcuts", bold=True)
    for s in ["Enter: Auto Decode", "Ctrl+M: Manual tab",
              "Ctrl+P: Pipeline tab", "Ctrl+L: Clear", "Ctrl+H: History"]:
        slbl(s)

    ttk.Separator(sidebar_frame, orient='horizontal').pack(fill=tk.X, pady=8)
    slbl("Encoder shortcuts", bold=True)
    for s in ["Ctrl+E: Encode", "Ctrl+A: Encode All", "Ctrl+Shift+E: Clear"]:
        slbl(s)

    ttk.Separator(sidebar_frame, orient='horizontal').pack(fill=tk.X, pady=8)
    slbl("Formats", bold=True)
    for s in ["Base64/32/58/85/URL", "Hex · Binary · Octal",
              "ASCII · URL · HTML", "ROT13/47 · Caesar", "Morse · MD5 · SHA"]:
        slbl(s)

    history_btn = ttk.Button(sidebar_frame, text="History (Ctrl+H)",
                              command=show_history, style=f"{current_theme}.TButton")
    history_btn.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0, 8))

    # ── Main notebook: DECODER | ENCODER ─────────────────────────────────────
    main_notebook = ttk.Notebook(outer, style=f"{current_theme}.TNotebook")
    main_notebook.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

    # ═══════════════════════════════════════════════════════════════
    # TAB 1: DECODER
    # ═══════════════════════════════════════════════════════════════
    decoder_tab = ttk.Frame(main_notebook, style=f"{current_theme}.TFrame", padding=8)
    main_notebook.add(decoder_tab, text="  \U0001f513  DECODER  ")

    # Decoder input
    dec_input_frame = ttk.LabelFrame(
        decoder_tab, text=" Input (encoded text) ",
        padding=8, style=f"{current_theme}.TLabelframe")
    dec_input_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 5))

    dec_input = scrolledtext.ScrolledText(
        dec_input_frame, height=5, font=("Consolas", 11),
        bg=THEMES[current_theme]['text_bg'],
        fg=THEMES[current_theme]['text'],
        insertbackground=THEMES[current_theme]['text'],
        selectbackground=THEMES[current_theme]['accent'],
        padx=8, pady=6, wrap=tk.WORD)
    dec_input.pack(fill=tk.BOTH, expand=True)

    # Decoder mode sub-notebook
    dec_mode_nb = ttk.Notebook(decoder_tab, style=f"{current_theme}.TNotebook")
    dec_mode_nb.pack(fill=tk.X, pady=(0, 5))

    # ── Auto tab ─────────────────────────────────────────────────────────────
    tab_auto = ttk.Frame(dec_mode_nb, style=f"{current_theme}.TFrame", padding=5)
    dec_mode_nb.add(tab_auto, text="  Auto  ")

    auto_row = ttk.Frame(tab_auto, style=f"{current_theme}.TFrame")
    auto_row.pack(fill=tk.X)

    ttk.Button(auto_row, text="\u25b6  DECODE (Enter)",
               command=run_auto_decode, style=f"{current_theme}.TButton"
               ).pack(side=tk.LEFT, padx=4, ipadx=8, ipady=2)
    ttk.Button(auto_row, text="\u2715  Clear",
               command=clear_decoder, style=f"{current_theme}.Clear.TButton"
               ).pack(side=tk.LEFT, padx=4, ipadx=8, ipady=2)
    ttk.Button(auto_row, text="\u2398  Copy All",
               command=copy_decoder_all, style=f"{current_theme}.TButton"
               ).pack(side=tk.LEFT, padx=4, ipadx=8, ipady=2)

    auto_hint = tk.Label(tab_auto,
                         text="Smart multi-layer auto-detection across all supported encodings.",
                         font=('Segoe UI', 8),
                         bg=THEMES[current_theme]['bg'],
                         fg=THEMES[current_theme]['label_fg'])
    auto_hint.pack(anchor='w', pady=(4, 0))
    sidebar_labels.append(auto_hint)

    # ── Manual tab ────────────────────────────────────────────────────────────
    tab_manual = ttk.Frame(dec_mode_nb, style=f"{current_theme}.TFrame", padding=5)
    dec_mode_nb.add(tab_manual, text="  Manual  ")

    man_row = ttk.Frame(tab_manual, style=f"{current_theme}.TFrame")
    man_row.pack(fill=tk.X, pady=2)

    man_lbl = tk.Label(man_row, text="Decode as:",
                       font=('Segoe UI', 10),
                       bg=THEMES[current_theme]['bg'],
                       fg=THEMES[current_theme]['label_fg'])
    man_lbl.pack(side=tk.LEFT, padx=(0, 8))
    sidebar_labels.append(man_lbl)

    dec_manual_var = tk.StringVar(value="Base64")
    ttk.Combobox(man_row, textvariable=dec_manual_var,
                 values=list(MANUAL_DECODER_MAP.keys()),
                 width=15, state='readonly',
                 font=('Segoe UI', 10)).pack(side=tk.LEFT, padx=(0, 10))

    ttk.Button(man_row, text="\u25b6  Run",
               command=run_manual_decode, style=f"{current_theme}.TButton"
               ).pack(side=tk.LEFT, ipadx=8, ipady=2)
    ttk.Button(man_row, text="\u2715  Clear",
               command=clear_decoder, style=f"{current_theme}.Clear.TButton"
               ).pack(side=tk.LEFT, padx=6, ipadx=6, ipady=2)

    man_hint = tk.Label(tab_manual,
                        text="Force a specific decoder — useful for CTF challenges.",
                        font=('Segoe UI', 8),
                        bg=THEMES[current_theme]['bg'],
                        fg=THEMES[current_theme]['label_fg'])
    man_hint.pack(anchor='w', pady=(4, 0))
    sidebar_labels.append(man_hint)

    # ── Pipeline tab ──────────────────────────────────────────────────────────
    tab_pipe = ttk.Frame(dec_mode_nb, style=f"{current_theme}.TFrame", padding=5)
    dec_mode_nb.add(tab_pipe, text="  Pipeline  ")

    pipe_ctrl_row = ttk.Frame(tab_pipe, style=f"{current_theme}.TFrame")
    pipe_ctrl_row.pack(fill=tk.X, pady=(0, 4))

    ttk.Button(pipe_ctrl_row, text="\u25b6  Run Pipeline",
               command=run_pipeline_decode, style=f"{current_theme}.TButton"
               ).pack(side=tk.LEFT, padx=(0, 5), ipadx=8, ipady=2)
    ttk.Button(pipe_ctrl_row, text="+ Step",
               command=add_dec_pipeline_step, style=f"{current_theme}.TButton"
               ).pack(side=tk.LEFT, padx=3, ipadx=5, ipady=2)
    ttk.Button(pipe_ctrl_row, text="\u2212 Remove",
               command=remove_dec_pipeline_step, style=f"{current_theme}.Clear.TButton"
               ).pack(side=tk.LEFT, padx=3, ipadx=5, ipady=2)
    ttk.Button(pipe_ctrl_row, text="\u2715  Clear",
               command=clear_decoder, style=f"{current_theme}.Clear.TButton"
               ).pack(side=tk.LEFT, padx=5, ipadx=5, ipady=2)

    pipe_scroll_wrap = tk.Frame(tab_pipe, bg=THEMES[current_theme]['bg'])
    pipe_scroll_wrap.pack(fill=tk.X, pady=2)

    dec_pipe_canvas = tk.Canvas(pipe_scroll_wrap, height=42,
                                bg=THEMES[current_theme]['bg'],
                                highlightthickness=0)
    pipe_hsc = ttk.Scrollbar(pipe_scroll_wrap, orient='horizontal',
                              command=dec_pipe_canvas.xview)
    dec_pipe_canvas.configure(xscrollcommand=pipe_hsc.set)
    pipe_hsc.pack(side=tk.BOTTOM, fill=tk.X)
    dec_pipe_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    dec_pipe_inner = tk.Frame(dec_pipe_canvas, bg=THEMES[current_theme]['bg'])
    dec_pipe_canvas.create_window((0, 0), window=dec_pipe_inner, anchor='nw')

    for i in range(3):
        _build_dec_pipeline_step(i)

    dec_pipe_canvas.update_idletasks()
    dec_pipe_canvas.configure(scrollregion=dec_pipe_canvas.bbox("all"))

    pipe_hint = tk.Label(tab_pipe,
                         text="Chain decoders: Base64 \u2192 ROT13 \u2192 Hex. Stops and shows partial results on failure.",
                         font=('Segoe UI', 8),
                         bg=THEMES[current_theme]['bg'],
                         fg=THEMES[current_theme]['label_fg'])
    pipe_hint.pack(anchor='w', pady=(2, 0))
    sidebar_labels.append(pipe_hint)

    # Decoder output
    dec_out_frame = ttk.LabelFrame(
        decoder_tab, text=" Decoded Output ",
        padding=8, style=f"{current_theme}.TLabelframe")
    dec_out_frame.pack(fill=tk.BOTH, expand=True)

    dec_layer_btn_frame = tk.Frame(dec_out_frame, bg=THEMES[current_theme]['bg'])
    dec_layer_btn_frame.pack(fill=tk.X, pady=(0, 4))

    dec_result_display = scrolledtext.ScrolledText(
        dec_out_frame, height=12, font=("Consolas", 11),
        bg=THEMES[current_theme]['text_bg'],
        fg=THEMES[current_theme]['text'],
        state='disabled',
        insertbackground=THEMES[current_theme]['text'],
        selectbackground=THEMES[current_theme]['accent'],
        padx=8, pady=6, wrap=tk.WORD)
    dec_result_display.pack(fill=tk.BOTH, expand=True)

    # ═══════════════════════════════════════════════════════════════
    # TAB 2: ENCODER
    # ═══════════════════════════════════════════════════════════════
    encoder_tab = ttk.Frame(main_notebook, style=f"{current_theme}.TFrame", padding=8)
    main_notebook.add(encoder_tab, text="  \U0001f510  ENCODER  ")

    # Encoder input
    enc_input_frame = ttk.LabelFrame(
        encoder_tab, text=" Input (plain text to encode) ",
        padding=8, style=f"{current_theme}.TLabelframe")
    enc_input_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 5))

    enc_input = scrolledtext.ScrolledText(
        enc_input_frame, height=5, font=("Consolas", 11),
        bg=THEMES[current_theme]['text_bg'],
        fg=THEMES[current_theme]['text'],
        insertbackground=THEMES[current_theme]['text'],
        selectbackground=THEMES[current_theme]['accent'],
        padx=8, pady=6, wrap=tk.WORD)
    enc_input.pack(fill=tk.BOTH, expand=True)

    # ── Encoder mode sub-notebook: Single | Pipeline | Encode All ────────────
    enc_mode_nb = ttk.Notebook(encoder_tab, style=f"{current_theme}.TNotebook")
    enc_mode_nb.pack(fill=tk.X, pady=(0, 5))

    # ── TAB: Single ───────────────────────────────────────────────────────────
    tab_enc_single = ttk.Frame(enc_mode_nb, style=f"{current_theme}.TFrame", padding=6)
    enc_mode_nb.add(tab_enc_single, text="  Single  ")

    single_r1 = ttk.Frame(tab_enc_single, style=f"{current_theme}.TFrame")
    single_r1.pack(fill=tk.X, pady=(0, 4))

    s_fmt_lbl = tk.Label(single_r1, text="Format:",
                         font=('Segoe UI', 10),
                         bg=THEMES[current_theme]['bg'],
                         fg=THEMES[current_theme]['label_fg'])
    s_fmt_lbl.pack(side=tk.LEFT, padx=(0, 8))
    sidebar_labels.append(s_fmt_lbl)

    enc_format_var = tk.StringVar(value="Base64")
    enc_format_cb = ttk.Combobox(
        single_r1, textvariable=enc_format_var,
        values=list(ENCODERS.keys()),
        width=20, state='readonly', font=('Segoe UI', 10))
    enc_format_cb.pack(side=tk.LEFT, padx=(0, 8))
    enc_format_cb.bind("<<ComboboxSelected>>", on_encoder_select)

    enc_param_frame = ttk.Frame(single_r1, style=f"{current_theme}.TFrame")
    enc_param_label = tk.Label(enc_param_frame, text="Shift:",
                               font=('Segoe UI', 10),
                               bg=THEMES[current_theme]['bg'],
                               fg=THEMES[current_theme]['label_fg'])
    enc_param_label.pack(side=tk.LEFT, padx=(0, 4))
    sidebar_labels.append(enc_param_label)
    enc_param_var = tk.StringVar(value="3")
    tk.Entry(enc_param_frame, textvariable=enc_param_var,
             width=5, font=('Segoe UI', 10)).pack(side=tk.LEFT)

    single_r2 = ttk.Frame(tab_enc_single, style=f"{current_theme}.TFrame")
    single_r2.pack(fill=tk.X)

    ttk.Button(single_r2, text="\u25b6  ENCODE (Ctrl+E)",
               command=run_encode, style=f"{current_theme}.TButton"
               ).pack(side=tk.LEFT, padx=4, ipadx=8, ipady=2)
    ttk.Button(single_r2, text="\u2398  Copy",
               command=copy_encoder_result, style=f"{current_theme}.TButton"
               ).pack(side=tk.LEFT, padx=4, ipadx=8, ipady=2)
    ttk.Button(single_r2, text="\u2715  Clear",
               command=clear_encoder, style=f"{current_theme}.Clear.TButton"
               ).pack(side=tk.LEFT, padx=4, ipadx=8, ipady=2)

    s_hint = tk.Label(tab_enc_single,
                      text="Pick one format and encode.",
                      font=('Segoe UI', 8),
                      bg=THEMES[current_theme]['bg'],
                      fg=THEMES[current_theme]['label_fg'])
    s_hint.pack(anchor='w', pady=(4, 0))
    sidebar_labels.append(s_hint)

    # ── TAB: Pipeline ─────────────────────────────────────────────────────────
    tab_enc_pipe = ttk.Frame(enc_mode_nb, style=f"{current_theme}.TFrame", padding=6)
    enc_mode_nb.add(tab_enc_pipe, text="  Pipeline  ")

    ep_ctrl = ttk.Frame(tab_enc_pipe, style=f"{current_theme}.TFrame")
    ep_ctrl.pack(fill=tk.X, pady=(0, 4))

    ttk.Button(ep_ctrl, text="\u25b6  Run Pipeline",
               command=run_pipeline_encode, style=f"{current_theme}.TButton"
               ).pack(side=tk.LEFT, padx=(0, 5), ipadx=8, ipady=2)
    ttk.Button(ep_ctrl, text="+ Step",
               command=add_enc_pipeline_step, style=f"{current_theme}.TButton"
               ).pack(side=tk.LEFT, padx=3, ipadx=5, ipady=2)
    ttk.Button(ep_ctrl, text="\u2212 Remove",
               command=remove_enc_pipeline_step, style=f"{current_theme}.Clear.TButton"
               ).pack(side=tk.LEFT, padx=3, ipadx=5, ipady=2)
    ttk.Button(ep_ctrl, text="\u2715  Clear",
               command=clear_encoder, style=f"{current_theme}.Clear.TButton"
               ).pack(side=tk.LEFT, padx=5, ipadx=5, ipady=2)

    ep_scroll_wrap = tk.Frame(tab_enc_pipe, bg=THEMES[current_theme]['bg'])
    ep_scroll_wrap.pack(fill=tk.X, pady=2)

    enc_pipe_canvas = tk.Canvas(ep_scroll_wrap, height=52,
                                bg=THEMES[current_theme]['bg'],
                                highlightthickness=0)
    ep_hsc = ttk.Scrollbar(ep_scroll_wrap, orient='horizontal',
                            command=enc_pipe_canvas.xview)
    enc_pipe_canvas.configure(xscrollcommand=ep_hsc.set)
    ep_hsc.pack(side=tk.BOTTOM, fill=tk.X)
    enc_pipe_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    enc_pipe_inner = tk.Frame(enc_pipe_canvas, bg=THEMES[current_theme]['bg'])
    enc_pipe_canvas.create_window((0, 0), window=enc_pipe_inner, anchor='nw')

    for i in range(3):
        _build_enc_pipeline_step(i)

    enc_pipe_canvas.update_idletasks()
    enc_pipe_canvas.configure(scrollregion=enc_pipe_canvas.bbox("all"))

    ep_hint = tk.Label(tab_enc_pipe,
                       text="Chain encoders: ROT13 \u2192 Base64 \u2192 Hex. "
                            "Each step gets a Copy button. Caesar shows n= field inline.",
                       font=('Segoe UI', 8),
                       bg=THEMES[current_theme]['bg'],
                       fg=THEMES[current_theme]['label_fg'])
    ep_hint.pack(anchor='w', pady=(2, 0))
    sidebar_labels.append(ep_hint)

    # ── TAB: Encode All ───────────────────────────────────────────────────────
    tab_enc_all = ttk.Frame(enc_mode_nb, style=f"{current_theme}.TFrame", padding=6)
    enc_mode_nb.add(tab_enc_all, text="  Encode All  ")

    ea_r = ttk.Frame(tab_enc_all, style=f"{current_theme}.TFrame")
    ea_r.pack(fill=tk.X, pady=(0, 4))

    ttk.Button(ea_r, text="\u25b6\u25b6  Encode All (Ctrl+A)",
               command=run_encode_all, style=f"{current_theme}.TButton"
               ).pack(side=tk.LEFT, padx=4, ipadx=8, ipady=2)
    ttk.Button(ea_r, text="\u2398  Copy Output",
               command=copy_encoder_result, style=f"{current_theme}.TButton"
               ).pack(side=tk.LEFT, padx=4, ipadx=8, ipady=2)
    ttk.Button(ea_r, text="\u2715  Clear",
               command=clear_encoder, style=f"{current_theme}.Clear.TButton"
               ).pack(side=tk.LEFT, padx=4, ipadx=8, ipady=2)

    ea_hint = tk.Label(tab_enc_all,
                       text="Encode input using every available format at once. Useful for CTF recon.",
                       font=('Segoe UI', 8),
                       bg=THEMES[current_theme]['bg'],
                       fg=THEMES[current_theme]['label_fg'])
    ea_hint.pack(anchor='w', pady=(4, 0))
    sidebar_labels.append(ea_hint)

    # ── Shared encoder output (used by all three encoder tabs) ────────────────
    enc_out_frame = ttk.LabelFrame(
        encoder_tab, text=" Encoded Output ",
        padding=8, style=f"{current_theme}.TLabelframe")
    enc_out_frame.pack(fill=tk.BOTH, expand=True)

    enc_layer_btn_frame = tk.Frame(enc_out_frame, bg=THEMES[current_theme]['bg'])
    enc_layer_btn_frame.pack(fill=tk.X, pady=(0, 4))

    enc_result_display = scrolledtext.ScrolledText(
        enc_out_frame, height=13, font=("Consolas", 11),
        bg=THEMES[current_theme]['text_bg'],
        fg=THEMES[current_theme]['text'],
        state='disabled',
        insertbackground=THEMES[current_theme]['text'],
        selectbackground=THEMES[current_theme]['accent'],
        padx=8, pady=6, wrap=tk.WORD)
    enc_result_display.pack(fill=tk.BOTH, expand=True)

    # ── Status bar ────────────────────────────────────────────────────────────
    status_var = tk.StringVar(value="Ready")
    status_bar = tk.Label(
        root, textvariable=status_var,
        bd=1, relief=tk.SUNKEN, anchor=tk.W,
        bg=THEMES[current_theme]['accent'],
        fg="white", font=("Segoe UI", 9), padx=8)
    status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # ── Key bindings ──────────────────────────────────────────────────────────
    root.bind("<Return>", run_auto_decode)
    root.bind("<Escape>", clear_decoder)
    root.bind("<Control-l>", lambda e: clear_decoder())
    root.bind("<Control-L>", lambda e: clear_decoder())
    root.bind("<Control-Shift-C>", lambda e: copy_decoder_all())
    root.bind("<Control-h>", lambda e: show_history())
    root.bind("<Control-H>", lambda e: show_history())
    root.bind("<Control-m>", lambda e: dec_mode_nb.select(1))
    root.bind("<Control-M>", lambda e: dec_mode_nb.select(1))
    root.bind("<Control-p>", lambda e: enc_mode_nb.select(1) if main_notebook.index(main_notebook.select()) == 1 else dec_mode_nb.select(2))
    root.bind("<Control-P>", lambda e: enc_mode_nb.select(1) if main_notebook.index(main_notebook.select()) == 1 else dec_mode_nb.select(2))
    root.bind("<Control-e>", lambda e: run_encode())
    root.bind("<Control-E>", lambda e: run_encode())
    root.bind("<Control-a>", lambda e: run_encode_all())
    root.bind("<Control-A>", lambda e: run_encode_all())
    root.bind("<Control-Shift-E>", lambda e: clear_encoder())

    dec_input.focus_set()
    apply_theme(current_theme)
    update_status("Ready — Decoder tab: paste encoded text | Encoder tab: paste plain text", "info")
    load_history()


# ===========================================================
# ENTRY POINT
# ===========================================================

if __name__ == "__main__":
    create_gui()
    root.mainloop()
