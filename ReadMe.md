# 📂 DLens: Directory Mapping Toolkit

## 🔍 Overview

DLens is a sophisticated command-line utility for comprehensive directory exploration and analysis.

## ✨ Features

- 🌐 Cross-platform directory scanning
- 🔬 Advanced filtering and sorting
- 📊 Multiple output formats
- 🚦 Configurable visualization options

## 🛠 Installation

```bash
pip install dlens
```

## 🧭 Command Line Options

| Option | Icon | Description | Example |
|--------|------|-------------|---------|
| `--depth` | 🌳 | Maximum recursion depth | `--depth 3` |
| `--show-hidden` | 🕵️ | Include hidden files | `--show-hidden` |
| `--output-format` | 📄 | Specify output type | `--output-format json` |
| `--icons` | 🎨 | Display file type icons | `--icons` |
| `--filter` | 🧩 | Filter by extensions | `--filter .py .js` |
| `--sort` | 📊 | Sort entries | `--sort size` |

## 🚀 Quick Usage

```bash
dlens map /path/to/directory --depth 5 --show-hidden --output-format json --icons
```

## 🔧 Configuration

```bash
# View configuration
dlens config view

# Set parameters
dlens config set max_preview 10
```

## 💻 System Requirements

- Python 3.8+
- Windows, macOS, Linux

## 🤝 Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## 📄 License
MIT License - See [LICENSE](LICENSE.md) for details.
