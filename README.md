# PubMed Agent 🔍

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

AI-powered tool for automated PubMed literature analysis and summary generation.

## ✨ Features

- Monthly literature monitoring
- Full-text extraction (PMC/PDF)
- DeepSeek AI analysis
- Automated report generation

## 🚀 Quick Start

```bash
# 安装
pip install -r requirements.txt

# 运行
python -m src.cli "neurodegenerative diseases" --max 5
```

## 🔧 Configuration

Rename `config/settings.example.ini` to `settings.ini` and fill your:

```ini
[api]
email = your@email.com
deepseek_key = your_api_key
```

## 📄 Sample Report
![Report Preview](docs/sample_report.png)
