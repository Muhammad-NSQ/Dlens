# DLens - Enhanced Directory Mapping Tool

A powerful command-line tool for visualizing and analyzing directory structures with rich formatting, search capabilities, and multiple export formats.

## Features

- 🌳 **Rich Terminal Output** - Beautiful tree visualization with colors and icons
- 🔍 **Powerful Search** - Find files and directories with pattern matching and regex support
- 📊 **Directory Statistics** - Analyze file types, sizes, and modification dates
- 🎨 **Customizable Themes** - Multiple color schemes and styling options
- 📤 **Multiple Export Formats** - Export to HTML, JSON, Markdown, CSV
- ⚡ **Performance Optimized** - Efficient scanning of large directories
- 🔧 **Highly Configurable** - Extensive options and persistent configuration

## Installation

### From PyPI (Recommended)

```bash
pip install dlens
```

### From Source

```bash
git clone https://github.com/Muhammad-NSQ/Dlens.git
cd Dlens
pip install -e .
```

## Quick Start

### Basic Directory Mapping

```bash
# Map current directory
dlens map

# Map specific directory with details
dlens map /path/to/directory --show-details --show-stats

# Map with custom depth and preview limits
dlens map ~/projects --depth 3 --max-preview 5
```

### Search Files and Directories

```bash
# Simple pattern search
dlens search "*.py" ~/projects

# Regex search with results limit
dlens search --regex "test_.*\.py$" --max-results 50

# Export search results to HTML
dlens search "*.md" --output-format html --output-file results.html
```

### Export Options

```bash
# Export directory map to HTML
dlens map --output-format html ~/project

# Export to JSON with statistics
dlens map --output-format json --show-stats > directory.json

# Generate Markdown documentation
dlens map --output-format markdown --show-details > STRUCTURE.md
```

## Configuration

DLens supports persistent configuration to save your preferred settings:

```bash
# View current configuration
dlens config view

# Set default options
dlens config set theme ocean
dlens config set max_preview 10
dlens config set show_details true

# Reset to defaults
dlens config reset
```

## Export Formats

### HTML Export
Interactive HTML with:
- Collapsible directory tree
- Dark/light theme toggle
- Search functionality
- File statistics
- Responsive design

### JSON Export
Structured data including:
- Complete directory hierarchy
- File metadata (size, dates, permissions)
- Directory statistics
- Scan information

### Markdown Export
Documentation-friendly format with:
- Hierarchical bullet lists
- File details and statistics
- GitHub-compatible formatting

## Advanced Features

### Filtering and Exclusion

```bash
# Include only specific file types
dlens map --filter .py --filter .js --filter .html

# Exclude certain file types
dlens map --exclude .pyc --exclude .log --exclude .tmp

# Show hidden files
dlens map --show-hidden
```

### Performance Options

```bash
# Parallel processing for large directories
dlens search "pattern" --parallel

# Limit depth to improve performance
dlens map --depth 5

# Disable progress for scripting
dlens map --no-progress
```

### Theming

Available themes: `default`, `ocean`, `forest`, `pastel`, `monochrome`, `dark`

```bash
# Use a specific theme
dlens map --theme ocean

# Use custom theme file
dlens map --theme-path /path/to/custom-theme.json
```

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `max_preview` | Items shown per directory | 3 |
| `root_preview` | Items shown in root directory | 5 |
| `depth` | Maximum recursion depth | unlimited |
| `show_hidden` | Include hidden files/directories | false |
| `show_details` | Show file metadata | false |
| `show_stats` | Display directory statistics | false |
| `color` | Enable colored output | true |
| `icons` | Show file type icons | true |
| `parallel` | Use parallel processing | true |
| `follow_symlinks` | Follow symbolic links | false |

## Examples

### Development Project Analysis

```bash
# Analyze a Python project
dlens map ~/my-python-project \
  --filter .py --filter .md --filter .yml \
  --show-details --show-stats \
  --output-format html \
  --theme dark

# Find all test files
dlens search "test_*.py" ~/my-python-project \
  --output-format csv \
  --output-file test-files.csv
```

### System Administration

```bash
# Check log directory structure
dlens map /var/log --show-details --max-preview 10

# Find large files
dlens search "*" /home/user --show-details | head -20

# Generate system documentation
dlens map /etc --output-format markdown --depth 2 > system-config.md
```

## Requirements

- Python 3.8 or higher
- Compatible with Windows, macOS, and Linux

## Dependencies

- `click` >= 8.0.0 - Command line interface
- `rich` >= 12.0.0 - Terminal formatting and colors
- `jinja2` >= 3.0.0 - Template rendering for HTML export

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### Version 1.0.0
- Initial release
- Core directory mapping functionality
- Search capabilities
- Multiple export formats
- Configuration management
- Theme support