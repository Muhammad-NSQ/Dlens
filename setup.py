#!/usr/bin/env python3
"""
Setup script for DLens - Directory Mapping Tool
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
def read_requirements(filename):
    """Read requirements from file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        return []

setup(
    name="dlens",
    version="1.0.0",
    author="Muhammad-NSQ",
    author_email="muhammednidal122@gmail.com",
    description="Enhanced directory mapping and visualization tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Muhammad-NSQ/Dlens",
    project_urls={
        "Bug Reports": "https://github.com/Muhammad-NSQ/Dlens/issues",
        "Source": "https://github.com/Muhammad-NSQ/Dlens",
        "Documentation": "https://github.com/Muhammad-NSQ/Dlens#readme",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Filesystems",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    keywords="directory mapping filesystem visualization cli tree",
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "rich>=12.0.0",
        "jinja2>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov",
            "black",
            "flake8",
            "mypy",
        ],
        "test": [
            "pytest>=6.0",
            "pytest-cov",
        ],
    },
    entry_points={
        "console_scripts": [
            "dlens=dlens.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "dlens": [
            "resources/*.json",
            "resources/templates/*.html",
        ],
    },
    zip_safe=False,
)
