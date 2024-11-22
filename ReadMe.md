# Directory Mapper 🗂️

A powerful, cross-platform directory visualization and mapping tool with rich features.

## 🌟 Features

- 🌐 **Cross-Platform Support**
  - Works seamlessly on Windows, macOS, and Linux
  - Handles long file paths and platform-specific nuances

- 🎨 **Flexible Output**
  - Multiple formats: Terminal, JSON, Markdown
  - Customizable color schemes
  - Detailed or compact views

- 🔍 **Advanced Filtering**
  - Include/exclude file extensions
  - Filter hidden files
  - Limit directory depth
  - Sort by name, size, or modification date

## 🚀 Installation

### Prerequisites
- Python 3.8+
- pip

### Install via pip
```bash
pip install directory-mapper
```

### Or from source
```bash
git clone https://github.com/Muhammad-NSQ/Dlens.git
cd Dlens
pip install -r requirements.txt
```

## 💡 Usage Examples

### Basic Usage
```bash
# Map current directory
python Dlens.py

# Map specific directory
python Dlens.py /path/to/directory
```

### Advanced Options
```bash
# Show hidden files, JSON output with details
python Dlens.py --show-hidden --output-format json --show-details

# Limit depth, filter Python files
python Dlens.py --depth 3 --filter .py

# Sort by file size
python Dlens.py --sort size
```

## 📋 Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `path` | Directory to map (default: current) | `python directory_mapper.py /home` |
| `--max-preview` | Max items per subdirectory | `--max-preview 5` |
| `--show-hidden` | Include hidden files/folders | `--show-hidden` |
| `--filter` | Include specific file extensions | `--filter .py .md` |
| `--output-format` | Output style (text/json/markdown) | `--output-format json` |
| `--sort` | Sort entries (name/size/date) | `--sort size` |

## 🤝 Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## 📄 License
MIT License - See [LICENSE](LICENSE.md) for details.
