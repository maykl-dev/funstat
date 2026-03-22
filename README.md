# 🔍 Demo-OSINT

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-2CA5E0?logo=telegram)](https://telegram.org)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Advanced Telegram OSINT & Message Intelligence Platform**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [ScrenShot](#-screenshot)

</div>

---

## 📋 Overview

Demo-OSINT is a professional-grade Telegram intelligence gathering platform designed for security research and digital forensics. It provides real-time message monitoring, multi-account management, and advanced search capabilities across Telegram conversations.

> ⚠️ **For authorized security testing and research purposes only**

---

## ✨ Features

| Module | Capability |
|--------|-----------|
| **🔐 Multi-Account Management** | Secure Telegram API integration with session persistence |
| **📡 Real-time Monitoring** | Live message capture from multiple accounts simultaneously |
| **🗄️ Intelligent Storage** | SQLite database with deduplication and indexing |
| **🔎 Advanced Search** | Full-text search by content, username, or user ID |
| **🤖 Bot Interface** | Interactive Telegram bot for remote querying |
| **📊 Admin Dashboard** | Account management and statistics panel |

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Telegram Bot   │────▶│   SQLite DB      │◄────│  Scraper Engine │
│   (bot.py)      │     │   (monitor.db)   │     │   (scrap.py)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
│                                              │
▼                                              ▼
┌──────────┐                                  ┌──────────┐
│  Admin   │                                  │ Telethon │
│  Panel   │                                  │ Clients  │
└──────────┘                                  └──────────┘
```

---

## 🚀 Installation

### Prerequisites
- Python 3.9+
- Telegram API credentials ([my.telegram.org](https://my.telegram.org))

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/Demo-Osint.git
cd Demo-Osint

# Install dependencies
pip install telebot telethon aiosqlite

```

### Configuration

Edit bot.py:

```
TELEGRAM_TOKEN = 'YOUR_BOT_TOKEN'      # From @BotFather
ADMIN_ID = 123456789                    # Your Telegram user ID
```

# 📖 Usage

1. Start bot.py
2. Go to telegram bot and add account in Panel
3. Run scrap.py

# scarp

- Features:

  - Automatic database initialization
  - Multi-account concurrent monitoring
  - Historical message backfill
  - Real-time new message capture
  - Duplicate prevention


# screenshot

<img src="https://github.com/user-attachments/assets/8f97a203-dcfb-4f61-a501-bc36751016d4">
