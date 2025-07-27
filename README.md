# ** Work in Progress **
# dlpipkle

A tool for downloading pip packages and their dependencies for offline installation.

## Overview

`dlpipkle` is a command-line tool that solves the challenge of downloading Python packages and their dependencies for offline installation. It addresses common issues with platform-specific binaries by first enumerating all dependencies and then downloading each package independently.

### Key Features

- Downloads complete dependency trees for specified packages
- Supports both binary (wheel) and source package downloads
- Allows specification of target platform, Python version, and ABI
- Handles platform compatibility issues by isolating package downloads
- Lists available platforms for packages to help with compatibility decisions
- Supports downloading packages specified in requirements files

## Installation

For development installation:

```bash
git clone https://github.com/yourusername/dlpipkle.git
cd dlpipkle
pip install -e .
```

## Usage

### Basic Usage

Download a single package and its dependencies:

```bash
dlpipkle numpy
```

Download packages from a requirements file:

```bash
dlpipkle -r requirements.txt
```

Download to a specific directory:

```bash
dlpipkle -d ./packages requests
```

### Advanced Usage

Download source packages instead of binaries:

```bash
dlpipkle --source numpy
```

Download packages for a specific platform and Python version:

```bash
dlpipkle --platform manylinux2014_x86_64 --python-version 3.9 tensorflow
```

List available platforms for a package:

```bash
dlpipkle --list-platforms numpy
```

Include specific extras:

```bash
dlpipkle -e aws -e testing boto3
```

Exclude certain packages from being downloaded:

```bash
dlpipkle --exclude setuptools wheel pandas
```

### Offline Installation

After downloading all packages, you can install them on an offline system using:

```bash
pip install --no-index --find-links=/path/to/downloaded/packages package-name
```

Or install all packages from a requirements file:

```bash
pip install --no-index --find-links=/path/to/downloaded/packages -r requirements.txt
```

## How It Works

The tool works in two distinct phases:

1. **Dependency Resolution Phase**:
   - Queries the PyPI JSON API to get package metadata
   - Extracts the "requires_dist" field to identify dependencies
   - Recursively builds a complete dependency tree
   - Normalizes package names to handle variations in formatting

2. **Download Phase**:
   - Uses `pip download` with the `--no-deps` flag for each package
   - Applies platform and Python version constraints when specified
   - Falls back to generic downloads if platform-specific downloads fail
   - Provides detailed download results and summary

## Project Structure

```
dlpipkle/
├── src/
│   └── dlpipkle/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── downloader.py
│       ├── dependency_resolver.py
│       └── platform_utils.py
│
├── pyproject.toml
├── README.md
└── LICENSE
```

## Requirements

- Python 3.8 or higher
- Required packages:
  - wheel-filename
  - packaging>=21.0

## Limitations and Considerations

- The tool does not evaluate conditional dependencies based on environment markers
- Some complex version specifiers might not be handled perfectly
- Platform-specific binaries may not be available for all packages
- For maximum compatibility, consider downloading source packages with the `--source` flag

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
