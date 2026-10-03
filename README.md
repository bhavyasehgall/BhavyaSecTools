# 🔐 BhavyaSecTools

> A modular Python/Tkinter cybersecurity utility suite built for cybersecurity learning, authorized security analysis, and practical experimentation.

**BhavyaSecTools** brings several small security-focused utilities into a single graphical interface. The project is designed to make common cybersecurity learning tasks easier to explore while keeping each utility relatively independent and understandable.

The project focuses on **network analysis, web detection, data decoding, steganography, and wireless security experimentation** in authorized environments.

---

## 📌 Overview

BhavyaSecTools is a lightweight cybersecurity toolkit developed in Python with a Tkinter-based GUI.

Instead of relying on one large security framework, the project organizes several focused utilities into a single dashboard.

### Current modules

* 🌐 Web Detection
* 📡 Wi-Fi Auditing
* 🔓 Data Decoder
* 🕵️ Steganography
* 🖥️ Graphical Dashboard

The project is primarily intended as a **learning and experimentation project** for understanding how security utilities can be developed and integrated using Python.

---

## 🚀 Features

### 🌐 Web Detection

The web detection module provides a simple interface for performing basic web/network analysis.

Depending on the environment and installed tools, it can be used to explore:

* Target connectivity
* HTTP-related information
* Web service analysis
* Network scanning workflows
* Security-oriented reconnaissance concepts

The module is designed for authorized targets and lab environments.

---

### 📡 Wi-Fi Audit

The Wi-Fi audit module provides a learning-oriented interface for wireless security assessment.

Features include:

* Wireless interface checks
* Dependency detection
* Authorization confirmation
* Wireless auditing workflow support
* Integration with relevant Linux wireless utilities

The module is intended for networks and devices that you own or have explicit permission to assess.

---

### 🔓 Decoder

The decoder utility provides several common decoding operations useful during cybersecurity analysis and CTF-style learning.

Supported techniques include:

* Base64
* Hexadecimal
* Binary
* URL decoding
* HTML decoding
* ROT/Caesar-style transformations
* Multi-step decoding workflows

This module is useful when analyzing encoded data encountered during security labs or investigations.

---

### 🕵️ Steganography

BhavyaSecTools includes a custom steganography utility for experimenting with hiding and extracting data.

The implementation uses an **LSB-based approach** for embedding data into supported image data.

The project uses a custom marker:

```text
LSTEG
```

This marker helps the application identify data written using the toolkit's own steganography format.

The module can be used to explore:

* Data hiding
* Data extraction
* Image-based steganography
* LSB concepts
* Basic payload handling

---

## 🖥️ Graphical Interface

The toolkit uses **Tkinter** to provide a central dashboard.

The main application launches the individual utilities and keeps the project organized as separate modules.

```text
                 BhavyaSecTools
                       │
             ┌─────────┴─────────┐
             │    Main Dashboard │
             └─────────┬─────────┘
                       │
       ┌───────────────┼────────────────┐
       │               │                │
       ▼               ▼                ▼
   Recon / Web      Analysis        Wireless
       │               │                │
       ▼          ┌────┴────┐           ▼
 Web Detection    │         │       Wi-Fi Audit
                  ▼         ▼
               Decoder   Steganography
```

---

## 🧰 Tech Stack

| Technology           | Purpose                           |
| -------------------- | --------------------------------- |
| **Python 3**         | Core programming language         |
| **Tkinter**          | Graphical user interface          |
| **Subprocess**       | Running system security utilities |
| **Linux CLI tools**  | Security and network operations   |
| **Image processing** | Steganography functionality       |

---

## 📁 Project Structure

```text
BhavyaSecTools/
│
├── main.py
├── wifi-audit.py
├── decoder.py
├── steghide.py
├── webdetection.py
│
└── README.md
```

### File Description

| File              | Purpose                          |
| ----------------- | -------------------------------- |
| `main.py`         | Main Tkinter dashboard           |
| `wifi-audit.py`   | Wireless auditing utility        |
| `decoder.py`      | Encoding/decoding utility        |
| `steghide.py`     | Custom LSB steganography utility |
| `webdetection.py` | Web/network detection utility    |
| `README.md`       | Project documentation            |

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/bhavyasehgall/BhavyaSecTools.git
cd BhavyaSecTools
```

### 2. Verify Python

```bash
python3 --version
```

Python 3 is recommended.

### 3. Install Tkinter

On Debian/Kali-based systems:

```bash
sudo apt update
sudo apt install python3-tk
```

Additional system utilities may be required depending on which module you use.

### 4. Run the toolkit

```bash
python3 main.py
```

Some wireless or network operations may require appropriate Linux permissions.

---

## 🧪 Example Usage

### Launch the dashboard

```bash
python3 main.py
```

From the graphical interface, select the utility you want to use.

### Decoder

Provide encoded data and select the appropriate decoding operation.

Example:

```text
SGVsbG8=
```

can be decoded from Base64 to:

```text
Hello
```

### Steganography

Use the steganography utility to experiment with embedding and extracting data from supported images.

### Web Detection

Provide an authorized domain, hostname, or IP address and perform the available analysis.

### Wi-Fi Audit

Select an appropriate wireless interface and use the auditing workflow only against networks you own or are explicitly authorized to test.

---

## 🎯 Project Goals

BhavyaSecTools was built to explore practical cybersecurity concepts through hands-on Python development.

The main goals are:

* Learn how security utilities work internally
* Practice Python programming for cybersecurity
* Understand Linux security tooling
* Experiment with network reconnaissance
* Explore data encoding and decoding
* Understand basic steganography techniques
* Build GUI-based security utilities
* Practice integrating Python applications with system tools

---

## 🔐 Security & Legal Notice

**BhavyaSecTools is intended for educational purposes and authorized security testing only.**

Only use the toolkit against:

* Systems you own
* Personal laboratory environments
* CTF platforms where testing is permitted
* Networks and applications for which you have explicit authorization

Do **not** use these utilities against systems, networks, websites, or devices without permission.

The author is not responsible for misuse of this software.

---

## ⚠️ Limitations

BhavyaSecTools is a learning-focused project rather than a replacement for established professional security frameworks.

Some functionality depends on:

* Operating system capabilities
* Installed command-line utilities
* Network interface support
* User permissions
* Python dependencies
* Target/environment configuration

Results produced by security utilities should be manually validated before being treated as security findings.

---

## 🛣️ Future Improvements

Potential improvements include:

* [ ] Improve the main dashboard UI
* [ ] Add better error handling
* [ ] Add structured logging
* [ ] Improve dependency detection
* [ ] Add configuration management
* [ ] Improve result presentation
* [ ] Add exportable reports
* [ ] Add more security-analysis utilities
* [ ] Improve cross-platform compatibility
* [ ] Add automated testing
* [ ] Improve module isolation and code organization

---

## 🤝 Contributing

Contributions, suggestions, and improvements are welcome.

A typical workflow:

```bash
git clone https://github.com/bhavyasehgall/BhavyaSecTools.git
cd BhavyaSecTools
```

Create a branch for your changes:

```bash
git checkout -b feature/improvement
```

Make your changes, test them, and submit a pull request.

Please keep contributions focused on legitimate cybersecurity education, research, and authorized security testing.

---

## 👨‍💻 Author

**Bhavya Sehgal**

Cybersecurity Student | Junior Cybersecurity Analyst

### Profiles

* GitHub: https://github.com/bhavyasehgall
* LinkedIn: https://www.linkedin.com/in/bhavyasehgall/

---

## 📄 License

This project is released under the **MIT License**.

See the repository license file for the complete license text.

---

## ⭐ Project

If you find BhavyaSecTools useful for learning cybersecurity or Python security development, consider giving the repository a ⭐.

**Built for learning. Built for experimentation. Built with cybersecurity in mind.**
