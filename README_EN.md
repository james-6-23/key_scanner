# 🎪 Hajimi King - Automated API Key Discovery System

<div align="center">

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![Status](https://img.shields.io/badge/status-beta-yellow.svg)](https://github.com/yourusername/hajimi-king)

**人人都是哈基米大王** 👑

[English](#) | [简体中文](docs/README_CN.md) | [Quick Reference](docs/guides/QUICK_REFERENCE.md) | [Documentation](docs/) | [API Reference](docs/api/)

</div>

---

## 📚 Documentation

All project documentation has been organized in the `docs/` directory for better maintainability:

- **[Documentation Center](docs/)** - Complete documentation index
- **[Quick Reference](docs/guides/QUICK_REFERENCE.md)** - Common commands and operations
- **[Deployment Guides](docs/deployment/)** - Docker, GitHub Container Registry, and more
- **[Technical Guides](docs/guides/)** - Project structure, optimization strategies
- **[中文文档](docs/README_CN.md)** - Chinese documentation

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage](#-usage)
- [Configuration](#-configuration)
- [API Documentation](#-api-documentation)
- [Docker Deployment](#-docker-deployment)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [Changelog](#-changelog)
- [License](#-license)

---

## 🌟 Overview

Hajimi King is an automated system designed to discover and validate API keys from public code repositories. It leverages GitHub's search API to find potentially exposed credentials and validates them efficiently using parallel processing.

> ⚠️ **DISCLAIMER**: This tool is for educational and security research purposes only. Always respect API terms of service and handle discovered keys responsibly.

### Key Benefits

- 🔍 **Intelligent Search**: Advanced query strategies for efficient discovery
- ⚡ **Parallel Validation**: Multi-threaded validation for high performance
- 🔄 **Incremental Scanning**: Resume from where you left off
- 🐳 **Docker Ready**: Easy deployment with Docker support
- 📊 **External Sync**: Integration with load balancers and key management systems

---

## ✨ Features

### Core Features

1. **GitHub Code Search** - Search for API keys using customizable queries
2. **Parallel Validation** - Validate multiple keys simultaneously
3. **Smart Filtering** - Automatically filter out documentation and test files
4. **Proxy Support** - Rotate through multiple proxies for stability
5. **External Synchronization** - Sync to [Gemini-Balancer](https://github.com/snailyp/gemini-balance) and [GPT-Load](https://github.com/tbphp/gpt-load)

### Advanced Features

- 📈 Incremental scanning with checkpoint support
- 🔐 Secure credential management
- 📝 Detailed logging and reporting
- 🚀 Zero-downtime deployment
- 📊 Performance monitoring

---

## 🚀 Quick Start

> 📖 **Need a quick command reference?** Check out our [Quick Reference Guide](docs/guides/QUICK_REFERENCE.md) for all common commands and operations.

### Prerequisites

- Python 3.11 or higher
- Docker (optional, for containerized deployment)
- GitHub Personal Access Token

### One-Line Installation

```bash
# Clone and setup
git clone https://github.com/james-6-23/key_scanner.git && cd key_scanner && make setup
```

### Basic Usage

```bash
# Configure environment
cp env.example .env
# Edit .env with your GitHub token

# Run the scanner
python app/api_key_scanner.py
```

---

## 📦 Installation

### Method 1: Using UV (Recommended) 🚀

UV is a fast Python package manager written in Rust. [Learn more about UV](docs/guides/uv_setup_guide.md)

1. **Install UV**
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Windows
   irm https://astral.sh/uv/install.ps1 | iex
   ```

2. **Clone and setup project**
   ```bash
   git clone https://github.com/james-6-23/key_scanner.git
   cd key_scanner
   
   # Set Python version
   uv python install 3.11
   uv python pin 3.11
   
   # Create virtual environment
   uv venv
   
   # Activate environment
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   
   # Install dependencies
   uv pip install -r pyproject.toml
   ```

### Method 2: Traditional pip/venv

1. **Clone the repository**
   ```bash
   git clone https://github.com/james-6-23/key_scanner.git
   cd key_scanner
   ```

2. **Set up Python environment**
   ```bash
   # Using venv
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Configure search queries**
   ```bash
   # Copy the example queries file
   cp queries.example data/queries.txt
   # Edit data/queries.txt to customize your search patterns
   ```

### Method 3: Docker Installation

```bash
# Using docker-compose
docker-compose up -d

# Or build manually
docker build -t hajimi-king:latest .
docker run -d --name hajimi-king -v ./data:/app/data hajimi-king:latest
```

### Method 4: Using Makefile

```bash
# View available commands
make help

# Quick setup and run
make build
make run
```

---

## 💻 Usage

### Command Line Interface

```bash
# Basic usage
python app/api_key_scanner.py

# With custom configuration
python app/api_key_scanner.py --config custom.env

# Run specific queries
python app/api_key_scanner.py --queries custom_queries.txt
```

### Python API

```python
from utils.github_client import GitHubClient
from utils.parallel_validator import ParallelKeyValidator

# Initialize clients
github = GitHubClient(tokens=['your_token'])
validator = ParallelKeyValidator(max_workers=10)

# Search for keys
results = github.search_for_keys("AIzaSy in:file")

# Validate keys
valid_keys = validator.validate_batch(potential_keys)
```

### Docker Commands

```bash
# Start service
docker-compose up -d

# View logs
docker-compose logs -f hajimi-king

# Stop service
docker-compose down

# Run with custom config
docker run -v $(pwd)/custom.env:/app/.env hajimi-king:latest
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file based on `env.example`:

```bash
# Required Configuration
GITHUB_TOKENS=ghp_token1,ghp_token2,ghp_token3  # GitHub API tokens (comma-separated)

# Search Configuration
QUERIES_FILE=queries.txt                        # Search queries file
DATE_RANGE_DAYS=730                            # Repository age filter (days)
FILE_PATH_BLACKLIST=readme,docs,test,example   # Paths to skip

# Performance Configuration
HAJIMI_MAX_WORKERS=10                          # Parallel validation threads
HAJIMI_BATCH_SIZE=10                           # Batch processing size
HAJIMI_BATCH_INTERVAL=60                       # Batch interval (seconds)

# Proxy Configuration (Optional)
PROXY=http://proxy1:8080,http://proxy2:8080    # Proxy list (comma-separated)

# External Sync (Optional)
GEMINI_BALANCER_SYNC_ENABLED=false             # Enable Gemini Balancer sync
GEMINI_BALANCER_URL=http://balancer:8080       # Balancer URL
GEMINI_BALANCER_AUTH=your_auth_token           # Balancer auth token

# Data Storage
DATA_PATH=./data                               # Data directory path
```

### Search Queries Configuration

The project uses a two-file approach for search queries:
- `queries.example` - Example queries file (committed to version control)
- `data/queries.txt` - Your actual queries file (ignored by git)

To set up your queries:
```bash
# First time setup
cp queries.example data/queries.txt

# Edit with your custom queries
nano data/queries.txt  # or use your preferred editor
```

Example query patterns in `data/queries.txt`:

```bash
# Basic search
AIzaSy in:file

# Environment files
AIzaSy in:file filename:.env
AIzaSy in:file filename:.env.example

# Language-specific
AIzaSy in:file extension:py "GEMINI_API_KEY"
AIzaSy in:file language:javascript filename:config.js

# Advanced patterns
"AIzaSy" "gemini" in:file
AIzaSy in:file size:<10000
```

See [Query Optimization Guide](docs/guides/queries_optimization_guide.md) for advanced strategies.

---

## 📚 API Documentation

### Core Modules

#### GitHubClient

Handles GitHub API interactions:

```python
class GitHubClient:
    def __init__(self, tokens: List[str])
    def search_for_keys(self, query: str) -> Dict[str, Any]
    def get_file_content(self, item: Dict[str, Any]) -> Optional[str]
```

#### ParallelKeyValidator

Validates API keys in parallel:

```python
class ParallelKeyValidator:
    def __init__(self, max_workers: int = 10)
    def validate_batch(self, keys: List[str]) -> Dict[str, ValidationResult]
    def get_stats(self) -> ValidationStats
```

#### FileManager

Manages data persistence:

```python
class FileManager:
    def __init__(self, data_dir: str)
    def save_valid_keys(self, repo: str, path: str, url: str, keys: List[str])
    def load_checkpoint(self) -> Checkpoint
    def save_checkpoint(self, checkpoint: Checkpoint)
```

For complete API reference, see [API Documentation](docs/api/).

---

## 🐳 Docker Deployment

### Development Environment

```yaml
# docker-compose.yml
version: '3.8'
services:
  hajimi-king:
    build: .
    volumes:
      - ./data:/app/data
    env_file:
      - .env
```

### Production Deployment

```bash
# Zero-downtime deployment
./deploy.sh --version v1.0.0

# Manual blue-green deployment
docker-compose -f docker-compose.prod.yml up -d
```

### Docker Hub

```bash
# Pull from Docker Hub
docker pull yourusername/hajimi-king:latest

# Run with custom config
docker run -d \
  --name hajimi-king \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/.env:/app/.env \
  yourusername/hajimi-king:latest
```

See [Docker Deployment Guide](docs/deployment/docker_deployment_guide.md) for detailed instructions, or check the [Quick Reference](docs/guides/QUICK_REFERENCE.md#-docker-镜像管理) for common Docker commands.

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Module Import Errors

```bash
ModuleNotFoundError: No module named 'common'
```

**Solution**: Ensure you're running from the project root:
```bash
cd /path/to/hajimi-king
python app/api_key_scanner.py  # Use the new filename
```

#### 2. GitHub API Rate Limiting

```
Error: API rate limit exceeded
```

**Solution**: 
- Add more GitHub tokens to `.env`
- Implement proxy rotation
- Reduce request frequency

#### 3. Permission Denied

```
PermissionError: [Errno 13] Permission denied: './data'
```

**Solution**:
```bash
# Fix permissions
chmod -R 755 data/
# Or for Docker
docker exec hajimi-king chown -R appuser:appuser /app/data
```

#### 4. Memory Issues

**Solution**: Adjust worker count and batch size:
```bash
HAJIMI_MAX_WORKERS=5
HAJIMI_BATCH_SIZE=5
```

### Debug Mode

Enable debug logging:
```bash
# In .env
LOG_LEVEL=DEBUG

# Or via command line
LOG_LEVEL=DEBUG python app/api_key_scanner.py
```

### Getting Help

1. Check [FAQ](docs/FAQ.md)
2. Search [Issues](https://github.com/yourusername/hajimi-king/issues)
3. Join our [Discord](https://discord.gg/hajimi-king)

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](docs/CONTRIBUTING.md) for details.

### Development Setup

```bash
# Fork and clone
git clone https://github.com/yourusername/hajimi-king.git
cd hajimi-king

# Create branch
git checkout -b feature/amazing-feature

# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Submit PR
```

### Code Style

- Follow PEP 8
- Use Black for formatting
- Run Ruff for linting
- Write tests for new features

---

## 📝 Changelog

### [Unreleased]
- Database support for key storage
- Web UI for key management
- Advanced analytics dashboard

### [v0.0.1-beta] - 2024-01-07
- Initial beta release
- Parallel validation support
- Docker deployment
- External sync integration

See [CHANGELOG.md](docs/CHANGELOG.md) for full history.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Thanks to all contributors
- Inspired by security research community
- Built with ❤️ using Python and Docker

---

<div align="center">

**⭐ Star us on GitHub if this project helped you!**

[Report Bug](https://github.com/yourusername/hajimi-king/issues) · [Request Feature](https://github.com/yourusername/hajimi-king/issues) · [Documentation](docs/)

</div>
