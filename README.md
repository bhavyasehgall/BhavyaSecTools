# 🔐 KaliToolkit — All-in-One Cybersecurity Toolkit

> A powerful GUI-based cybersecurity toolkit designed for **ethical hackers, security researchers, and learners**.
> Combines multiple tools into one interface for **reconnaissance, Wi-Fi auditing, decoding, steganography, and automation**.

---

## 🚀 Features

### 🌐 Network & Recon Tools

* 🔍 Fast port scanning (Nmap)
* 🌍 HTTP header analysis
* 📡 DNS, Ping, Traceroute
* 🛠️ Vulnerability scanning (CVE detection)
* 🌐 Website technology detection

---

### 📶 Wi-Fi Audit Module

* 📡 Wi-Fi scanning (SSID, BSSID, Signal)
* ⚡ Monitor mode toggle
* 🔄 WPA handshake conversion (.cap → .hc22000)
* 🔐 Password cracking (John the Ripper)

---

### 🔓 Decoder Tool

* Base64, Hex, Binary decoding
* Multi-layer auto decoding
* URL / HTML decoding
* ROT / Caesar cipher detection

---

### 🕵️ Steganography Tool

* Hide data in images/files
* Extract hidden payloads
* Encryption support (password-based)
* Multi-format support

---

### ⚙️ Automation Toolkit

* Combine multiple tools in one GUI
* Run parallel scans
* Save outputs/logs
* Fast mode for aggressive scanning

---

## 🖥️ Screenshots

> *(Add your GUI screenshots here for better impact)*

---

## ⚙️ Installation

### 1. Clone Repository

```bash
git clone https://github.com/bhavyasehgall/kalitoolkit.git
cd kalitoolkit
```

### 2. Install Dependencies

```bash
sudo apt update
sudo apt install nmap aircrack-ng hcxtools john sqlmap whatweb
```

### 3. Run the Tool

```bash
sudo python3 main.py
```

---

## 🧪 Usage

### 🔹 Wi-Fi Auditing Workflow

1. Scan available networks
2. Enable monitor mode
3. Capture handshake (external tools)
4. Convert capture → hash
5. Run password cracking

---

### 🔹 Network Scanning

* Enter target (domain/IP)
* Choose scan type
* View results in real-time GUI

---

### 🔹 Decoder

* Paste encoded text
* Use Auto Decode or Pipeline Mode

---

## ⚠️ Legal Disclaimer

This tool is intended **ONLY for authorized use**.

You must:

* Own the network OR
* Have **explicit written permission**

Unauthorized usage may violate laws such as:

* IT Act 2000 (India)
* CFAA (USA)
* Computer Misuse Act (UK)

---

## 🧠 Tech Stack

* Python 3
* Tkinter (GUI)
* Linux CLI tools
* Subprocess automation

---

## 📁 Project Structure

```
kalitoolkit/
│── wifi-audit.py
│── decoder.py
│── steghide.py
│── webdetection.py
│── main.py
```

---

## 🔥 Future Improvements

* GPU cracking (Hashcat)
* Auto handshake capture
* Dark mode UI
* Report export (JSON/PDF)
* Plugin system

---

## 🤝 Contributing

Pull requests are welcome!
Feel free to fork and improve the toolkit.

---

## ⭐ Support

If you like this project:

* ⭐ Star the repo
* 🍴 Fork it
* 🧠 Share with others

---

## 👨‍💻 Author

**Bhavya Sehgal**
Cybersecurity Enthusiast 🚀

* GitHub: https://github.com/bhavyasehgall
* LinkedIn: https://www.linkedin.com/in/bhavyasehgall/

---

## 💡 Inspiration

Inspired by real-world tools used in penetration testing environments like Kali Linux and modern bug bounty workflows.

---

## 🛡️ License

MIT License — Free to use and modify
